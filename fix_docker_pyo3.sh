#!/bin/bash

echo "🔧 Fixing PyO3 issues in Docker environment..."

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo "❌ Docker is not running. Please start Docker and try again."
        exit 1
    fi
    echo "✓ Docker is running"
}

# Function to stop and remove existing containers
cleanup_containers() {
    echo "🧹 Cleaning up existing containers..."
    
    # Stop running containers
    docker stop $(docker ps -q --filter ancestor=workflows-app-googlesheet-app-connector-template) 2>/dev/null || true
    docker stop $(docker ps -q --filter ancestor=workflows-app-connector) 2>/dev/null || true
    
    # Remove containers
    docker rm $(docker ps -aq --filter ancestor=workflows-app-googlesheet-app-connector-template) 2>/dev/null || true
    docker rm $(docker ps -aq --filter ancestor=workflows-app-connector) 2>/dev/null || true
    
    echo "✓ Containers cleaned up"
}

# Function to remove old images
cleanup_images() {
    echo "🧹 Removing old images..."
    
    # Remove old images
    docker rmi workflows-app-googlesheet-app-connector-template:latest 2>/dev/null || true
    docker rmi workflows-app-connector:latest 2>/dev/null || true
    
    # Clean up Docker system
    docker system prune -f
    
    echo "✓ Images cleaned up"
}

# Function to rebuild development image
rebuild_dev_image() {
    echo "📦 Rebuilding development Docker image with PyO3 fix..."
    
    # Build with no cache and proper environment variables
    docker build --no-cache -t workflows-app-connector -f config/Dockerfile.dev . \
        --build-arg ENVIRONMENT=dev \
        --build-arg CRYPTOGRAPHY_DONT_BUILD_RUST=1 \
        --build-arg CRYPTOGRAPHY_USE_PURE_PYTHON=1 \
        --build-arg PYTHONUNBUFFERED=1
    
    if [ $? -eq 0 ]; then
        echo "✅ Development image rebuilt successfully"
        return 0
    else
        echo "❌ Failed to rebuild development image"
        return 1
    fi
}

# Function to rebuild production image
rebuild_prod_image() {
    echo "📦 Rebuilding production Docker image with PyO3 fix..."
    
    # Build with no cache and proper environment variables
    docker build --no-cache -t workflows-app-googlesheet-app-connector-template . \
        --build-arg ENVIRONMENT=dev \
        --build-arg CRYPTOGRAPHY_DONT_BUILD_RUST=1 \
        --build-arg CRYPTOGRAPHY_USE_PURE_PYTHON=1 \
        --build-arg PYTHONUNBUFFERED=1
    
    if [ $? -eq 0 ]; then
        echo "✅ Production image rebuilt successfully"
        return 0
    else
        echo "❌ Failed to rebuild production image"
        return 1
    fi
}

# Function to test the rebuilt image
test_image() {
    local image_name=$1
    local container_name="test-${image_name}"
    
    echo "🧪 Testing rebuilt image: ${image_name}"
    
    # Run container with test script
    docker run --rm \
        -e CRYPTOGRAPHY_DONT_BUILD_RUST=1 \
        -e CRYPTOGRAPHY_USE_PURE_PYTHON=1 \
        -e PYTHONUNBUFFERED=1 \
        -v "$(pwd):/usr/src/app" \
        --name "${container_name}" \
        "${image_name}" \
        python docker_test_pyo3.py
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo "✅ Image test passed: ${image_name}"
        return 0
    else
        echo "❌ Image test failed: ${image_name}"
        return 1
    fi
}

# Function to run the application
run_application() {
    local image_name=$1
    local port=${2:-2003}
    
    echo "🚀 Running application with image: ${image_name}"
    echo "📡 Application will be available at: http://localhost:${port}"
    echo ""
    echo "To stop the application, press Ctrl+C"
    echo ""
    
    # Run the container
    docker run --rm \
        -p "${port}:8080" \
        -e ENVIRONMENT=dev \
        -e REGION=besg \
        -e CRYPTOGRAPHY_DONT_BUILD_RUST=1 \
        -e CRYPTOGRAPHY_USE_PURE_PYTHON=1 \
        -e PYTHONUNBUFFERED=1 \
        -v "$(pwd):/usr/src/app" \
        --name "running-${image_name}" \
        "${image_name}"
}

# Main script
main() {
    echo "=== DOCKER PYO3 FIX SCRIPT ==="
    echo ""
    
    # Check Docker
    check_docker
    
    # Clean up
    cleanup_containers
    cleanup_images
    
    # Ask user which image to rebuild
    echo ""
    echo "Which Docker image would you like to rebuild?"
    echo "1. Development image (workflows-app-connector)"
    echo "2. Production image (workflows-app-googlesheet-app-connector-template)"
    echo "3. Both images"
    echo "4. Exit"
    echo ""
    read -p "Enter your choice (1-4): " choice
    
    case $choice in
        1)
            echo "Rebuilding development image..."
            if rebuild_dev_image; then
                if test_image "workflows-app-connector"; then
                    echo ""
                    read -p "Would you like to run the application now? (y/n): " run_app
                    if [[ $run_app =~ ^[Yy]$ ]]; then
                        run_application "workflows-app-connector" 2003
                    fi
                fi
            fi
            ;;
        2)
            echo "Rebuilding production image..."
            if rebuild_prod_image; then
                if test_image "workflows-app-googlesheet-app-connector-template"; then
                    echo ""
                    read -p "Would you like to run the application now? (y/n): " run_app
                    if [[ $run_app =~ ^[Yy]$ ]]; then
                        run_application "workflows-app-googlesheet-app-connector-template" 2001
                    fi
                fi
            fi
            ;;
        3)
            echo "Rebuilding both images..."
            dev_success=false
            prod_success=false
            
            if rebuild_dev_image; then
                dev_success=true
            fi
            
            if rebuild_prod_image; then
                prod_success=true
            fi
            
            if $dev_success && $prod_success; then
                echo ""
                echo "Both images rebuilt successfully!"
                echo ""
                echo "To run development version:"
                echo "  docker run --rm -p 2003:8080 -it -e ENVIRONMENT=dev -e REGION=besg -e CRYPTOGRAPHY_DONT_BUILD_RUST=1 -e CRYPTOGRAPHY_USE_PURE_PYTHON=1 -v \$(pwd):/usr/src/app/ workflows-app-connector"
                echo ""
                echo "To run production version:"
                echo "  docker run --rm -p 2001:8080 -it -e ENVIRONMENT=dev -e REGION=besg -e CRYPTOGRAPHY_DONT_BUILD_RUST=1 -e CRYPTOGRAPHY_USE_PURE_PYTHON=1 -v \$(pwd):/usr/src/app/ workflows-app-googlesheet-app-connector-template"
            fi
            ;;
        4)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo "Invalid choice. Please run the script again."
            exit 1
            ;;
    esac
    
    echo ""
    echo "🎉 Docker PyO3 fix completed!"
    echo ""
    echo "Key changes made:"
    echo "  ✓ Added explicit cryptography==41.0.8 to requirements.txt"
    echo "  ✓ Set CRYPTOGRAPHY_DONT_BUILD_RUST=1 environment variable"
    echo "  ✓ Set CRYPTOGRAPHY_USE_PURE_PYTHON=1 environment variable"
    echo "  ✓ Rebuilt Docker images with no cache"
    echo ""
    echo "The PyO3 error should now be resolved in your Docker containers."
}

# Run main function
main 