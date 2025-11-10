#!/usr/bin/env python3
"""
Cloud Runner Integration for External Code Execution
Supports Modal, AWS Lambda, and other serverless platforms
"""

import json
import requests
import time
import base64
import boto3
import zipfile
import tempfile
import os
from flask import Flask, request, jsonify
from concurrent.futures import ThreadPoolExecutor
import asyncio

app = Flask(__name__)

class ModalRunner:
    """Modal.com integration for GPU/CPU intensive tasks"""
    
    def __init__(self, api_token=None):
        self.api_token = api_token or os.getenv('MODAL_API_TOKEN')
        self.base_url = 'https://api.modal.com/v1'
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
    
    def create_function(self, code, language, requirements=None):
        """Create Modal function from code"""
        function_config = {
            'name': f'k0bra_exec_{int(time.time())}',
            'image': self._get_image_config(language, requirements),
            'code': code,
            'timeout': 300,  # 5 minutes
            'cpu': 1,
            'memory': 1024
        }
        
        response = requests.post(
            f'{self.base_url}/functions',
            headers=self.headers,
            json=function_config
        )
        
        if response.status_code == 201:
            return response.json()['function_id']
        else:
            raise Exception(f'Failed to create Modal function: {response.text}')
    
    def _get_image_config(self, language, requirements):
        """Get Modal image configuration for language"""
        images = {
            'python': {
                'base': 'python:3.11-slim',
                'packages': requirements or ['requests', 'numpy']
            },
            'node': {
                'base': 'node:18-alpine',
                'packages': requirements or []
            },
            'go': {
                'base': 'golang:1.21-alpine',
                'packages': requirements or []
            }
        }
        return images.get(language, images['python'])
    
    def execute_function(self, function_id, inputs=None):
        """Execute Modal function"""
        payload = {
            'inputs': inputs or {},
            'async': False
        }
        
        response = requests.post(
            f'{self.base_url}/functions/{function_id}/invoke',
            headers=self.headers,
            json=payload
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f'Function execution failed: {response.text}')

class AWSLambdaRunner:
    """AWS Lambda integration for serverless execution"""
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda')
        self.s3_client = boto3.client('s3')
        self.bucket_name = 'k0bra-lambda-code'
    
    def create_lambda_function(self, code, language, function_name=None):
        """Create AWS Lambda function"""
        if not function_name:
            function_name = f'k0bra-exec-{int(time.time())}'
        
        # Create deployment package
        zip_buffer = self._create_deployment_package(code, language)
        
        # Create function
        response = self.lambda_client.create_function(
            FunctionName=function_name,
            Runtime=self._get_runtime(language),
            Role=os.getenv('AWS_LAMBDA_ROLE_ARN'),
            Handler=self._get_handler(language),
            Code={'ZipFile': zip_buffer},
            Timeout=300,
            MemorySize=512,
            Environment={
                'Variables': {
                    'EXECUTION_ENV': 'k0bra'
                }
            }
        )
        
        return response['FunctionArn']
    
    def _create_deployment_package(self, code, language):
        """Create Lambda deployment package"""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
            with zipfile.ZipFile(temp_zip.name, 'w') as zip_file:
                # Add main code file
                filename = self._get_filename(language)
                zip_file.writestr(filename, code)
                
                # Add handler wrapper
                handler_code = self._get_handler_code(language)
                zip_file.writestr('lambda_function.py', handler_code)
            
            with open(temp_zip.name, 'rb') as f:
                zip_buffer = f.read()
            
            os.unlink(temp_zip.name)
            return zip_buffer
    
    def _get_runtime(self, language):
        """Get Lambda runtime for language"""
        runtimes = {
            'python': 'python3.11',
            'node': 'nodejs18.x',
            'go': 'go1.x'
        }
        return runtimes.get(language, 'python3.11')
    
    def _get_handler(self, language):
        """Get Lambda handler for language"""
        handlers = {
            'python': 'lambda_function.lambda_handler',
            'node': 'index.handler',
            'go': 'main'
        }
        return handlers.get(language, 'lambda_function.lambda_handler')
    
    def _get_filename(self, language):
        """Get filename for language"""
        filenames = {
            'python': 'main.py',
            'node': 'index.js',
            'go': 'main.go'
        }
        return filenames.get(language, 'main.py')
    
    def _get_handler_code(self, language):
        """Get Lambda handler wrapper code"""
        if language == 'python':
            return '''
import json
import subprocess
import sys

def lambda_handler(event, context):
    try:
        # Execute main.py
        result = subprocess.run([sys.executable, 'main.py'], 
                              capture_output=True, text=True, timeout=30)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'output': result.stdout,
                'error': result.stderr,
                'exit_code': result.returncode
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
'''
        return ''  # Add handlers for other languages as needed
    
    def execute_lambda(self, function_arn, payload=None):
        """Execute Lambda function"""
        response = self.lambda_client.invoke(
            FunctionName=function_arn,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload or {})
        )
        
        result = json.loads(response['Payload'].read())
        return result

