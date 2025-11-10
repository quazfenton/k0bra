#!/usr/bin/env python3
"""
Static Project Preview Generator
Creates preview screenshots for static projects by temporarily serving them
"""

import os
import subprocess
import time
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
import threading
import http.server
import socketserver

def setup_chrome_driver():
    """Setup Chrome driver for taking screenshots"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1200,800")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"Error setting up Chrome driver: {e}")
        return None

def start_temp_server(directory, port):
    """Start a temporary HTTP server for the given directory"""
    os.chdir(directory)
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Server started at http://localhost:{port}")
        httpd.serve_forever()

def capture_static_preview(project_path, port=8080):
    """Capture preview of static project by temporarily serving it"""
    driver = setup_chrome_driver()
    if not driver:
        return None
    
    # Start server in a separate thread
    server_thread = threading.Thread(target=start_temp_server, args=(project_path, port))
    server_thread.daemon = True
    server_thread.start()
    
    # Give server time to start
    time.sleep(2)
    
    try:
        url = f"http://localhost:{port}"
        preview_path = f"previews/{Path(project_path).name}_static.png"
        
        driver.get(url)
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(1)  # Additional wait
        
        # Take screenshot
        driver.save_screenshot(preview_path)
        
        # Create thumbnail
        with Image.open(preview_path) as img:
            img.thumbnail((400, 300), Image.LANCZOS)
            thumb_path = f"previews/{Path(project_path).name}_thumb.png"
            img.save(thumb_path, "PNG")
        
        print(f"Static preview saved: {thumb_path}")
        return thumb_path
    except Exception as e:
        print(f"Error capturing static preview for {project_path}: {e}")
        return None
    finally:
        driver.quit()
        # Note: Server thread will continue in background, but should stop when script exits

def generate_static_previews():
    """Generate previews for static projects"""
    try:
        with open('projects.json', 'r') as f:
            projects = json.load(f)
    except FileNotFoundError:
        print("projects.json not found, skipping static preview generation")
        return
    
    # Create previews directory
    previews_dir = Path('previews')
    previews_dir.mkdir(exist_ok=True)
    
    for project in projects:
        if project.get('status') != 'running':  # Only for non-running projects
            project_path = project['path']
            project_type = project.get('type', 'unknown')
            
            # Check if it's a static project type
            static_types = ['html', 'unknown']  # Types that can be served statically
            if project_type in static_types:
                # Check if the project has index.html or similar
                if (Path(project_path) / 'index.html').exists():
                    print(f"Generating static preview for {project['name']}")
                    preview_path = capture_static_preview(project_path)
                    if preview_path:
                        project['preview_image'] = preview_path
    
    # Save updated projects.json
    with open('projects.json', 'w') as f:
        json.dump(projects, f, indent=2)

if __name__ == "__main__":
    generate_static_previews()