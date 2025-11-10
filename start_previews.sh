#!/bin/bash

# Clean up any existing processes more selectively
pkill -f "python3 port_registry.py" || true
pkill -f "python3 launch_server.py" || true
pkill -f "python3 dashboard_server.py" || true
# Don't kill all npm processes - too aggressive

# Check if virtual environment exists, if not create it
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start servers in the background and log their output
python3 port_registry.py > port_registry.log 2>&1 &
sleep 1
python3 launch_server.py > launch_server.log 2>&1 &
sleep 1
python3 dashboard_server.py > dashboard_server.log 2>&1 &

# Generate initial projects list
python3 generate_projects_json.py

# Fix projects
if [ -f "fix_projects.sh" ]; then
    ./fix_projects.sh
fi

# Start preview manager if it exists
if [ -f "preview_manager.sh" ]; then
    ./preview_manager.sh &
fi

# Add cleanup handler
trap "pkill -f 'python3 port_registry.py'; pkill -f 'python3 launch_server.py'; pkill -f 'python3 dashboard_server.py'; pkill -f 'npm run dev'; exit" SIGINT SIGTERM

# Keep the script running to maintain background processes
while true; do sleep 1; done