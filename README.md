# k0bra - Advanced Code Execution & Portfolio Platform

A comprehensive frontend/backend sandbox portfolio with **advanced containerization**, **cloud execution**, and **enterprise-grade monitoring**. All projects run locally by default, with optional cloud scaling and secure isolation.

## 🚀 Enhanced Features

### Core Capabilities
- **Frontend Portfolio**: Bulk app rendering and site visualization
- **Backend Development**: GUI-based modularity and low-code platforming
- **Local-First**: All services run on localhost (127.0.0.1) by default
- **Cloud-Ready**: Optional scaling to Modal, AWS Lambda, and Kubernetes

### Advanced Features ✨
- **🔒 Sandboxed Execution**: Docker containers with resource limits (128MB RAM, 0.5 CPU, 30s timeout)
- **🛡️ MicroVM Security**: Firecracker integration for ultra-secure code isolation
- **⚡ Build Caching**: Redis + nginx proxy for CI/CD acceleration
- **☁️ Cloud Runners**: Modal.com + AWS Lambda with auto-platform selection
- **📸 UI Screenshots**: Multi-viewport capture (desktop/tablet/mobile)
- **📊 Telemetry**: Prometheus metrics, alerts, and resource monitoring
- **🎛️ Orchestration**: Kubernetes deployment with auto-scaling

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Dashboard     │    │  Orchestrator   │    │   Telemetry     │
│   :9111         │    │   :5000         │    │    :5006        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
    ┌────────────────────────────┼────────────────────────────┐
    │                            │                            │
┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
│Sandbox  │  │MicroVM  │  │ Cache   │  │ Cloud   │  │Screenshot│
│ :5001   │  │ :5002   │  │ :5003   │  │ :5004   │  │ :5005   │
└─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘
```

## 🛠️ Supported Frameworks

- **Frontend**: React, Vue, Angular, Svelte/SvelteKit, Next.js, Nuxt
- **Backend**: Express, NestJS, Flask, Django, Go, Rust, Ruby on Rails
- **Languages**: Python, Node.js, TypeScript, Go, Rust, PHP, Ruby
- **Cloud**: Modal.com, AWS Lambda, Kubernetes

## 📦 Installation

### Quick Start (Local)
```bash
git clone <repository>
cd k0bra

# Install dependencies
pip install -r requirements.txt

# Start enhanced system
./start-enhanced.sh
```

### Kubernetes Deployment
```bash
# Deploy to cluster
./deploy-k8s.sh

# Access at https://k0bra.example.com
```

## 🎯 Usage

### Local Development
```bash
# Start all services
./start-enhanced.sh

# Access dashboard
open http://localhost:9111

# Monitor system
curl http://localhost:5000/orchestrator/overview
```

### API Examples

#### Execute Code (Sandboxed)
```bash
curl -X POST http://localhost:5001/execute \
  -H "Content-Type: application/json" \
  -d '{"code": "print(\"Hello k0bra!\")", "language": "python"}'
```

#### Cloud Execution
```bash
curl -X POST http://localhost:5004/cloud/execute \
  -H "Content-Type: application/json" \
  -d '{"code": "import numpy as np; print(np.array([1,2,3]))", "language": "python", "platform": "modal"}'
```

#### Screenshot Capture
```bash
curl -X POST http://localhost:5005/screenshot/url \
  -H "Content-Type: application/json" \
  -d '{"url": "http://localhost:3000", "viewports": [[1920,1080], [375,667]]}'
```

#### Build Caching
```bash
curl -X POST http://localhost:5003/build \
  -H "Content-Type: application/json" \
  -d '{"project_path": "/path/to/project", "build_config": {"command": "npm run build"}}'
