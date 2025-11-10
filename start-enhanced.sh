#!/bin/bash
set -e

echo "🚀 Starting Enhanced k0bra System..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3 first."
    exit 1
fi

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

# Check if Redis is running (optional)
if ! docker ps | grep -q redis; then
    echo "🔴 Starting Redis container..."
    docker run -d --name k0bra-redis -p 6379:6379 redis:7-alpine || echo "Redis already running"
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Start the service orchestrator
echo "🎯 Starting Service Orchestrator..."
python service_orchestrator.py &
ORCHESTRATOR_PID=$!

# Wait for orchestrator to start
sleep 3

# Start all services
echo "🚀 Starting all enhanced services..."
curl -X POST http://localhost:5000/orchestrator/start-all || echo "Services starting..."

echo "✅ Enhanced k0bra system started!"
echo ""
echo "🔗 Service URLs:"
echo "  - Orchestrator: http://localhost:5000/orchestrator/overview"
echo "  - Sandbox: http://localhost:5001/health"
echo "  - MicroVM: http://localhost:5002/health"
echo "  - Cache: http://localhost:5003/health"
echo "  - Cloud: http://localhost:5004/health"
echo "  - Screenshots: http://localhost:5005/health"
echo "  - Telemetry: http://localhost:5006/metrics/summary"
echo ""
echo "📊 Monitor with: curl http://localhost:5000/orchestrator/overview"
echo "🛑 Stop with: curl -X POST http://localhost:5000/orchestrator/stop-all"

# Keep script running
wait $ORCHESTRATOR_PID
