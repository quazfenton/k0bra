#!/usr/bin/env python3
"""
UI Screenshot Capture Service for Containerized Applications
Captures screenshots of running web applications in containers
"""

import docker
import time
import os
import json
import base64
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, request, jsonify, send_file
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
import requests

app = Flask(__name__)
client = docker.from_env()

class ScreenshotCapture:
    def __init__(self):
        self.chrome_options = self._setup_chrome_options()
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.screenshot_cache = {}
    
    def _setup_chrome_options(self):
        """Setup Chrome options for headless screenshot capture"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')  # Faster loading
        return options
    
    def capture_url(self, url, wait_time=3, viewport_size=(1920, 1080)):
        """Capture screenshot of URL"""
        driver = None
        try:
            # Setup driver with custom viewport
            options = self.chrome_options
            options.add_argument(f'--window-size={viewport_size[0]},{viewport_size[1]}')
            
            driver = webdriver.Chrome(options=options)
            driver.set_window_size(*viewport_size)
            
            # Navigate and wait
            driver.get(url)
            time.sleep(wait_time)
            
            # Wait for page to be ready
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            
            # Capture screenshot
            screenshot_path = tempfile.mktemp(suffix='.png')
            driver.save_screenshot(screenshot_path)
            
            return screenshot_path
            
        except Exception as e:
            return None
        finally:
            if driver:
                driver.quit()
    
    def capture_container_app(self, container_id, port=None, path='/', wait_time=5):
        """Capture screenshot of containerized application"""
        try:
            container = client.containers.get(container_id)
            
            # Get container port mapping
            if not port:
                ports = container.attrs['NetworkSettings']['Ports']
                for container_port, host_bindings in ports.items():
                    if host_bindings:
                        port = host_bindings[0]['HostPort']
                        break
            
            if not port:
                return {'error': 'No accessible port found'}
            
            # Wait for service to be ready
            url = f'http://localhost:{port}{path}'
            self._wait_for_service(url, timeout=30)
            
            # Capture screenshot
            screenshot_path = self.capture_url(url, wait_time)
            
            if screenshot_path:
                return {
                    'success': True,
                    'screenshot_path': screenshot_path,
                    'url': url,
                    'container_id': container_id
                }
            else:
                return {'error': 'Failed to capture screenshot'}
                
        except Exception as e:
            return {'error': str(e)}
    
    def _wait_for_service(self, url, timeout=30):
        """Wait for service to be accessible"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code < 500:
                    return True
            except:
                pass
            time.sleep(1)
        return False
    
    def capture_multiple_viewports(self, url, viewports=None):
        """Capture screenshots at multiple viewport sizes"""
        if not viewports:
            viewports = [
                (1920, 1080),  # Desktop
                (1366, 768),   # Laptop
                (768, 1024),   # Tablet
                (375, 667)     # Mobile
            ]
        
        screenshots = {}
        for viewport in viewports:
            screenshot_path = self.capture_url(url, viewport_size=viewport)
            if screenshot_path:
                screenshots[f'{viewport[0]}x{viewport[1]}'] = screenshot_path
        
        return screenshots
    
    def create_comparison_image(self, screenshots, labels=None):
        """Create side-by-side comparison of screenshots"""
        if not screenshots:
            return None
        
        images = []
        for path in screenshots.values():
            if os.path.exists(path):
                img = Image.open(path)
                images.append(img)
        
        if not images:
            return None
        
        # Calculate dimensions for grid layout
        cols = min(2, len(images))
        rows = (len(images) + cols - 1) // cols
        
        max_width = max(img.width for img in images)
        max_height = max(img.height for img in images)
        
        # Create comparison image
        comparison_width = max_width * cols + 20 * (cols - 1)
        comparison_height = max_height * rows + 20 * (rows - 1) + 50  # Extra space for labels
        
        comparison = Image.new('RGB', (comparison_width, comparison_height), 'white')
        
        # Paste images
        for i, img in enumerate(images):
            row = i // cols
            col = i % cols
            
            x = col * (max_width + 20)
            y = row * (max_height + 50) + 30  # Space for label
            
            comparison.paste(img, (x, y))
            
            # Add label if provided
            if labels and i < len(labels):
                draw = ImageDraw.Draw(comparison)
                try:
                    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 16)
                except:
                    font = ImageFont.load_default()
                
                draw.text((x, y - 25), labels[i], fill='black', font=font)
        
        # Save comparison
        comparison_path = tempfile.mktemp(suffix='.png')
        comparison.save(comparison_path)
        
        return comparison_path
    
    def batch_capture(self, urls, wait_time=3):
        """Capture screenshots of multiple URLs in parallel"""
        futures = []
        for url in urls:
            future = self.executor.submit(self.capture_url, url, wait_time)
            futures.append((url, future))
        
        results = {}
        for url, future in futures:
            try:
                screenshot_path = future.result(timeout=60)
                results[url] = screenshot_path
            except Exception as e:
                results[url] = None
        
        return results

