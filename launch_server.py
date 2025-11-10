from flask import Flask, request, jsonify
import subprocess
import threading
import os
import time
import signal
from datetime import datetime
import json
import requests

app = Flask(__name__)

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

# Store running projects to avoid multiple starts
running_projects = {}

@app.route('/launch')
def launch_project():
    project_path = request.args.get('project')
    if not project_path:
        return "Project path missing", 400

    # Normalize and check path exists
    project_path = os.path.normpath(project_path)
    if not os.path.exists(project_path):
        return "Project not found", 404

    # Check if already running
    if project_path in running_projects:
        # Return the URL of the running project
        return running_projects[project_path]['url'], 200

    # Run the launch script in a new thread
    def run_project():
        # Use absolute path to launch_project.sh
        script_path = os.path.join(os.getcwd(), 'launch_project.sh')
        process = subprocess.Popen([script_path, project_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

        # Read output line by line until we get the PORT
        port = None
        for line in iter(process.stdout.readline, ''):
            if line.startswith('PORT:'):
                port_str = line.split(':')[1].strip()
                if port_str and port_str.isdigit():
                    port = int(port_str)
                    break
                else:
                    print(f"Invalid port number: '{port_str}'")
                    # We break anyway because we don't want to keep reading
                    break

        # If we didn't get a port, try to read the rest and log an error
        if port is None:
            # Read the rest of the output
            remaining_output = process.stdout.read()
            error_msg = f"Failed to get port for project {project_path}. Output: {remaining_output}"
            print(error_msg)
            # Also log to launch.log for better debugging
            with open('launch.log', 'a') as log_file:
                log_file.write(f"{datetime.now()} - {error_msg}\n")
            
            # Try to get port from the .pid file in the project directory as fallback
            pid_file = os.path.join(project_path, '.pid')
            if os.path.exists(pid_file):
                try:
                    with open(pid_file, 'r') as f:
                        pid = f.read().strip()
                    # Get the port from the process listening on that pid
                    port_cmd = f"lsof -i -P -n -p {pid} | grep LISTEN | awk '{{print $9}}' | cut -d':' -f2 | head -1"
                    port_result = subprocess.run(port_cmd, shell=True, capture_output=True, text=True)
                    if port_result.returncode == 0:
                        port_output = port_result.stdout.strip()
                        if port_output and port_output.isdigit():
                            port = int(port_output)
                            print(f"Fallback port detection using .pid: {port}")
                        else:
                            port = None
                    else:
                        port = None
                except Exception as e:
                    print(f"Fallback port detection failed: {e}")
                    port = None
            else:
                port = None
            
            if not port:
                # Still no port, give up
                return

        # Store complete project info
        running_projects[project_path] = {
            'url': f"http://localhost:{port}",
            'start_time': datetime.now(),
            'path': project_path,
            'port': port,
            'project_name': os.path.basename(project_path)
        }

        # Regenerate projects.json to update status
        try:
            requests.post('http://localhost:9111/regenerate-projects', timeout=10)
        except Exception as e:
            print(f"Error regenerating projects after launch: {e}")

    thread = threading.Thread(target=run_project)
    thread.daemon = True
    thread.start()

    # Wait for the thread to start and potentially set the project info
    time.sleep(0.5)
    if project_path in running_projects:
        return running_projects[project_path]['url'], 200
    else:
        return "Project launch in progress. Please try again in a moment.", 202

@app.route('/stop')
def stop_project():
    project_path = request.args.get('project')
    if not project_path:
        return "Project path missing", 400

    project_path = os.path.normpath(project_path)
    
    if project_path not in running_projects:
        return "Project is not running", 404

    project_info = running_projects[project_path]
    
    try:
        # Read PID from project directory
        pid_file = os.path.join(project_path, '.pid')
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Kill the process
            os.kill(pid, signal.SIGTERM)
            
            # Remove the PID file
            os.remove(pid_file)
        
        # Release the port
        release_response = requests.post('http://localhost:4110/release-port', json={
            'port': project_info['port'],
            'project_path': project_path
        })
        
        if release_response.status_code == 200:
            # Remove from running projects
            del running_projects[project_path]
            
            # Regenerate projects.json to update status
            try:
                requests.post('http://localhost:9111/regenerate-projects', timeout=10)
            except Exception as e:
                print(f"Error regenerating projects after stop: {e}")
            
            return "Project stopped successfully", 200
        else:
            return "Failed to release port", 500
    except Exception as e:
        return f"Error stopping project: {str(e)}", 500

@app.route('/status')
def project_status():
    return jsonify(running_projects), 200

@app.route('/list')
def list_projects():
    """List all projects with their status"""
    try:
        with open('projects.json', 'r') as f:
            projects = json.load(f)
        return jsonify(projects), 200
    except Exception as e:
        return f"Error reading projects: {str(e)}", 500

def cleanup(signum, frame):
    """Clean up running projects when receiving termination signals"""
    for project_path in list(running_projects.keys()):  # Use list() to avoid modification during iteration
        project = running_projects[project_path]
        try:
            # Read PID from project directory
            pid_file = os.path.join(project['path'], '.pid')
            if os.path.exists(pid_file):
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                try:
                    # Kill only the specific process we started
                    os.kill(pid, signal.SIGTERM)
                except (ProcessLookupError, ValueError):
                    # Process already exited or invalid PID, ignore
                    pass
                # Remove the PID file
                os.remove(pid_file)
        except Exception as e:
            print(f"Error cleaning up project {project['path']}: {e}")
        
        # Release the port
        try:
            data = json.dumps({'project_path': project['path'], 'port': project['port']})
            response = requests.post('http://localhost:4110/release-port', 
                                   data=data, 
                                   headers={'Content-Type': 'application/json'},
                                   timeout=10)
        except Exception as e:
            print(f"Error releasing port for project {project['path']}: {e}")
        
        # Remove from running projects dict
        if project_path in running_projects:
            del running_projects[project_path]

# Register signal handlers
signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

if __name__ == '__main__':
    app.run(port=6110, host='0.0.0.0', debug=True)