#!/usr/bin/env python3
"""
Project Preview Generation System
Captures screenshots of running projects for preview thumbnails
"""

import os
import time
import json
import requests
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
import io

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
        # Fallback options - try different browsers
        try:
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            firefox_options = FirefoxOptions()
            firefox_options.add_argument("--headless")
            driver = webdriver.Firefox(options=firefox_options)
            return driver
        except:
            print("Could not setup any browser driver for screenshots")
            return None

def capture_screenshot(driver, url, output_path):
    """Capture screenshot of the given URL"""
    try:
        driver.get(url)
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2)  # Additional wait for dynamic content
        
        # Take screenshot
        driver.save_screenshot(output_path)
        print(f"Screenshot saved: {output_path}")
        return True
    except Exception as e:
        print(f"Error capturing screenshot for {url}: {e}")
        return False

def resize_image(input_path, output_path, size=(400, 300)):
    """Resize image to thumbnail size"""
    try:
        with Image.open(input_path) as img:
            # Maintain aspect ratio
            img.thumbnail(size, Image.LANCZOS)
            img.save(output_path, "PNG")
        return True
    except Exception as e:
        print(f"Error resizing image: {e}")
        return False

def generate_previews():
    """Generate previews for all running projects"""
    # Read projects.json to get running projects
    try:
        with open('projects.json', 'r') as f:
            projects = json.load(f)
    except FileNotFoundError:
        print("projects.json not found, skipping preview generation")
        return
    
    # Setup browser driver
    driver = setup_chrome_driver()
    if not driver:
        print("No browser driver available, skipping preview generation")
        return
    
    try:
        # Create previews directory
        previews_dir = Path('previews')
        previews_dir.mkdir(exist_ok=True)
        
        for project in projects:
            if project.get('status') == 'running' and project.get('url'):
                project_name = project['name']
                project_url = project['url']
                
                # Define preview paths
                full_size_path = previews_dir / f"{project_name}_full.png"
                thumb_path = previews_dir / f"{project_name}_thumb.png"
                
                print(f"Capturing preview for {project_name} at {project_url}")
                
                # Capture full-size screenshot
                if capture_screenshot(driver, project_url, str(full_size_path)):
                    # Create thumbnail
                    resize_image(str(full_size_path), str(thumb_path))
                    
                    # Update project with preview path
                    project['preview_image'] = f"previews/{project_name}_thumb.png"
    
    finally:
        driver.quit()
    
    # Save updated projects.json with preview paths
    with open('projects.json', 'w') as f:
        json.dump(projects, f, indent=2)

def generate_static_previews():
    """Generate previews for static HTML files"""
    # This function would generate previews for static projects that aren't running
    # by starting a temporary server and taking screenshots
    pass

if __name__ == "__main__":
    generate_previews()