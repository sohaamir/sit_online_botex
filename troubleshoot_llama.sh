#!/bin/bash
# rebuild_llama_server.sh - Simplified build for just the server

set -e  # Exit on error

echo "Building llama.cpp server..."

# Create build directory
cd llama_cpp
mkdir -p build
cd build

# Configure and build with focus on the server
cmake ..
cmake --build . --target server

# Check if binary was created
if [ -f "bin/server" ]; then
    echo "Server built successfully at: $(pwd)/bin/server"
    cd ../..  # Return to project root
    ln -sf "$(pwd)/llama_cpp/build/bin/server" "$(pwd)/llama_server"
    echo "Created symlink to llama_server"
else
    echo "Server binary not found at expected location."
    echo "Looking for server binary:"
    find . -name "server" -type f
    cd ../..  # Return to project root
fi