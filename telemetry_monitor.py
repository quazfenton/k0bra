#!/usr/bin/env python3
"""
Telemetry and Resource Monitoring for Container Execution
Provides real-time metrics, alerts, and performance analytics
"""

import docker
import psutil
import time
import json
import threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from collections import defaultdict, deque
import redis
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge, generate_latest

app = Flask(__name__)
client = docker.from_env()

# Prometheus metrics
CONTAINER_EXECUTIONS = Counter('k0bra_container_executions_total', 'Total container executions', ['language', 'status'])
EXECUTION_DURATION = Histogram('k0bra_execution_duration_seconds', 'Execution duration', ['language'])
ACTIVE_CONTAINERS = Gauge('k0bra_active_containers', 'Number of active containers')
MEMORY_USAGE = Gauge('k0bra_memory_usage_bytes', 'Memory usage by container', ['container_id'])
CPU_USAGE = Gauge('k0bra_cpu_usage_percent', 'CPU usage by container', ['container_id'])
CACHE_HIT_RATE = Gauge('k0bra_cache_hit_rate', 'Build cache hit rate')

@dataclass
class ContainerMetrics:
    container_id: str
    name: str
    status: str
    cpu_percent: float
    memory_usage: int
    memory_limit: int
    network_rx: int
    network_tx: int
    block_read: int
    block_write: int
    timestamp: float

@dataclass
class ExecutionMetrics:
    execution_id: str
    language: str
    platform: str
    start_time: float
    end_time: Optional[float]
    duration: Optional[float]
    status: str
    memory_peak: int
    cpu_peak: float
    error_message: Optional[str]

