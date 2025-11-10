#!/usr/bin/env python3
"""
Service Orchestrator for Enhanced k0bra System
Manages all advanced containerization and cloud execution services
"""

import subprocess
import time
import requests
import json
import threading
from flask import Flask, request, jsonify
import logging
import os
import signal
import sys

app = Flask(__name__)

class ServiceOrchestrator:
    def __init__(self):
        self.services = {
            'sandbox_executor': {
                'port': 5001,
                'script': 'sandbox_executor.py',
                'process': None,
                'status': 'stopped'
            },
            'microvm_manager': {
                'port': 5002,
                'script': 'microvm_manager.py',
                'process': None,
                'status': 'stopped'
            },
            'build_cache_proxy': {
                'port': 5003,
                'script': 'build_cache_proxy.py',
                'process': None,
                'status': 'stopped'
            },
            'cloud_runners': {
                'port': 5004,
                'script': 'cloud_runners.py',
                'process': None,
                'status': 'stopped'
            },
            'screenshot_service': {
                'port': 5005,
                'script': 'screenshot_service.py',
                'process': None,
                'status': 'stopped'
            },
            'telemetry_monitor': {
                'port': 5006,
                'script': 'telemetry_monitor.py',
                'process': None,
                'status': 'stopped'
            }
        }
        
        self.monitoring_thread = None
        self.monitoring_active = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def start_service(self, service_name):
        """Start a specific service"""
        if service_name not in self.services:
            return False, f"Unknown service: {service_name}"
        
        service = self.services[service_name]
        
        if service['process'] and service['process'].poll() is None:
            return False, f"Service {service_name} is already running"
        
        try:
            # Start the service
            service['process'] = subprocess.Popen([
                sys.executable, service['script']
            ], cwd=os.path.dirname(os.path.abspath(__file__)))
            
            # Wait a moment and check if it started successfully
            time.sleep(2)
            
            if service['process'].poll() is None:
                service['status'] = 'running'
                logging.info(f"Started service: {service_name}")
                return True, f"Service {service_name} started successfully"
            else:
                service['status'] = 'failed'
                return False, f"Service {service_name} failed to start"
                
        except Exception as e:
            service['status'] = 'failed'
            return False, f"Error starting {service_name}: {str(e)}"
    
    def stop_service(self, service_name):
        """Stop a specific service"""
        if service_name not in self.services:
            return False, f"Unknown service: {service_name}"
        
        service = self.services[service_name]
        
        if not service['process'] or service['process'].poll() is not None:
            service['status'] = 'stopped'
            return True, f"Service {service_name} is not running"
        
        try:
            service['process'].terminate()
            
            # Wait for graceful shutdown
            try:
                service['process'].wait(timeout=10)
            except subprocess.TimeoutExpired:
                service['process'].kill()
                service['process'].wait()
            
            service['status'] = 'stopped'
            service['process'] = None
            logging.info(f"Stopped service: {service_name}")
            return True, f"Service {service_name} stopped successfully"
            
        except Exception as e:
            return False, f"Error stopping {service_name}: {str(e)}"
    
    def restart_service(self, service_name):
        """Restart a specific service"""
        stop_success, stop_msg = self.stop_service(service_name)
        if stop_success:
            time.sleep(1)  # Brief pause
            return self.start_service(service_name)
        else:
            return False, stop_msg
    
    def start_all_services(self):
        """Start all services in dependency order"""
        # Start services in order of dependencies
        service_order = [
            'telemetry_monitor',  # Start monitoring first
            'build_cache_proxy',  # Cache service
            'sandbox_executor',   # Basic execution
            'microvm_manager',    # Secure execution
            'cloud_runners',      # Cloud execution
            'screenshot_service'  # UI capture
        ]
        
        results = {}
        for service_name in service_order:
            success, message = self.start_service(service_name)
            results[service_name] = {'success': success, 'message': message}
            
            if success:
                time.sleep(2)  # Stagger startup
        
        # Start health monitoring
        self.start_monitoring()
        
        return results
    
    def stop_all_services(self):
        """Stop all services"""
        self.stop_monitoring()
        
        results = {}
        for service_name in self.services.keys():
            success, message = self.stop_service(service_name)
            results[service_name] = {'success': success, 'message': message}
        
        return results
    
    def get_service_status(self, service_name=None):
        """Get status of services"""
        if service_name:
            if service_name not in self.services:
                return None
            
            service = self.services[service_name]
            is_running = service['process'] and service['process'].poll() is None
            
            status = {
                'name': service_name,
                'status': 'running' if is_running else 'stopped',
                'port': service['port'],
                'health': self._check_service_health(service_name) if is_running else 'down'
            }
            
            return status
        else:
            # Return status for all services
            statuses = {}
            for name in self.services.keys():
                statuses[name] = self.get_service_status(name)
            
            return statuses
    
    def _check_service_health(self, service_name):
        """Check if service is responding to health checks"""
        service = self.services[service_name]
        
        try:
            response = requests.get(
                f"http://localhost:{service['port']}/health",
                timeout=5
            )
            return 'healthy' if response.status_code == 200 else 'unhealthy'
        except:
            return 'unreachable'
    
    def start_monitoring(self):
        """Start service health monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitor_services, daemon=True)
        self.monitoring_thread.start()
        logging.info("Started service monitoring")
    
    def stop_monitoring(self):
        """Stop service health monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logging.info("Stopped service monitoring")
    
    def _monitor_services(self):
        """Monitor service health and restart if needed"""
        while self.monitoring_active:
            for service_name, service in self.services.items():
                if service['status'] == 'running':
                    # Check if process is still alive
                    if not service['process'] or service['process'].poll() is not None:
                        logging.warning(f"Service {service_name} died, restarting...")
                        self.start_service(service_name)
                    
                    # Check health endpoint
                    elif self._check_service_health(service_name) == 'unreachable':
                        logging.warning(f"Service {service_name} is unreachable, restarting...")
                        self.restart_service(service_name)
            
            time.sleep(30)  # Check every 30 seconds
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logging.info(f"Received signal {signum}, shutting down...")
        self.stop_all_services()
        sys.exit(0)
    
    def get_system_overview(self):
        """Get comprehensive system overview"""
        service_statuses = self.get_service_status()
        
        # Count services by status
        running_count = sum(1 for s in service_statuses.values() if s['status'] == 'running')
        healthy_count = sum(1 for s in service_statuses.values() if s['health'] == 'healthy')
        
        # Get telemetry summary if available
        telemetry_summary = None
        if service_statuses['telemetry_monitor']['status'] == 'running':
            try:
                response = requests.get('http://localhost:5006/metrics/summary', timeout=5)
                if response.status_code == 200:
                    telemetry_summary = response.json()
            except:
                pass
        
        return {
            'services': service_statuses,
            'summary': {
                'total_services': len(self.services),
                'running_services': running_count,
                'healthy_services': healthy_count,
                'monitoring_active': self.monitoring_active
            },
            'telemetry': telemetry_summary,
            'timestamp': time.time()
        }

