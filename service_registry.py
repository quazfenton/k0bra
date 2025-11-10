#!/usr/bin/env python3
"""
Service Registry and Project Dependencies Manager
"""

import json
from flask import Flask, request, jsonify
from pathlib import Path
import subprocess
import os
import threading
import time

app = Flask(__name__)

class ServiceRegistry:
    def __init__(self):
        self.services = {}
        self.dependencies = {}
        self.service_ports = {}
        self.load_services()
    
    def load_services(self):
        """Load services from configuration file"""
        try:
            with open('services.json', 'r') as f:
                self.services = json.load(f)
        except FileNotFoundError:
            # Default services configuration
            self.services = {
                'database': {
                    'service': 'postgresql',
                    'port': 5432,
                    'env_vars': ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASS']
                },
                'cache': {
                    'service': 'redis',
                    'port': 6379,
                    'env_vars': ['REDIS_HOST', 'REDIS_PORT']
                },
                'message_queue': {
                    'service': 'rabbitmq',
                    'port': 5672,
                    'env_vars': ['RABBITMQ_HOST', 'RABBITMQ_PORT']
                }
            }
    
    def save_services(self):
        """Save services to configuration file"""
        with open('services.json', 'w') as f:
            json.dump(self.services, f, indent=2)
    
    def start_service(self, service_name):
        """Start a service using Docker or system service"""
        service_info = self.services.get(service_name)
        if not service_info:
            return False, f"Service {service_name} not found"
        
        service_type = service_info['service']
        
        try:
            if service_type == 'postgresql':
                # Start PostgreSQL with Docker
                cmd = [
                    'docker', 'run', '-d', 
                    '--name', f'cs-postgres-{service_name}',
                    '-e', 'POSTGRES_DB=codesandbox',
                    '-e', 'POSTGRES_USER=cs_user', 
                    '-e', 'POSTGRES_PASSWORD=cs_pass',
                    '-p', f'{service_info["port"]}:5432',
                    'postgres:13'
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    return False, f"Failed to start PostgreSQL: {result.stderr}"
            
            elif service_type == 'redis':
                # Start Redis with Docker
                cmd = [
                    'docker', 'run', '-d',
                    '--name', f'cs-redis-{service_name}',
                    '-p', f'{service_info["port"]}:6379',
                    'redis:alpine'
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    return False, f"Failed to start Redis: {result.stderr}"
            
            elif service_type == 'rabbitmq':
                # Start RabbitMQ with Docker
                cmd = [
                    'docker', 'run', '-d',
                    '--name', f'cs-rabbit-{service_name}',
                    '-p', f'{service_info["port"]}:5672',
                    'rabbitmq:3-management'
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    return False, f"Failed to start RabbitMQ: {result.stderr}"
            
            return True, f"Service {service_name} started successfully"
        
        except Exception as e:
            return False, f"Error starting service {service_name}: {str(e)}"
    
    def stop_service(self, service_name):
        """Stop a service"""
        service_info = self.services.get(service_name)
        if not service_info:
            return False, f"Service {service_name} not found"
        
        try:
            # Stop Docker container
            container_name = f'cs-{service_info["service"]}-{service_name}'
            cmd = ['docker', 'stop', container_name]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return False, f"Failed to stop service {service_name}: {result.stderr}"
            
            # Remove container
            cmd = ['docker', 'rm', container_name]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            return True, f"Service {service_name} stopped successfully"
        
        except Exception as e:
            return False, f"Error stopping service {service_name}: {str(e)}"

registry = ServiceRegistry()

@app.route('/services/list', methods=['GET'])
def list_services():
    """List all available services"""
    return jsonify(registry.services), 200

@app.route('/services/start', methods=['POST'])
def start_service():
    """Start a service"""
    data = request.json
    service_name = data.get('service_name')
    
    if not service_name:
        return jsonify({'error': 'Missing service_name'}), 400
    
    success, message = registry.start_service(service_name)
    if success:
        return jsonify({'message': message}), 200
    else:
        return jsonify({'error': message}), 500

@app.route('/services/stop', methods=['POST'])
def stop_service():
    """Stop a service"""
    data = request.json
    service_name = data.get('service_name')
    
    if not service_name:
        return jsonify({'error': 'Missing service_name'}), 400
    
    success, message = registry.stop_service(service_name)
    if success:
        return jsonify({'message': message}), 200
    else:
        return jsonify({'error': message}), 500

@app.route('/dependencies/analyze', methods=['POST'])
def analyze_dependencies():
    """Analyze project dependencies"""
    data = request.json
    project_path = data.get('project_path')
    
    if not project_path:
        return jsonify({'error': 'Missing project_path'}), 400
    
    deps = {
        'project_path': project_path,
        'dependencies': [],
        'dev_dependencies': [],
        'security_issues': [],
        'outdated_packages': []
    }
    
    # Analyze based on project type
    if Path(project_path).joinpath('package.json').exists():
        try:
            with open(Path(project_path) / 'package.json', 'r') as f:
                package_data = json.load(f)
            
            deps['dependencies'] = list(package_data.get('dependencies', {}).keys())
            deps['dev_dependencies'] = list(package_data.get('devDependencies', {}).keys())
            
            # Run npm audit to check for security issues
            result = subprocess.run(
                ['npm', 'audit', '--json'], 
                cwd=project_path, 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                try:
                    audit_data = json.loads(result.stdout)
                    deps['security_issues'] = audit_data.get('vulnerabilities', {})
                    deps['outdated_packages'] = audit_data.get('metadata', {}).get('dependencies', {})
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            return jsonify({'error': f'Error analyzing Node.js project: {str(e)}'}), 500
    
    elif Path(project_path).joinpath('requirements.txt').exists():
        try:
            with open(Path(project_path) / 'requirements.txt', 'r') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    dep = line.split('==')[0].split('>=')[0].split('<=')[0]
                    deps['dependencies'].append(dep)
            
            # Run pip-audit to check for security issues
            result = subprocess.run(
                ['pip', 'list', '--outdated', '--format', 'json'], 
                cwd=project_path, 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                try:
                    outdated_data = json.loads(result.stdout)
                    deps['outdated_packages'] = outdated_data
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            return jsonify({'error': f'Error analyzing Python project: {str(e)}'}), 500
    
    return jsonify(deps), 200

@app.route('/dependencies/install', methods=['POST'])
def install_dependencies():
    """Install project dependencies"""
    data = request.json
    project_path = data.get('project_path')
    
    if not project_path:
        return jsonify({'error': 'Missing project_path'}), 400
    
    try:
        # Determine project type and install dependencies
        if Path(project_path).joinpath('package.json').exists():
            result = subprocess.run(
                ['npm', 'install'], 
                cwd=project_path, 
                capture_output=True, 
                text=True
            )
            
            if result.returncode != 0:
                return jsonify({'error': f'npm install failed: {result.stderr}'}), 500
        elif Path(project_path).joinpath('requirements.txt').exists():
            result = subprocess.run(
                ['pip', 'install', '-r', 'requirements.txt'], 
                cwd=project_path, 
                capture_output=True, 
                text=True
            )
            
            if result.returncode != 0:
                return jsonify({'error': f'pip install failed: {result.stderr}'}), 500
        else:
            return jsonify({'error': 'No package.json or requirements.txt found'}), 400
        
        return jsonify({'message': 'Dependencies installed successfully'}), 200
    except Exception as e:
        return jsonify({'error': f'Error installing dependencies: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)