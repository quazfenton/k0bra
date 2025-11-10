from flask import Flask, request, redirect
import subprocess
import threading
import os

app = Flask(__name__)

@app.route('/launch')
def launch_project():
    project_path = request.args.get('project')
    if not project_path:
        return "Project path missing", 400

    # Run the launch script in a separate thread
    threading.Thread(target=run_project, args=(project_path,)).start()
    return redirect(f"http://localhost:9110/{project_path}")

def run_project(project_path):
    # Use the launch_project.sh script to start the project
    subprocess.run(["./launch_project.sh", project_path])

if __name__ == '__main__':
    app.run(port=5000)