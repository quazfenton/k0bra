#!/usr/bin/env python3
"""
Sandboxed Code Execution Service with Resource Limits
"""

import docker
import json
import time
import threading
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import subprocess
import os
import tempfile
import shutil

app = Flask(__name__)
client = docker.from_env()

class SandboxExecutor:
    def __init__(self):
        self.active_containers = {}
        self.resource_limits = {
            'memory': '128m',
            'cpu_quota': 50000,  # 0.5 CPU
            'timeout': 30,  # seconds
            'network': 'none'  # No network access
        }
    
    def create_sandbox_image(self, language):
        """Create minimal sandbox images for different languages"""
        dockerfiles = {
            'python': '''
FROM python:3.11-alpine
RUN adduser -D -s /bin/sh sandbox
USER sandbox
WORKDIR /app
CMD ["python", "main.py"]
''',
            'node': '''
FROM node:18-alpine
RUN adduser -D -s /bin/sh sandbox
USER sandbox
WORKDIR /app
CMD ["node", "main.js"]
''',
            'go': '''
FROM golang:1.21-alpine
RUN adduser -D -s /bin/sh sandbox
USER sandbox
WORKDIR /app
CMD ["go", "run", "main.go"]
'''
        }
        
        if language not in dockerfiles:
            return False
            
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write(dockerfiles[language])
            dockerfile_path = f.name
        
        try:
            client.images.build(
                fileobj=open(dockerfile_path, 'rb'),
                tag=f'sandbox-{language}:latest',
                rm=True
            )
            os.unlink(dockerfile_path)
            return True
        except Exception as e:
            os.unlink(dockerfile_path)
            return False
    
    def execute_code(self, code, language, timeout=None):
        """Execute code in sandboxed container"""
        if timeout is None:
            timeout = self.resource_limits['timeout']
            
        # Create temporary directory for code
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write code to file
            file_extensions = {'python': 'py', 'node': 'js', 'go': 'go'}
            filename = f"main.{file_extensions.get(language, 'txt')}"
            code_path = os.path.join(temp_dir, filename)
            
            with open(code_path, 'w') as f:
                f.write(code)
            
            try:
                # Run container with strict limits
                container = client.containers.run(
                    f'sandbox-{language}:latest',
                    volumes={temp_dir: {'bind': '/app', 'mode': 'ro'}},
                    mem_limit=self.resource_limits['memory'],
                    cpu_quota=self.resource_limits['cpu_quota'],
                    network_mode=self.resource_limits['network'],
                    detach=True,
                    remove=True
                )
                
                # Wait for completion with timeout
                start_time = time.time()
                while container.status != 'exited' and time.time() - start_time < timeout:
                    time.sleep(0.1)
                    container.reload()
                
                if container.status != 'exited':
                    container.kill()
                    return {'error': 'Execution timeout', 'timeout': True}
                
                # Get output
                logs = container.logs().decode('utf-8')
                exit_code = container.attrs['State']['ExitCode']
                
                return {
                    'output': logs,
                    'exit_code': exit_code,
                    'execution_time': time.time() - start_time
                }
                
            except Exception as e:
                return {'error': str(e)}

@app.route('/execute', methods=['POST'])
def execute_endpoint():
    data = request.json
    code = data.get('code', '')
    language = data.get('language', 'python')
    timeout = data.get('timeout', 30)
    
    executor = SandboxExecutor()
    
    # Ensure sandbox image exists
    if not executor.create_sandbox_image(language):
        return jsonify({'error': 'Failed to create sandbox image'}), 500
    
    result = executor.execute_code(code, language, timeout)
    return jsonify(result)

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'service': 'sandbox_executor'})

@app.route('/ready')
def ready():
    return jsonify({'status': 'ready', 'service': 'sandbox_executor'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