class CloudRunnerManager:
    """Unified cloud runner manager"""
    
    def __init__(self):
        self.modal = ModalRunner()
        self.aws_lambda = AWSLambdaRunner()
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    def execute_code(self, code, language, platform='auto', requirements=None):
        """Execute code on specified cloud platform"""
        if platform == 'auto':
            platform = self._select_platform(code, language)
        
        if platform == 'modal':
            return self._execute_on_modal(code, language, requirements)
        elif platform == 'lambda':
            return self._execute_on_lambda(code, language)
        else:
            return {'error': f'Unsupported platform: {platform}'}
    
    def _select_platform(self, code, language):
        """Auto-select best platform based on code characteristics"""
        # Simple heuristics
        if 'numpy' in code or 'tensorflow' in code or 'torch' in code:
            return 'modal'  # Better for ML/scientific computing
        elif len(code) < 1000:
            return 'lambda'  # Good for simple functions
        else:
            return 'modal'  # Better for complex applications
    
    def _execute_on_modal(self, code, language, requirements):
        """Execute on Modal"""
        try:
            function_id = self.modal.create_function(code, language, requirements)
            result = self.modal.execute_function(function_id)
            return {
                'platform': 'modal',
                'function_id': function_id,
                'result': result
            }
        except Exception as e:
            return {'error': f'Modal execution failed: {str(e)}'}
    
    def _execute_on_lambda(self, code, language):
        """Execute on AWS Lambda"""
        try:
            function_arn = self.aws_lambda.create_lambda_function(code, language)
            result = self.aws_lambda.execute_lambda(function_arn)
            return {
                'platform': 'lambda',
                'function_arn': function_arn,
                'result': result
            }
        except Exception as e:
            return {'error': f'Lambda execution failed: {str(e)}'}
    
    def batch_execute(self, jobs):
        """Execute multiple jobs in parallel"""
        futures = []
        for job in jobs:
            future = self.executor.submit(
                self.execute_code,
                job['code'],
                job['language'],
                job.get('platform', 'auto'),
                job.get('requirements')
            )
            futures.append(future)
        
        results = []
        for future in futures:
            try:
                result = future.result(timeout=600)  # 10 minute timeout
                results.append(result)
            except Exception as e:
                results.append({'error': str(e)})
        
        return results

# Flask endpoints
cloud_manager = CloudRunnerManager()

@app.route('/cloud/execute', methods=['POST'])
def execute_cloud():
    data = request.json
    code = data.get('code', '')
    language = data.get('language', 'python')
    platform = data.get('platform', 'auto')
    requirements = data.get('requirements')
    
    result = cloud_manager.execute_code(code, language, platform, requirements)
    return jsonify(result)

@app.route('/cloud/batch', methods=['POST'])
def batch_execute():
    jobs = request.json.get('jobs', [])
    results = cloud_manager.batch_execute(jobs)
    return jsonify({'results': results})

@app.route('/cloud/platforms', methods=['GET'])
def list_platforms():
    return jsonify({
        'platforms': ['modal', 'lambda', 'auto'],
        'languages': ['python', 'node', 'go'],
        'features': {
            'modal': ['GPU support', 'Long running', 'ML libraries'],
            'lambda': ['Fast cold start', 'Pay per request', 'Auto scaling']
        }
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'service': 'cloud_runners'})

@app.route('/ready')
def ready():
    return jsonify({'status': 'ready', 'service': 'cloud_runners'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=True)
