#!/bin/bash
# Quick deployment script for Oracle Cloud VM

set -e

echo "🚀 TravelBook Generator - Backend Deployment Script"
echo "=================================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found! Creating from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your settings and run this script again."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data output

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "✅ Docker installed. Please log out and back in, then run this script again."
    exit 0
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Installing..."
    sudo apt update
    sudo apt install docker-compose -y
fi

# Pull latest changes (if in git repo)
if [ -d .git ]; then
    echo "📥 Pulling latest changes from git..."
    git pull
fi

# Stop and remove old containers
echo "🛑 Stopping old containers..."
docker-compose down

# Build and start containers
echo "🏗️  Building Docker image..."
docker-compose build

echo "🚀 Starting backend..."
docker-compose up -d

echo "⏳ Waiting for backend to start..."
sleep 10

# Test health endpoint
echo "🏥 Testing health endpoint..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is running!"
    echo ""
    echo "🎉 Deployment successful!"
    echo ""
    echo "📊 View logs: docker-compose logs -f"
    echo "🛑 Stop backend: docker-compose down"
    echo "🔄 Restart backend: docker-compose restart"
    echo ""
    echo "🌐 Access backend at: http://YOUR_SERVER_IP:8000"
else
    echo "❌ Backend health check failed!"
    echo "📋 Checking logs..."
    docker-compose logs --tail=50
    exit 1
fi
