#!/usr/bin/env python3
"""
Firecracker MicroVM Manager for Ultra-Secure Code Execution
"""

import json
import subprocess
import tempfile
import os
import time
import threading
from pathlib import Path
import requests

class FirecrackerManager:
    def __init__(self):
        self.vm_instances = {}
        self.base_config = {
            "boot-source": {
                "kernel_image_path": "/opt/firecracker/vmlinux.bin",
                "boot_args": "console=ttyS0 reboot=k panic=1 pci=off"
            },
            "drives": [{
                "drive_id": "rootfs",
                "path_on_host": "/opt/firecracker/rootfs.ext4",
                "is_root_device": True,
                "is_read_only": False
            }],
            "machine-config": {
                "vcpu_count": 1,
                "mem_size_mib": 128,
                "ht_enabled": False
            },
            "network-interfaces": []  # No network for security
        }
    
    def create_vm_config(self, vm_id, code, language):
        """Create VM configuration with injected code"""
        config = self.base_config.copy()
        
        # Create temporary rootfs with code
        rootfs_path = f"/tmp/rootfs_{vm_id}.ext4"
        self._prepare_rootfs(rootfs_path, code, language)
        
        config["drives"][0]["path_on_host"] = rootfs_path
        return config
    
    def _prepare_rootfs(self, rootfs_path, code, language):
        """Prepare minimal rootfs with code"""
        # Copy base rootfs
        subprocess.run([
            "cp", "/opt/firecracker/base_rootfs.ext4", rootfs_path
        ], check=True)
        
        # Mount and inject code
        mount_point = f"/tmp/mount_{os.path.basename(rootfs_path)}"
        os.makedirs(mount_point, exist_ok=True)
        
        try:
            subprocess.run(["sudo", "mount", "-o", "loop", rootfs_path, mount_point], check=True)
            
            # Write code file
            file_extensions = {'python': 'py', 'node': 'js', 'go': 'go'}
            filename = f"main.{file_extensions.get(language, 'txt')}"
            code_path = os.path.join(mount_point, "home", filename)
            
            with open(code_path, 'w') as f:
                f.write(code)
            
            # Set execution script
            exec_script = self._get_exec_script(language, filename)
            with open(os.path.join(mount_point, "home", "run.sh"), 'w') as f:
                f.write(exec_script)
            
            os.chmod(os.path.join(mount_point, "home", "run.sh"), 0o755)
            
        finally:
            subprocess.run(["sudo", "umount", mount_point], check=False)
            os.rmdir(mount_point)
    
    def _get_exec_script(self, language, filename):
        """Get execution script for different languages"""
        scripts = {
            'python': f'#!/bin/sh\ncd /home\npython3 {filename}\n',
            'node': f'#!/bin/sh\ncd /home\nnode {filename}\n',
            'go': f'#!/bin/sh\ncd /home\ngo run {filename}\n'
        }
        return scripts.get(language, f'#!/bin/sh\ncd /home\ncat {filename}\n')
    
    def start_vm(self, vm_id, config):
        """Start Firecracker VM"""
        socket_path = f"/tmp/firecracker_{vm_id}.socket"
        config_path = f"/tmp/config_{vm_id}.json"
        
        # Write config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Start Firecracker
        process = subprocess.Popen([
            "firecracker",
            "--api-sock", socket_path,
            "--config-file", config_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        self.vm_instances[vm_id] = {
            'process': process,
            'socket': socket_path,
            'config_path': config_path,
            'start_time': time.time()
        }
        
        return vm_id
    
    def execute_in_vm(self, vm_id, timeout=30):
        """Execute code in VM and get output"""
        if vm_id not in self.vm_instances:
            return {'error': 'VM not found'}
        
        vm = self.vm_instances[vm_id]
        start_time = time.time()
        
        # Wait for VM to boot and execute
        try:
            stdout, stderr = vm['process'].communicate(timeout=timeout)
            execution_time = time.time() - start_time
            
            return {
                'output': stdout.decode('utf-8'),
                'error': stderr.decode('utf-8'),
                'execution_time': execution_time,
                'exit_code': vm['process'].returncode
            }
        except subprocess.TimeoutExpired:
            vm['process'].kill()
            return {'error': 'Execution timeout', 'timeout': True}
        finally:
            self.cleanup_vm(vm_id)
    
    def cleanup_vm(self, vm_id):
        """Clean up VM resources"""
        if vm_id in self.vm_instances:
            vm = self.vm_instances[vm_id]
            
            # Kill process if still running
            if vm['process'].poll() is None:
                vm['process'].kill()
            
            # Clean up files
            for path in [vm['socket'], vm['config_path']]:
                if os.path.exists(path):
                    os.unlink(path)
            
            # Clean up rootfs
            rootfs_path = f"/tmp/rootfs_{vm_id}.ext4"
            if os.path.exists(rootfs_path):
                os.unlink(rootfs_path)
            
            del self.vm_instances[vm_id]

class MicroVMExecutor:
    def __init__(self):
        self.firecracker = FirecrackerManager()
    
    def execute_code(self, code, language, timeout=30):
        """Execute code in MicroVM"""
        vm_id = f"vm_{int(time.time() * 1000)}"
        
        try:
            # Create VM config
            config = self.firecracker.create_vm_config(vm_id, code, language)
            
            # Start VM
            self.firecracker.start_vm(vm_id, config)
            
            # Execute and get result
            result = self.firecracker.execute_in_vm(vm_id, timeout)
            
            return result
            
        except Exception as e:
            self.firecracker.cleanup_vm(vm_id)
            return {'error': f'MicroVM execution failed: {str(e)}'}

# Integration with existing sandbox
def create_microvm_endpoint():
    """Create Flask endpoint for MicroVM execution"""
    from flask import Flask, request, jsonify
    
    app = Flask(__name__)
    executor = MicroVMExecutor()
    
    @app.route('/microvm/execute', methods=['POST'])
    def execute_microvm():
        data = request.json
        code = data.get('code', '')
        language = data.get('language', 'python')
        timeout = data.get('timeout', 30)
        
        result = executor.execute_code(code, language, timeout)
        return jsonify(result)
    
    @app.route('/health')
    def health():
        return jsonify({'status': 'healthy', 'service': 'microvm_manager'})
    
    @app.route('/ready')
    def ready():
        return jsonify({'status': 'ready', 'service': 'microvm_manager'})
    
    return app

if __name__ == '__main__':
    app = create_microvm_endpoint()
    app.run(host='0.0.0.0', port=5002, debug=True)
