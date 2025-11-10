#!/bin/bash
set -e

echo "🚀 Deploying k0bra to Kubernetes..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl first."
    exit 1
fi

# Check if cluster is accessible
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster. Please check your kubeconfig."
    exit 1
fi

# Create namespace first
echo "📦 Creating namespace..."
kubectl apply -f k8s/namespace.yaml

# Apply storage resources
echo "💾 Setting up storage..."
kubectl apply -f k8s/storage.yaml

# Deploy Redis
echo "🔴 Deploying Redis..."
kubectl apply -f k8s/redis-deployment.yaml

# Wait for Redis to be ready
echo "⏳ Waiting for Redis to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/redis -n k0bra-system

# Deploy main application
echo "🎯 Deploying k0bra application..."
kubectl apply -f k8s/k0bra-deployment.yaml

# Deploy sandbox executor
echo "🔒 Deploying sandbox executor..."
kubectl apply -f k8s/sandbox-deployment.yaml

# Deploy screenshot service
echo "📸 Deploying screenshot service..."
kubectl apply -f k8s/screenshot-deployment.yaml

# Deploy ingress
echo "🌐 Setting up ingress..."
kubectl apply -f k8s/ingress.yaml

# Wait for deployments
echo "⏳ Waiting for all deployments to be ready..."
kubectl wait --for=condition=available --timeout=600s deployment/k0bra-app -n k0bra-system
kubectl wait --for=condition=available --timeout=600s deployment/sandbox-executor -n k0bra-system
kubectl wait --for=condition=available --timeout=600s deployment/build-cache-proxy -n k0bra-system
kubectl wait --for=condition=available --timeout=600s deployment/screenshot-service -n k0bra-system

# Get service information
echo "📋 Deployment complete! Service information:"
kubectl get services -n k0bra-system
echo ""
kubectl get ingress -n k0bra-system

# Show pod status
echo "🔍 Pod status:"
kubectl get pods -n k0bra-system

echo "✅ k0bra deployment completed successfully!"
echo ""
echo "🔗 Access your application at: https://k0bra.example.com"
echo "📊 Monitor with: kubectl get pods -n k0bra-system -w"