class ContainerScreenshotManager:
    """Manage screenshots for all running containers"""
    
    def __init__(self):
        self.capture = ScreenshotCapture()
        self.monitoring_thread = None
        self.auto_capture = False
    
    def start_monitoring(self, interval=300):  # 5 minutes
        """Start automatic screenshot monitoring"""
        self.auto_capture = True
        self.monitoring_thread = threading.Thread(target=self._monitor_containers, args=(interval,))
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
    
    def _monitor_containers(self, interval):
        """Monitor containers and capture screenshots periodically"""
        while self.auto_capture:
            try:
                containers = client.containers.list()
                for container in containers:
                    # Check if container has web service
                    ports = container.attrs['NetworkSettings']['Ports']
                    if ports:
                        self.capture_container_screenshot(container.id)
            except Exception as e:
                print(f"Monitoring error: {e}")
            
            time.sleep(interval)
    
    def capture_container_screenshot(self, container_id):
        """Capture screenshot for specific container"""
        result = self.capture.capture_container_app(container_id)
        
        if result.get('success'):
            # Store screenshot info
            screenshot_info = {
                'container_id': container_id,
                'screenshot_path': result['screenshot_path'],
                'url': result['url'],
                'timestamp': time.time()
            }
            
            # Cache for quick access
            self.capture.screenshot_cache[container_id] = screenshot_info
            
        return result
    
    def get_all_screenshots(self):
        """Get screenshots for all running containers"""
        containers = client.containers.list()
        results = {}
        
        for container in containers:
            result = self.capture_container_app(container.id)
            results[container.id] = result
        
        return results

# Flask endpoints
screenshot_manager = ContainerScreenshotManager()

@app.route('/screenshot/url', methods=['POST'])
def screenshot_url():
    data = request.json
    url = data.get('url')
    wait_time = data.get('wait_time', 3)
    viewports = data.get('viewports')
    
    if not url:
        return jsonify({'error': 'URL required'}), 400
    
    if viewports:
        screenshots = screenshot_manager.capture.capture_multiple_viewports(url, viewports)
        return jsonify({'screenshots': screenshots})
    else:
        screenshot_path = screenshot_manager.capture.capture_url(url, wait_time)
        if screenshot_path:
            return send_file(screenshot_path, mimetype='image/png')
        else:
            return jsonify({'error': 'Failed to capture screenshot'}), 500

@app.route('/screenshot/container/<container_id>', methods=['POST'])
def screenshot_container(container_id):
    data = request.json or {}
    port = data.get('port')
    path = data.get('path', '/')
    wait_time = data.get('wait_time', 5)
    
    result = screenshot_manager.capture.capture_container_app(container_id, port, path, wait_time)
    
    if result.get('success'):
        return send_file(result['screenshot_path'], mimetype='image/png')
    else:
        return jsonify(result), 500

@app.route('/screenshot/batch', methods=['POST'])
def batch_screenshot():
    data = request.json
    urls = data.get('urls', [])
    wait_time = data.get('wait_time', 3)
    
    results = screenshot_manager.capture.batch_capture(urls, wait_time)
    
    # Convert file paths to base64 for JSON response
    encoded_results = {}
    for url, path in results.items():
        if path and os.path.exists(path):
            with open(path, 'rb') as f:
                encoded_results[url] = base64.b64encode(f.read()).decode()
        else:
            encoded_results[url] = None
    
    return jsonify({'screenshots': encoded_results})

@app.route('/screenshot/containers', methods=['GET'])
def screenshot_all_containers():
    results = screenshot_manager.get_all_screenshots()
    return jsonify(results)

@app.route('/screenshot/monitor/start', methods=['POST'])
def start_monitoring():
    data = request.json or {}
    interval = data.get('interval', 300)
    
    screenshot_manager.start_monitoring(interval)
    return jsonify({'message': 'Monitoring started', 'interval': interval})

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'service': 'screenshot_service'})

@app.route('/ready')
def ready():
    return jsonify({'status': 'ready', 'service': 'screenshot_service'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True)