class TelemetryCollector:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=1)
        self.metrics_history = defaultdict(lambda: deque(maxlen=1000))
        self.execution_history = deque(maxlen=10000)
        self.alerts = deque(maxlen=100)
        self.monitoring_active = False
        self.collection_interval = 5  # seconds
        
        # Thresholds for alerts
        self.thresholds = {
            'cpu_high': 80.0,
            'memory_high': 0.9,  # 90% of limit
            'execution_timeout': 300,  # 5 minutes
            'error_rate_high': 0.1  # 10%
        }
    
    def start_monitoring(self):
        """Start continuous monitoring"""
        self.monitoring_active = True
        
        # Start collection threads
        threading.Thread(target=self._collect_container_metrics, daemon=True).start()
        threading.Thread(target=self._collect_system_metrics, daemon=True).start()
        threading.Thread(target=self._process_alerts, daemon=True).start()
        
        logging.info("Telemetry monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring_active = False
        logging.info("Telemetry monitoring stopped")
    
    def _collect_container_metrics(self):
        """Collect metrics from all containers"""
        while self.monitoring_active:
            try:
                containers = client.containers.list()
                active_count = 0
                
                for container in containers:
                    if container.status == 'running':
                        active_count += 1
                        metrics = self._get_container_metrics(container)
                        if metrics:
                            self._store_metrics(metrics)
                            self._update_prometheus_metrics(metrics)
                
                ACTIVE_CONTAINERS.set(active_count)
                
            except Exception as e:
                logging.error(f"Error collecting container metrics: {e}")
            
            time.sleep(self.collection_interval)
    
    def _get_container_metrics(self, container) -> Optional[ContainerMetrics]:
        """Get detailed metrics for a single container"""
        try:
            stats = container.stats(stream=False)
            
            # Calculate CPU percentage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            
            cpu_percent = 0.0
            if system_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * \
                             len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100.0
            
            # Memory metrics
            memory_usage = stats['memory_stats']['usage']
            memory_limit = stats['memory_stats']['limit']
            
            # Network metrics
            network_rx = network_tx = 0
            if 'networks' in stats:
                for interface in stats['networks'].values():
                    network_rx += interface['rx_bytes']
                    network_tx += interface['tx_bytes']
            
            # Block I/O metrics
            block_read = block_write = 0
            if 'blkio_stats' in stats and 'io_service_bytes_recursive' in stats['blkio_stats']:
                for entry in stats['blkio_stats']['io_service_bytes_recursive']:
                    if entry['op'] == 'Read':
                        block_read += entry['value']
                    elif entry['op'] == 'Write':
                        block_write += entry['value']
            
            return ContainerMetrics(
                container_id=container.id[:12],
                name=container.name,
                status=container.status,
                cpu_percent=cpu_percent,
                memory_usage=memory_usage,
                memory_limit=memory_limit,
                network_rx=network_rx,
                network_tx=network_tx,
                block_read=block_read,
                block_write=block_write,
                timestamp=time.time()
            )
            
        except Exception as e:
            logging.error(f"Error getting metrics for container {container.id}: {e}")
            return None
    
    def _collect_system_metrics(self):
        """Collect system-wide metrics"""
        while self.monitoring_active:
            try:
                # System CPU and memory
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                system_metrics = {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available': memory.available,
                    'disk_percent': disk.percent,
                    'disk_free': disk.free,
                    'timestamp': time.time()
                }
                
                self.metrics_history['system'].append(system_metrics)
                self.redis_client.lpush('system_metrics', json.dumps(system_metrics))
                self.redis_client.ltrim('system_metrics', 0, 999)  # Keep last 1000
                
            except Exception as e:
                logging.error(f"Error collecting system metrics: {e}")
            
            time.sleep(self.collection_interval)
    
    def _store_metrics(self, metrics: ContainerMetrics):
        """Store metrics in Redis and memory"""
        metrics_dict = asdict(metrics)
        
        # Store in Redis
        key = f"container_metrics:{metrics.container_id}"
        self.redis_client.lpush(key, json.dumps(metrics_dict))
        self.redis_client.ltrim(key, 0, 999)  # Keep last 1000 entries
        self.redis_client.expire(key, 3600)  # 1 hour TTL
        
        # Store in memory for quick access
        self.metrics_history[metrics.container_id].append(metrics_dict)
    
    def _update_prometheus_metrics(self, metrics: ContainerMetrics):
        """Update Prometheus metrics"""
        MEMORY_USAGE.labels(container_id=metrics.container_id).set(metrics.memory_usage)
        CPU_USAGE.labels(container_id=metrics.container_id).set(metrics.cpu_percent)
    
    def _process_alerts(self):
        """Process alerts based on thresholds"""
        while self.monitoring_active:
            try:
                self._check_resource_alerts()
                self._check_execution_alerts()
                self._check_error_rate_alerts()
                
            except Exception as e:
                logging.error(f"Error processing alerts: {e}")
            
            time.sleep(30)  # Check every 30 seconds
    
    def _check_resource_alerts(self):
        """Check for resource usage alerts"""
        for container_id, metrics_list in self.metrics_history.items():
            if not metrics_list:
                continue
                
            latest_metrics = metrics_list[-1]
            
            # CPU alert
            if latest_metrics['cpu_percent'] > self.thresholds['cpu_high']:
                self._create_alert('high_cpu', {
                    'container_id': container_id,
                    'cpu_percent': latest_metrics['cpu_percent'],
                    'threshold': self.thresholds['cpu_high']
                })
            
            # Memory alert
            memory_ratio = latest_metrics['memory_usage'] / latest_metrics['memory_limit']
            if memory_ratio > self.thresholds['memory_high']:
                self._create_alert('high_memory', {
                    'container_id': container_id,
                    'memory_ratio': memory_ratio,
                    'threshold': self.thresholds['memory_high']
                })
    
    def _check_execution_alerts(self):
        """Check for execution-related alerts"""
        recent_executions = [e for e in self.execution_history 
                           if time.time() - e.get('start_time', 0) < 3600]  # Last hour
        
        for execution in recent_executions:
            if execution.get('duration', 0) > self.thresholds['execution_timeout']:
                self._create_alert('execution_timeout', {
                    'execution_id': execution.get('execution_id'),
                    'duration': execution.get('duration'),
                    'threshold': self.thresholds['execution_timeout']
                })
    
    def _check_error_rate_alerts(self):
        """Check for high error rates"""
        recent_executions = [e for e in self.execution_history 
                           if time.time() - e.get('start_time', 0) < 3600]  # Last hour
        
        if len(recent_executions) > 10:  # Only check if we have enough data
            error_count = sum(1 for e in recent_executions if e.get('status') == 'error')
            error_rate = error_count / len(recent_executions)
            
            if error_rate > self.thresholds['error_rate_high']:
                self._create_alert('high_error_rate', {
                    'error_rate': error_rate,
                    'error_count': error_count,
                    'total_executions': len(recent_executions),
                    'threshold': self.thresholds['error_rate_high']
                })
    
    def _create_alert(self, alert_type: str, data: dict):
        """Create and store alert"""
        alert = {
            'type': alert_type,
            'timestamp': time.time(),
            'data': data,
            'severity': self._get_alert_severity(alert_type)
        }
        
        self.alerts.append(alert)
        self.redis_client.lpush('alerts', json.dumps(alert))
        self.redis_client.ltrim('alerts', 0, 99)  # Keep last 100 alerts
        
        logging.warning(f"Alert created: {alert_type} - {data}")
    
    def _get_alert_severity(self, alert_type: str) -> str:
        """Get severity level for alert type"""
        severity_map = {
            'high_cpu': 'warning',
            'high_memory': 'warning',
            'execution_timeout': 'error',
            'high_error_rate': 'critical'
        }
        return severity_map.get(alert_type, 'info')
    
    def record_execution(self, execution_metrics: ExecutionMetrics):
        """Record execution metrics"""
        execution_dict = asdict(execution_metrics)
        self.execution_history.append(execution_dict)
        
        # Store in Redis
        self.redis_client.lpush('execution_metrics', json.dumps(execution_dict))
        self.redis_client.ltrim('execution_metrics', 0, 9999)  # Keep last 10k
        
        # Update Prometheus metrics
        if execution_metrics.end_time:
            EXECUTION_DURATION.labels(language=execution_metrics.language).observe(
                execution_metrics.duration or 0
            )
        
        CONTAINER_EXECUTIONS.labels(
            language=execution_metrics.language,
            status=execution_metrics.status
        ).inc()
    
    def get_metrics_summary(self, time_range: int = 3600) -> dict:
        """Get metrics summary for specified time range"""
        cutoff_time = time.time() - time_range
        
        # Container metrics summary
        active_containers = []
        for container_id, metrics_list in self.metrics_history.items():
            recent_metrics = [m for m in metrics_list if m['timestamp'] > cutoff_time]
            if recent_metrics:
                latest = recent_metrics[-1]
                avg_cpu = sum(m['cpu_percent'] for m in recent_metrics) / len(recent_metrics)
                avg_memory = sum(m['memory_usage'] for m in recent_metrics) / len(recent_metrics)
                
                active_containers.append({
                    'container_id': container_id,
                    'name': latest['name'],
                    'status': latest['status'],
                    'current_cpu': latest['cpu_percent'],
                    'average_cpu': avg_cpu,
                    'current_memory': latest['memory_usage'],
                    'average_memory': avg_memory,
                    'memory_limit': latest['memory_limit']
                })
        
        # Execution metrics summary
        recent_executions = [e for e in self.execution_history if e.get('start_time', 0) > cutoff_time]
        
        execution_summary = {
            'total_executions': len(recent_executions),
            'successful_executions': sum(1 for e in recent_executions if e.get('status') == 'success'),
            'failed_executions': sum(1 for e in recent_executions if e.get('status') == 'error'),
            'average_duration': sum(e.get('duration', 0) for e in recent_executions) / max(len(recent_executions), 1),
            'languages': {}
        }
        
        # Language breakdown
        for execution in recent_executions:
            lang = execution.get('language', 'unknown')
            if lang not in execution_summary['languages']:
                execution_summary['languages'][lang] = {'count': 0, 'success': 0, 'error': 0}
            
            execution_summary['languages'][lang]['count'] += 1
            if execution.get('status') == 'success':
                execution_summary['languages'][lang]['success'] += 1
            elif execution.get('status') == 'error':
                execution_summary['languages'][lang]['error'] += 1
        
        # Recent alerts
        recent_alerts = [a for a in self.alerts if a['timestamp'] > cutoff_time]
        
        return {
            'time_range_seconds': time_range,
            'active_containers': active_containers,
            'execution_summary': execution_summary,
            'recent_alerts': recent_alerts,
            'system_health': self._get_system_health()
        }
    
    def _get_system_health(self) -> dict:
        """Get current system health status"""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent,
                'status': 'healthy' if cpu_percent < 80 and memory.percent < 80 and disk.percent < 90 else 'warning'
            }
        except:
            return {'status': 'unknown'}

