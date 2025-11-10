from flask import Flask, send_from_directory, jsonify, redirect, request
import subprocess
import requests
import json
import os
from pathlib import Path
import time
from datetime import datetime

app = Flask(__name__)

# Serve dashboard files (index.html, projects.json, etc.)
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/healthcheck')
def healthcheck():
    return jsonify({"status": "ok"})

@app.route('/projects.json')
def projects_json():
    return send_from_directory('.', 'projects.json')

# Serve projects under /projects/<project_name>
@app.route('/projects/<path:project_name>/', defaults={'filename': 'index.html'})
@app.route('/projects/<path:project_name>/<path:filename>')
def serve_project(project_name, filename):
    # Security: Ensure project_name is a valid directory name
    if '..' in project_name or project_name.startswith('.'):
        return "Invalid project", 404

    # Check if the project is running and has an allocated port
    try:
        with open('projects.json', 'r') as f:
            projects_data = json.load(f)
            for project in projects_data:
                if project['path'] == project_name and project.get('status') == 'running' and project.get('port'):
                    # Redirect to the running project's port (local only)
                    return redirect(f"http://localhost:{project['port']}/{filename}", code=302)
    except (FileNotFoundError, json.JSONDecodeError):
        pass # projects.json not found or invalid, treat as static

    # If not running or no port, serve as static from local directory
    project_path = Path(project_name)
    if project_path.is_dir():
        return send_from_directory(str(project_path), filename)
    else:
        return "Project not found", 404

# Regenerate projects.json
@app.route('/regenerate-projects', methods=['POST'])
def regenerate_projects():
    try:
        result = subprocess.run(['python', 'generate_projects_json.py'], check=True, capture_output=True, text=True)
        print(f"Regenerate projects output: {result.stdout}")
        return send_from_directory('.', 'projects.json')
    except subprocess.CalledProcessError as e:
        print(f"Error regenerating projects: {e}")
        return jsonify({"error": f"Failed to regenerate projects: {e}"}), 500

# Launch project endpoint
@app.route('/launch', methods=['GET'])
def launch_project():
    project_path = request.args.get('project')
    if not project_path:
        return "Project path missing", 400
    
    # Call the launch server to start the project
    try:
        response = requests.get(f"http://localhost:6110/launch?project={project_path}")
        if response.status_code == 200:
            return response.text, 200
        else:
            return f"Failed to launch project: {response.text}", response.status_code
    except Exception as e:
        print(f"Error launching project: {e}")
        return f"Error launching project: {e}", 500

# Release port API endpoint
@app.route('/release-port', methods=['POST'])
def release_port():
    data = request.json
    port = data.get('port')
    project_path = data.get('project_path')
    
    # Validate input
    if not port or not project_path:
        return jsonify({"error": "Missing port or project_path"}), 400
    
    # Call port registry to release port
    try:
        release_response = requests.post('http://localhost:4110/release-port', json={
            "port": port,
            "project_path": project_path
        })
        
        if release_response.status_code != 200:
            return jsonify({"error": "Failed to release port"}), 500
        
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error releasing port: {e}")
        return jsonify({"error": f"Failed to release port: {e}"}), 500

# Serve assets directory
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory('assets', filename)

# Serve static files from root
@app.route('/<path:filename>')
def serve_static(filename):
    try:
        return send_from_directory('.', filename)
    except:
        return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    # Run on localhost only for local development
    app.run(port=9111, host='127.0.0.1', debug=True)