#!/usr/bin/env python3
"""
Container Management and Cloud/Network Features for CodeSandbox Portfolio
"""

import docker
import json
import os
from pathlib import Path
from flask import Flask, request, jsonify
import subprocess
import threading

app = Flask(__name__)
client = docker.from_env()

def build_docker_image(project_path, image_name):
    """Build a Docker image for a project"""
    try:
        # Change to project directory
        original_cwd = os.getcwd()
        os.chdir(project_path)
        
        # Build image
        image, build_logs = client.images.build(
            path=".",
            tag=image_name,
            rm=True,  # Remove intermediate containers
            forcerm=True  # Force removal of intermediate containers
        )
        
        # Print build logs
        for log in build_logs:
            if 'stream' in log:
                print(log['stream'].strip())
        
        os.chdir(original_cwd)
        return True, f"Image {image_name} built successfully"
    except Exception as e:
        os.chdir(original_cwd)
        return False, f"Error building image: {str(e)}"

def run_docker_container(image_name, port):
    """Run a Docker container with specified port mapping"""
    try:
        container = client.containers.run(
            image_name,
            ports={'80/tcp': port},  # Map container port 80 to host port
            detach=True,
            environment={'PORT': port}
        )
        return True, f"Container {container.id[:12]} started successfully"
    except Exception as e:
        return False, f"Error running container: {str(e)}"

def stop_docker_container(container_name):
    """Stop a running Docker container"""
    try:
        container = client.containers.get(container_name)
        container.stop()
        container.remove()
        return True, f"Container {container_name} stopped and removed"
    except Exception as e:
        return False, f"Error stopping container: {str(e)}"

@app.route('/containers/build', methods=['POST'])
def build_container():
    """Build a Docker container for a project"""
    data = request.json
    project_path = data.get('project_path')
    image_name = data.get('image_name')
    
    if not project_path or not image_name:
        return jsonify({'error': 'Missing project_path or image_name'}), 400
    
    success, message = build_docker_image(project_path, image_name)
    if success:
        return jsonify({'message': message}), 200
    else:
        return jsonify({'error': message}), 500

@app.route('/containers/run', methods=['POST'])
def run_container():
    """Run a Docker container"""
    data = request.json
    image_name = data.get('image_name')
    port = data.get('port')
    
    if not image_name or not port:
        return jsonify({'error': 'Missing image_name or port'}), 400
    
    success, message = run_docker_container(image_name, port)
    if success:
        return jsonify({'message': message}), 200
    else:
        return jsonify({'error': message}), 500

@app.route('/containers/stop', methods=['POST'])
def stop_container():
    """Stop a Docker container"""
    data = request.json
    container_name = data.get('container_name')
    
    if not container_name:
        return jsonify({'error': 'Missing container_name'}), 400
    
    success, message = stop_docker_container(container_name)
    if success:
        return jsonify({'message': message}), 200
    else:
        return jsonify({'error': message}), 500

@app.route('/containers/list', methods=['GET'])
def list_containers():
    """List all running containers"""
    try:
        containers = client.containers.list()
        container_list = []
        for container in containers:
            container_info = {
                'id': container.id[:12],
                'name': container.name,
                'image': container.image.tags[0] if container.image.tags else 'N/A',
                'status': container.status,
                'ports': container.ports
            }
            container_list.append(container_info)
        
        return jsonify(container_list), 200
    except Exception as e:
        return jsonify({'error': f'Error listing containers: {str(e)}'}), 500

@app.route('/network/create', methods=['POST'])
def create_network():
    """Create a Docker network for projects"""
    data = request.json
    network_name = data.get('network_name', 'project-network')
    
    try:
        network = client.networks.create(network_name, driver="bridge")
        return jsonify({'message': f'Network {network_name} created', 'id': network.id}), 200
    except Exception as e:
        return jsonify({'error': f'Error creating network: {str(e)}'}), 500

@app.route('/network/list', methods=['GET'])
def list_networks():
    """List all Docker networks"""
    try:
        networks = client.networks.list()
        network_list = []
        for network in networks:
            network_info = {
                'name': network.name,
                'id': network.id,
                'driver': network.attrs.get('Driver', 'N/A'),
                'containers': len(network.containers)
            }
            network_list.append(network_info)
        
        return jsonify(network_list), 200
    except Exception as e:
        return jsonify({'error': f'Error listing networks: {str(e)}'}), 500

if __name__ == '__main__':
    # Run on port 8000 for container management
    app.run(host='0.0.0.0', port=8000, debug=True)