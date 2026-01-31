#!/bin/bash
# Docker Troubleshooting and Rebuild Script

set -e

echo "======================================"
echo "Docker Troubleshooting & Rebuild"
echo "======================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Step 1: Check Docker installation
print_step "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed!"
    exit 1
fi
docker --version
echo ""

# Step 2: Stop all containers
print_step "Stopping all containers..."
docker compose down || true
echo ""

# Step 3: Remove old images (force rebuild)
print_step "Removing old images..."
docker compose rm -f || true
docker rmi fnb_ho_web:latest 2>/dev/null || true
docker rmi foodbeverages-cms-web:latest 2>/dev/null || true
docker rmi foodbeverages-cms_web:latest 2>/dev/null || true
echo ""

# Step 4: Clean up Docker system
print_step "Cleaning up Docker system..."
docker system prune -f
echo ""

# Step 5: Fix line endings in entrypoint.sh
print_step "Fixing line endings in entrypoint.sh..."
if command -v dos2unix &> /dev/null; then
    dos2unix entrypoint.sh
    echo "✓ Used dos2unix"
else
    sed -i 's/\r$//' entrypoint.sh
    echo "✓ Used sed"
fi
chmod +x entrypoint.sh
echo ""

# Step 6: Verify entrypoint.sh
print_step "Verifying entrypoint.sh..."
if [ ! -f entrypoint.sh ]; then
    print_error "entrypoint.sh not found!"
    exit 1
fi
if [ ! -x entrypoint.sh ]; then
    print_error "entrypoint.sh is not executable!"
    chmod +x entrypoint.sh
fi
echo "✓ File exists and is executable"
echo ""

# Step 7: Check .env file
print_step "Checking environment file..."
if [ ! -f .env ] && [ ! -f .env.docker ]; then
    print_warning ".env file not found, creating from .env.docker..."
    if [ -f .env.docker ]; then
        cp .env.docker .env
        echo "✓ Created .env from .env.docker"
    else
        print_error "No environment file found!"
        exit 1
    fi
else
    echo "✓ Environment file found"
fi
echo ""

# Step 8: Build images with no cache
print_step "Building Docker images (no cache)..."
docker compose build --no-cache
echo ""

# Step 9: Start services
print_step "Starting services..."
docker compose up -d
echo ""

# Step 10: Wait for services to be healthy
print_step "Waiting for services to be healthy..."
sleep 10
echo ""

# Step 11: Check container status
print_step "Checking container status..."
docker compose ps
echo ""

# Step 12: Show logs
print_step "Showing logs (last 50 lines)..."
docker compose logs --tail=50
echo ""

# Step 13: Test web service
print_step "Testing web service..."
sleep 5
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000 || echo "000")
if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "302" ]; then
    echo -e "${GREEN}✓ Web service is responding (HTTP $HTTP_CODE)${NC}"
else
    print_warning "Web service returned HTTP $HTTP_CODE"
    echo "Checking container logs..."
    docker compose logs web
fi
echo ""

echo "======================================"
echo -e "${GREEN}Troubleshooting Complete!${NC}"
echo "======================================"
echo ""
echo "Access points:"
echo "  - Web: http://localhost:8000"
echo "  - Admin: http://localhost:8000/admin/"
echo "  - API Docs: http://localhost:8000/api/docs/"
echo ""
echo "Commands:"
echo "  - View logs: docker compose logs -f"
echo "  - Stop: docker compose down"
echo "  - Restart: docker compose restart"
echo ""