# Global telemetry collector
telemetry = TelemetryCollector()

# Flask endpoints
@app.route('/metrics/prometheus')
def prometheus_metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/metrics/summary')
def metrics_summary():
    """Get metrics summary"""
    time_range = request.args.get('time_range', 3600, type=int)
    summary = telemetry.get_metrics_summary(time_range)
    return jsonify(summary)

@app.route('/metrics/container/<container_id>')
def container_metrics(container_id):
    """Get metrics for specific container"""
    metrics = telemetry.metrics_history.get(container_id, [])
    return jsonify({'container_id': container_id, 'metrics': list(metrics)})

@app.route('/metrics/alerts')
def get_alerts():
    """Get recent alerts"""
    return jsonify({'alerts': list(telemetry.alerts)})

@app.route('/metrics/execution', methods=['POST'])
def record_execution():
    """Record execution metrics"""
    data = request.json
    
    execution_metrics = ExecutionMetrics(
        execution_id=data.get('execution_id'),
        language=data.get('language'),
        platform=data.get('platform'),
        start_time=data.get('start_time'),
        end_time=data.get('end_time'),
        duration=data.get('duration'),
        status=data.get('status'),
        memory_peak=data.get('memory_peak', 0),
        cpu_peak=data.get('cpu_peak', 0.0),
        error_message=data.get('error_message')
    )
    
    telemetry.record_execution(execution_metrics)
    return jsonify({'status': 'recorded'})

@app.route('/metrics/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'monitoring_active': telemetry.monitoring_active,
        'timestamp': time.time()
    })

@app.route('/metrics/start', methods=['POST'])
def start_monitoring():
    """Start telemetry monitoring"""
    if not telemetry.monitoring_active:
        telemetry.start_monitoring()
        return jsonify({'status': 'started'})
    else:
        return jsonify({'status': 'already_running'})

@app.route('/metrics/stop', methods=['POST'])
def stop_monitoring():
    """Stop telemetry monitoring"""
    telemetry.stop_monitoring()
    return jsonify({'status': 'stopped'})

if __name__ == '__main__':
    # Start monitoring automatically
    telemetry.start_monitoring()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    app.run(host='0.0.0.0', port=5006, debug=True)
