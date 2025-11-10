import json
import socket
from flask import Flask, request, jsonify
import threading

app = Flask(__name__)
PORT_FILE = 'port_registry.json'
START_PORT = 3000
END_PORT = 4000
lock = threading.Lock()

def load_registry():
    try:
        with open(PORT_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_registry(registry):
    with open(PORT_FILE, 'w') as f:
        json.dump(registry, f)

def is_port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0

@app.route('/allocate', methods=['POST'])
def allocate_port():
    data = request.get_json()
    project_path = data.get('project_path')
    
    if not project_path:
        return jsonify({'error': 'Missing project_path'}), 400
    
    with lock:
        registry = load_registry()
        
        # Reuse existing allocation if available and port is free
        if project_path in registry:
            port = registry[project_path]
            if is_port_available(port):
                return jsonify({'port': port})
            else:
                # Port is occupied, remove stale entry
                del registry[project_path]
                save_registry(registry)
        
        # Find next available port
        port = START_PORT
        while port <= END_PORT:
            # Skip if port is occupied
            if not is_port_available(port):
                port += 1
                continue
            
            # Skip if port is allocated to another project
            if port in registry.values():
                port += 1
                continue
                
            registry[project_path] = port
            save_registry(registry)
            return jsonify({'port': port})
        
        return jsonify({'error': 'No available ports'}), 500

@app.route('/release-port', methods=['POST'])
def release_port():
    data = request.get_json()
    port = data.get('port')
    project_path = data.get('project_path')
    
    if not project_path or not port:
        return jsonify({'error': 'Missing port or project_path'}), 400
    
    with lock:
        registry = load_registry()
        
        # Validate the project owns the port
        if project_path in registry and registry[project_path] == port:
            del registry[project_path]
            save_registry(registry)
            return jsonify({'status': 'released', 'port': port})
        elif project_path in registry:
            return jsonify({'error': 'Port mismatch for project'}), 400
        else:
            return jsonify({'error': 'Project not found'}), 404

if __name__ == '__main__':
    app.run(port=4110)