```

## 🔧 Service Endpoints

| Service | Port | Purpose | Health Check |
|---------|------|---------|--------------|
| **Dashboard** | 9111 | Main portfolio interface | `/` |
| **Orchestrator** | 5000 | Service management | `/orchestrator/health` |
| **Sandbox** | 5001 | Docker code execution | `/health` |
| **MicroVM** | 5002 | Firecracker isolation | `/health` |
| **Cache** | 5003 | Build artifact caching | `/health` |
| **Cloud** | 5004 | Modal/Lambda runners | `/health` |
| **Screenshots** | 5005 | UI capture service | `/health` |
| **Telemetry** | 5006 | Metrics & monitoring | `/metrics/health` |

## 📊 Monitoring & Observability

### Prometheus Metrics
```bash
# System metrics
curl http://localhost:5006/metrics/prometheus

# Service overview
curl http://localhost:5000/orchestrator/overview

# Cache statistics
curl http://localhost:5003/cache/stats
```

### Alerts & Thresholds
- **CPU Usage**: > 80%
- **Memory Usage**: > 90% of limit
- **Execution Timeout**: > 5 minutes
- **Error Rate**: > 10%

## 🔒 Security Features

- **Container Isolation**: Docker + cgroups resource limits
- **MicroVM Sandboxing**: Firecracker for kernel-level isolation
- **Network Restrictions**: No external access for code execution
- **Resource Limits**: CPU, memory, and timeout constraints
- **Read-only Filesystems**: Immutable execution environments

## ☁️ Cloud Integration

### Modal.com
- GPU/ML workload support
- Long-running tasks (5-10 minutes)
- Auto-scaling based on demand

### AWS Lambda
- Fast cold starts
- Pay-per-request pricing
- Automatic platform selection

### Kubernetes
- Horizontal pod autoscaling
- Rolling deployments
- SSL termination with cert-manager

## 🏃‍♂️ Performance

- **Build Cache Hit Rate**: ~80% typical
- **Execution Latency**: <2s for simple code
- **Screenshot Generation**: <5s per viewport
- **Concurrent Executions**: 10+ per service
- **Memory Efficiency**: 128MB per sandbox

## 🔧 Configuration

### Environment Variables
```bash
# Cloud providers
export MODAL_API_TOKEN="your-token"
export AWS_LAMBDA_ROLE_ARN="arn:aws:iam::..."

# Resource limits
export MAX_CONCURRENT_EXECUTIONS=10
export EXECUTION_TIMEOUT=30
export CACHE_TTL=86400

# Monitoring
export PROMETHEUS_ENABLED=true
export ALERT_WEBHOOK_URL="https://..."
```

### Service Configuration
```python
# Resource thresholds
thresholds = {
    'cpu_high': 80.0,
    'memory_high': 0.9,
    'execution_timeout': 300,
    'error_rate_high': 0.1
}
```

## 🚀 Scaling

### Local Scaling
- Multiple service instances
- Load balancing with nginx
- Redis clustering

### Cloud Scaling
- Kubernetes horizontal pod autoscaler
- Modal.com auto-scaling
- AWS Lambda concurrency limits

## 🛠️ Development

### Adding New Languages
1. Update `sandbox_executor.py` with new Dockerfile
2. Add language detection in `framework_detector.py`
3. Update cloud runner configurations

### Custom Execution Platforms
1. Implement platform class in `cloud_runners.py`
2. Add platform selection logic
3. Update API documentation

## 📝 API Documentation

### Service Management
- `POST /orchestrator/start-all` - Start all services
- `GET /orchestrator/overview` - System status
- `POST /orchestrator/stop-all` - Stop all services

### Code Execution
- `POST /execute` - Sandbox execution
- `POST /microvm/execute` - MicroVM execution
- `POST /cloud/execute` - Cloud execution

### Build & Cache
- `POST /build` - Build with caching
- `GET /cache/stats` - Cache statistics
- `GET /cache/<key>` - Retrieve artifact

### Monitoring
- `GET /metrics/summary` - System metrics
- `GET /metrics/alerts` - Recent alerts
- `POST /metrics/execution` - Record execution

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request

## 📄 License

MIT License - see LICENSE file for details

---

**k0bra** - Advanced code execution platform with enterprise-grade security, monitoring, and cloud integration.
