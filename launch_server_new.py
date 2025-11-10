from flask import Flask, request, jsonify
import subprocess
import threading
import os
import time
import signal
from datetime import datetime

app = Flask(__name__)

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
        return f"Project already running at {running_projects[project_path]}", 200

    # Run the launch script in a new thread
    def run_project():
        # Use absolute path to launch_project.sh
        script_path = os.path.join(os.getcwd(), 'launch_project.sh')
        result = subprocess.run([script_path, project_path], check=True, capture_output=True, text=True)
        # Extract port from output
        port_line = [line for line in result.stdout.split('\n') if line.startswith('PORT:')]
        port = int(port_line[0].split(':')[1]) if port_line else 9110

        # Store complete project info
        running_projects[project_path] = {
            'url': f"http://localhost:{port}/",
            'start_time': datetime.now(),
            'path': project_path,
            'port': port
        }

    thread = threading.Thread(target=run_project)
    thread.daemon = True
    thread.start()

    # Wait briefly for project info to be stored
    time.sleep(0.5)
    if project_path in running_projects:
        return running_projects[project_path]['url'], 200
    return "Project launch in progress", 202

@app.route('/status')
def project_status():
    return jsonify(running_projects), 200

def cleanup(signum, frame):
    """Clean up running projects when receiving termination signals"""
    for project in running_projects.values():
        try:
            # Read PID from project directory
            pid_file = os.path.join(project['path'], '.pid')
            if os.path.exists(pid_file):
                pid = int(open(pid_file).read())
                os.kill(pid, signal.SIGTERM)
            
            # Kill processes running on the project port
            subprocess.run(['fuser', '-k', f"{project['port']}/tcp"], stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Error cleaning up project {project['path']}: {e}")
            continue

# Register signal handlers
signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

if __name__ == '__main__':
    app.run(port=6110)