#!/bin/bash
set -e

# k0bra - Advanced Code Execution & Portfolio Platform
# Comprehensive startup script for the complete k0bra system
# This script starts all services in the proper order with error handling

echo "🚀 Starting Enhanced k0bra System..."
echo "=================================================="

# Configuration
STARTUP_LOG="startup.log"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Function to log messages with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$STARTUP_LOG"
}

# Function to check if a service is running on a port
is_port_free() {
    local port=$1
    if command -v lsof &> /dev/null; then
        ! lsof -i:"$port" -sTCP:LISTEN -t >/dev/null 2>&1
    else
        ! nc -z localhost "$port" >/dev/null 2>&1
    fi
}

# Function to wait for a service to be ready
wait_for_service() {
    local service_name=$1
    local port=$2
    local timeout=30
    local count=0
    
    log_message "Waiting for $service_name (port $port) to be ready..."
    
    while [ $count -lt $timeout ]; do
        if curl -s "http://localhost:$port/health" >/dev/null 2>&1 || [ "$service_name" = "Dashboard Server" -a "$port" = "9111" -a "$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9111)" = "200" ]; then
            log_message "$service_name is ready on port $port"
            return 0
        fi
        sleep 2
        count=$((count + 1))
    done
    
    log_message "ERROR: $service_name failed to start within timeout period"
    return 1
}

# Function to stop all running services by checking ports
stop_existing_services() {
    log_message "Checking for existing running services..."
    
    # Define services and their ports
    local services_ports=("4110" "5000" "5001" "5002" "5003" "5004" "5005" "5006" "6110" "9111")
    
    for port in "${services_ports[@]}"; do
        if ! is_port_free "$port"; then
            log_message "Stopping service on port $port..."
            if command -v lsof &> /dev/null; then
                lsof -i:"$port" -sTCP:LISTEN -t | xargs -r kill -9 2>/dev/null || true
            fi
        fi
    done
    
    # Kill any Python processes that might be related to k0bra services
    pkill -f "port_registry.py\|service_orchestrator.py\|sandbox_executor.py\|microvm_manager.py\|build_cache_proxy.py\|cloud_runners.py\|screenshot_service.py\|telemetry_monitor.py\|launch_server.py\|dashboard_server.py" 2>/dev/null || true
    sleep 2  # Wait for processes to terminate
}

# Check prerequisites
log_message "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    log_message "ERROR: Python 3 not found. Please install Python 3 first."
    exit 1
fi

if ! command -v pip &> /dev/null; then
    log_message "ERROR: pip not found. Please install pip first."
    exit 1
fi

if ! command -v docker &> /dev/null; then
    log_message "ERROR: Docker not found. Please install Docker first."
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    log_message "ERROR: Docker daemon is not running. Please start Docker."
    exit 1
fi

# Stop any existing services to ensure clean startup
log_message "Stopping any existing k0bra services..."
stop_existing_services

# Install dependencies
log_message "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Start Redis if not already running
if ! docker ps | grep -q k0bra-redis; then
    log_message "Starting Redis container..."
    docker run -d --name k0bra-redis -p 6379:6379 --rm redis:7-alpine
    sleep 3
else
    log_message "Redis is already running"
fi

# Start the port registry service (port 4110)
log_message "Starting Port Registry Service (port 4110)..."
if is_port_free 4110; then
    python port_registry.py &
    PORT_REGISTRY_PID=$!
    sleep 2
    if wait_for_service "Port Registry" 4110; then
        log_message "Port Registry started successfully (PID: $PORT_REGISTRY_PID)"
    else
        log_message "ERROR: Port Registry failed to start"
        exit 1
    fi
else
    log_message "Port 4110 is already in use. Please stop the service using that port first."
    exit 1
fi

# Start the service orchestrator (port 5000)
log_message "Starting Service Orchestrator (port 5000)..."
if is_port_free 5000; then
    python service_orchestrator.py &
    ORCHESTRATOR_PID=$!
    sleep 3
    if wait_for_service "Service Orchestrator" 5000; then
        log_message "Service Orchestrator started successfully (PID: $ORCHESTRATOR_PID)"
    else
        log_message "ERROR: Service Orchestrator failed to start"
        exit 1
    fi
else
    log_message "Port 5000 is already in use. Please stop the service using that port first."
    exit 1
fi

