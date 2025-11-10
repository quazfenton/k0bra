#!/usr/bin/env python3
"""
Containerized Build Cache Proxy
Speeds CI by providing sharable remote build cache stored in container volumes
"""

import os
import json
import hashlib
import time
import redis
import docker
from flask import Flask, request, jsonify, send_file
from pathlib import Path
import tempfile
import tarfile
import threading

app = Flask(__name__)
client = docker.from_env()

class BuildCacheProxy:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.cache_volume = 'build_cache_volume'
        self.nginx_container = None
        self.setup_infrastructure()
    
    def setup_infrastructure(self):
        """Setup Redis, nginx cache, and Docker volumes"""
        # Create cache volume
        try:
            client.volumes.create(name=self.cache_volume)
        except docker.errors.APIError:
            pass  # Volume already exists
        
        # Start Redis if not running
        self._ensure_redis_running()
        
        # Start nginx cache proxy
        self._start_nginx_cache()
    
    def _ensure_redis_running(self):
        """Ensure Redis container is running"""
        try:
            redis_container = client.containers.get('build_cache_redis')
            if redis_container.status != 'running':
                redis_container.start()
        except docker.errors.NotFound:
            client.containers.run(
                'redis:7-alpine',
                name='build_cache_redis',
                ports={'6379/tcp': 6379},
                detach=True,
                restart_policy={'Name': 'unless-stopped'}
            )
    
    def _start_nginx_cache(self):
        """Start nginx cache proxy container"""
        nginx_config = self._generate_nginx_config()
        
        # Write nginx config to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(nginx_config)
            config_path = f.name
        
        try:
            self.nginx_container = client.containers.run(
                'nginx:alpine',
                name='build_cache_nginx',
                ports={'8080/tcp': 8080},
                volumes={
                    config_path: {'bind': '/etc/nginx/nginx.conf', 'mode': 'ro'},
                    self.cache_volume: {'bind': '/var/cache/nginx', 'mode': 'rw'}
                },
                detach=True,
                restart_policy={'Name': 'unless-stopped'}
            )
        except docker.errors.APIError as e:
            if 'already in use' in str(e):
                self.nginx_container = client.containers.get('build_cache_nginx')
    
    def _generate_nginx_config(self):
        """Generate nginx configuration for build cache"""
        return '''
events {
    worker_connections 1024;
}

http {
    # Cache configuration
    proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=build_cache:100m 
                     max_size=10g inactive=60m use_temp_path=off;
    
    # Upstream for build cache service
    upstream build_cache_backend {
        server host.docker.internal:5003;
    }
    
    server {
        listen 8080;
        
        # Cache build artifacts
        location /cache/ {
            proxy_pass http://build_cache_backend/;
            proxy_cache build_cache;
            proxy_cache_valid 200 60m;
            proxy_cache_valid 404 1m;
            proxy_cache_key "$request_uri";
            
            # Cache headers
            add_header X-Cache-Status $upstream_cache_status;
            add_header X-Cache-Key "$request_uri";
            
            # Allow large uploads
            client_max_body_size 1G;
        }
        
        # Health check
        location /health {
            return 200 "OK";
            add_header Content-Type text/plain;
        }
    }
}
'''
    
    def generate_cache_key(self, project_path, build_config):
        """Generate cache key from project and build configuration"""
        # Hash project files and build config
        hasher = hashlib.sha256()
        
        # Add build config
        hasher.update(json.dumps(build_config, sort_keys=True).encode())
        
        # Add relevant project files
        for root, dirs, files in os.walk(project_path):
            # Skip common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__']]
            
            for file in sorted(files):
                if not file.startswith('.') and not file.endswith('.log'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'rb') as f:
                            hasher.update(f.read())
                    except (IOError, OSError):
                        continue
        
        return hasher.hexdigest()
    
    def store_build_artifact(self, cache_key, artifact_path):
        """Store build artifact in cache"""
        # Create tar archive
        with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as temp_file:
            with tarfile.open(temp_file.name, 'w:gz') as tar:
                tar.add(artifact_path, arcname='.')
            
            # Store in Redis with metadata
            with open(temp_file.name, 'rb') as f:
                artifact_data = f.read()
            
            metadata = {
                'size': len(artifact_data),
                'created': time.time(),
                'path': artifact_path
            }
            
            # Store artifact and metadata
            self.redis_client.set(f"artifact:{cache_key}", artifact_data, ex=3600*24)  # 24h TTL
            self.redis_client.set(f"metadata:{cache_key}", json.dumps(metadata), ex=3600*24)
            
            os.unlink(temp_file.name)
            return True
    
    def retrieve_build_artifact(self, cache_key, output_path):
        """Retrieve build artifact from cache"""
        artifact_data = self.redis_client.get(f"artifact:{cache_key}")
        if not artifact_data:
            return False
        
        # Extract artifact
        with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as temp_file:
            temp_file.write(artifact_data)
            temp_file.flush()
            
            with tarfile.open(temp_file.name, 'r:gz') as tar:
                tar.extractall(output_path)
            
            os.unlink(temp_file.name)
            return True
    
    def build_with_cache(self, project_path, build_config):
        """Build project with cache support"""
        cache_key = self.generate_cache_key(project_path, build_config)
        
        # Check cache first
        if self.redis_client.exists(f"artifact:{cache_key}"):
            return {
                'cache_hit': True,
                'cache_key': cache_key,
                'message': 'Build artifact retrieved from cache'
            }
        
        # Build project
        build_result = self._execute_build(project_path, build_config)
        
        if build_result['success']:
            # Store in cache
            self.store_build_artifact(cache_key, build_result['output_path'])
            
        return {
            'cache_hit': False,
            'cache_key': cache_key,
            'build_result': build_result
        }
    
    def _execute_build(self, project_path, build_config):
        """Execute actual build process"""
        build_command = build_config.get('command', 'npm run build')
        
        try:
            # Run build in container
            container = client.containers.run(
                build_config.get('image', 'node:18-alpine'),
                command=f'sh -c "cd /app && {build_command}"',
                volumes={project_path: {'bind': '/app', 'mode': 'rw'}},
                working_dir='/app',
                detach=True,
                remove=True
            )
            
            # Wait for completion
            result = container.wait()
            logs = container.logs().decode('utf-8')
            
            return {
                'success': result['StatusCode'] == 0,
                'output_path': os.path.join(project_path, build_config.get('output_dir', 'dist')),
                'logs': logs,
                'exit_code': result['StatusCode']
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# Flask endpoints
cache_proxy = BuildCacheProxy()

@app.route('/build', methods=['POST'])
def build_project():
    data = request.json
    project_path = data.get('project_path')
    build_config = data.get('build_config', {})
    
    if not project_path or not os.path.exists(project_path):
        return jsonify({'error': 'Invalid project path'}), 400
    
    result = cache_proxy.build_with_cache(project_path, build_config)
    return jsonify(result)

@app.route('/cache/<cache_key>', methods=['GET'])
def get_cached_artifact(cache_key):
    """Retrieve cached build artifact"""
    metadata = cache_proxy.redis_client.get(f"metadata:{cache_key}")
    if not metadata:
        return jsonify({'error': 'Cache key not found'}), 404
    
    metadata = json.loads(metadata)
    
    with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as temp_file:
        if cache_proxy.retrieve_build_artifact(cache_key, temp_file.name):
            return send_file(temp_file.name, as_attachment=True, 
                           download_name=f'build_{cache_key[:8]}.tar.gz')
    
    return jsonify({'error': 'Failed to retrieve artifact'}), 500

@app.route('/cache/stats', methods=['GET'])
def cache_stats():
    """Get cache statistics"""
    keys = cache_proxy.redis_client.keys('metadata:*')
    total_size = 0
    
    for key in keys:
        metadata = json.loads(cache_proxy.redis_client.get(key))
        total_size += metadata.get('size', 0)
    
    return jsonify({
        'total_artifacts': len(keys),
        'total_size_bytes': total_size,
        'total_size_mb': round(total_size / (1024*1024), 2)
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'service': 'build_cache_proxy'})

@app.route('/ready')
def ready():
    return jsonify({'status': 'ready', 'service': 'build_cache_proxy'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True)