# Global orchestrator instance
orchestrator = ServiceOrchestrator()

# Flask endpoints
@app.route('/orchestrator/start/<service_name>', methods=['POST'])
def start_service_endpoint(service_name):
    success, message = orchestrator.start_service(service_name)
    return jsonify({'success': success, 'message': message})

@app.route('/orchestrator/stop/<service_name>', methods=['POST'])
def stop_service_endpoint(service_name):
    success, message = orchestrator.stop_service(service_name)
    return jsonify({'success': success, 'message': message})

@app.route('/orchestrator/restart/<service_name>', methods=['POST'])
def restart_service_endpoint(service_name):
    success, message = orchestrator.restart_service(service_name)
    return jsonify({'success': success, 'message': message})

@app.route('/orchestrator/start-all', methods=['POST'])
def start_all_services():
    results = orchestrator.start_all_services()
    return jsonify(results)

@app.route('/orchestrator/stop-all', methods=['POST'])
def stop_all_services():
    results = orchestrator.stop_all_services()
    return jsonify(results)

@app.route('/orchestrator/status')
def get_status():
    service_name = request.args.get('service')
    status = orchestrator.get_service_status(service_name)
    return jsonify(status)

@app.route('/orchestrator/overview')
def get_overview():
    overview = orchestrator.get_system_overview()
    return jsonify(overview)

@app.route('/orchestrator/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'orchestrator': 'running',
        'timestamp': time.time()
    })

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting k0bra Service Orchestrator...")
    
    # Start orchestrator API
    app.run(host='0.0.0.0', port=5000, debug=False)