# Start the launch server (port 6110)
log_message "Starting Launch Server (port 6110)..."
if is_port_free 6110; then
    python launch_server.py &
    LAUNCH_SERVER_PID=$!
    sleep 2
    if curl -s "http://localhost:6110/status" >/dev/null 2>&1; then
        log_message "Launch Server started successfully (PID: $LAUNCH_SERVER_PID)"
    else
        log_message "WARNING: Launch Server may not be ready yet, continuing..."
    fi
else
    log_message "Port 6110 is already in use. Please stop the service using that port first."
    exit 1
fi

# Start the dashboard server (port 9111)
log_message "Starting Dashboard Server (port 9111)..."
if is_port_free 9111; then
    python dashboard_server.py &
    DASHBOARD_PID=$!
    sleep 2
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:9111 | grep -q "200\|302"; then
        log_message "Dashboard Server started successfully (PID: $DASHBOARD_PID)"
    else
        log_message "WARNING: Dashboard Server may not be ready yet, continuing..."
    fi
else
    log_message "Port 9111 is already in use. Please stop the service using that port first."
    exit 1
fi

# Start all services through the orchestrator
log_message "Starting all orchestrated services via Service Orchestrator..."
curl -s -X POST http://localhost:5000/orchestrator/start-all > /tmp/service_start_result.json 2>&1
if [ $? -eq 0 ]; then
    log_message "Requested all services to start via orchestrator"
else
    log_message "WARNING: Failed to request services start via orchestrator"
fi

# Wait a moment for orchestrated services to start
sleep 5

# Verify all services are running
log_message "Verifying service status..."
curl -s http://localhost:5000/orchestrator/overview > /tmp/orchestrator_overview.json 2>&1

# Regenerate projects.json to ensure dashboard has current information
log_message "Regenerating projects.json..."
if [ -f "generate_projects_json.py" ]; then
    python generate_projects_json.py
fi

# Create a script to stop all services
cat > stop-k0bra.sh << 'EOF'
#!/bin/bash
set -e

echo "🛑 Stopping k0bra services..."

# Kill all Python processes related to k0bra
pkill -f "port_registry.py\|service_orchestrator.py\|sandbox_executor.py\|microvm_manager.py\|build_cache_proxy.py\|cloud_runners.py\|screenshot_service.py\|telemetry_monitor.py\|launch_server.py\|dashboard_server.py" 2>/dev/null || true

# Stop Redis container
docker stop k0bra-redis 2>/dev/null || true

# Kill any remaining processes on k0bra ports
for port in 4110 5000 5001 5002 5003 5004 5005 5006 6110 9111; do
    if command -v lsof &> /dev/null; then
        lsof -i:"$port" -sTCP:LISTEN -t | xargs -r kill -9 2>/dev/null || true
    fi
done

echo "✅ k0bra services stopped"
EOF

chmod +x stop-k0bra.sh

# Display startup summary
echo ""
echo "=================================================="
echo "✅ Enhanced k0bra system started successfully!"
echo "=================================================="
echo ""
echo "🔗 Service URLs:"
echo "  - Dashboard: http://localhost:9111/"
echo "  - Port Registry: http://localhost:4110/"
echo "  - Orchestrator: http://localhost:5000/orchestrator/overview"
echo "  - Launch Server: http://localhost:6110/status"
echo "  - Sandbox: http://localhost:5001/health"
echo "  - MicroVM: http://localhost:5002/health"
echo "  - Cache: http://localhost:5003/health"
echo "  - Cloud: http://localhost:5004/health"
echo "  - Screenshots: http://localhost:5005/health"
echo "  - Telemetry: http://localhost:5006/metrics/summary"
echo ""
echo "📊 Monitor with: curl http://localhost:5000/orchestrator/overview"
echo "📊 System status: http://localhost:5000/orchestrator/overview"
echo ""
echo "🛑 Stop all services: ./stop-k0bra.sh"
echo ""
echo "🚀 Your k0bra system is ready for action!"

# Keep script running and handle shutdown gracefully
trap 'echo "Shutting down k0bra services..."; ./stop-k0bra.sh; exit' SIGINT SIGTERM

# Wait for orchestrator process (the main coordinator)
if [ ! -z "$ORCHESTRATOR_PID" ] && kill -0 "$ORCHESTRATOR_PID" 2>/dev/null; then
    wait "$ORCHESTRATOR_PID"
else
    echo "Orchestrator process not found, waiting indefinitely..."
    while true; do
        sleep 30
    done
fi