#!/bin/bash
# Oracle VM Initial Setup Script
# Run this ONCE on your Oracle Cloud VM

set -e  # Exit on any error

echo "=========================================="
echo "TravelBook Generator - VM Setup"
echo "=========================================="
echo ""

# 1. Update system
echo "Step 1: Updating system packages..."
sudo apt update
sudo apt upgrade -y

# 2. Install Docker
echo ""
echo "Step 2: Installing Docker..."
if ! command -v docker &> /dev/null; then
    sudo apt install -y docker.io
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker $USER
    echo "✅ Docker installed"
else
    echo "✅ Docker already installed"
fi

# 3. Install Docker Compose v2 (plugin version, compatible with Python 3.12)
echo ""
echo "Step 3: Installing Docker Compose v2..."
if ! docker compose version &> /dev/null; then
    sudo apt install -y docker-compose-v2
    echo "✅ Docker Compose v2 installed"
else
    echo "✅ Docker Compose v2 already installed"
fi

# 4. Install Git
echo ""
echo "Step 4: Installing Git..."
if ! command -v git &> /dev/null; then
    sudo apt install -y git
    echo "✅ Git installed"
else
    echo "✅ Git already installed"
fi

# 5. Configure Git
echo ""
echo "Step 5: Configuring Git..."
git config --global user.email "github-actions@example.com"
git config --global user.name "GitHub Actions"
git config --global pull.rebase false

# 6. Clone repository
echo ""
echo "Step 6: Cloning repository..."
cd ~
if [ -d "travel-book-generator" ]; then
    echo "⚠️  Repository already exists, updating..."
    cd travel-book-generator
    git pull origin main
else
    git clone https://github.com/lefei1980/travel-book-generator.git
    cd travel-book-generator
    echo "✅ Repository cloned"
fi

# 7. Set up backend environment
echo ""
echo "Step 7: Setting up backend environment..."
cd ~/travel-book-generator/backend

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file with your email!"
    echo "   Run: nano ~/travel-book-generator/backend/.env"
    echo "   Change CONTACT_EMAIL to your real email address"
    echo ""
else
    echo "✅ .env file already exists"
fi

# 8. Deploy backend
echo ""
echo "Step 8: Deploying backend with Docker..."
cd ~/travel-book-generator/backend

# Make deploy script executable
chmod +x deploy.sh

# Deploy using Docker Compose v2
echo "Building and starting containers..."
docker compose down 2>/dev/null || true
docker compose build --no-cache
docker compose up -d

# 9. Wait for backend to start
echo ""
echo "Step 9: Waiting for backend to start..."
sleep 15

# 10. Health check
echo ""
echo "Step 10: Running health check..."
if curl -f http://localhost:8000/health; then
    echo ""
    echo "=========================================="
    echo "✅ Backend deployed successfully!"
    echo "=========================================="
    echo ""
    echo "Your backend is running at:"
    echo "  - Health: http://localhost:8000/health"
    echo "  - API Docs: http://localhost:8000/docs"
    echo ""

    # Get public IP
    PUBLIC_IP=$(curl -4 -s ifconfig.me)
    echo "Your public IP: $PUBLIC_IP"
    echo ""
    echo "External access (if firewall allows):"
    echo "  - http://$PUBLIC_IP:8000/health"
    echo "  - http://$PUBLIC_IP:8000/docs"
    echo ""
    echo "=========================================="
    echo "Next Steps:"
    echo "=========================================="
    echo "1. Edit .env file with your real email:"
    echo "   nano ~/travel-book-generator/backend/.env"
    echo ""
    echo "2. If you changed .env, restart:"
    echo "   cd ~/travel-book-generator/backend"
    echo "   docker compose restart"
    echo ""
    echo "3. GitHub Actions is now ready to deploy automatically!"
    echo "   Just push changes to the main branch."
    echo ""
else
    echo ""
    echo "❌ Health check failed!"
    echo ""
    echo "Checking logs:"
    docker compose logs --tail=50
    exit 1
fi
