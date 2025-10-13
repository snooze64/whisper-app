#!/bin/bash
# Frontend build script for production deployment
# This script builds the frontend with the configured VITE_API_URL

set -e

echo "===================================="
echo "Building Frontend for Production"
echo "===================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please create .env from .env.example and set VITE_API_URL"
    exit 1
fi

# Load VITE_API_URL from .env
source .env

if [ -z "$VITE_API_URL" ]; then
    echo "Error: VITE_API_URL is not set in .env"
    exit 1
fi

echo "VITE_API_URL: $VITE_API_URL"
echo ""

# Build the frontend image
echo "Step 1/2: Building frontend Docker image..."
docker-compose -f docker-compose.gpu.yml build frontend-build

# Extract dist directory
echo ""
echo "Step 2/2: Extracting build artifacts to ./frontend/dist..."
rm -rf ./frontend/dist
docker-compose -f docker-compose.gpu.yml run --rm frontend-build sh -c "cp -r /usr/share/nginx/html/* /dist/"

echo ""
echo "===================================="
echo "Frontend build completed successfully!"
echo "Build artifacts are in: ./frontend/dist"
echo "===================================="
