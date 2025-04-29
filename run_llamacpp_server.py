#!/usr/bin/env python
# run_llamacpp_server.py

import subprocess
import requests
import signal
import time
import sys
import os

def run_server(model_path, port=8080):
    """Run the llama.cpp server as a Python module"""
    print(f"Starting llama.cpp server with model: {model_path}")
    
    # Make sure the model exists
    if not os.path.exists(model_path):
        print(f"Error: Model file not found at {model_path}")
        return None
    
    # Command to run the server
    cmd = [
        sys.executable, "-m", "llama_cpp.server",
        "--model", model_path,
        "--host", "127.0.0.1",
        "--port", str(port)
    ]
    
    # Start the server process
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for the server to start
        max_retries = 30
        for i in range(max_retries):
            try:
                # Check if server is running
                response = requests.get(f"http://localhost:{port}/health")
                if response.status_code == 200:
                    print(f"Server started successfully at http://localhost:{port}")
                    return process
            except requests.exceptions.ConnectionError:
                # Server not ready yet
                print(f"Waiting for server to start (attempt {i+1}/{max_retries})...")
                time.sleep(2)
        
        # If we get here, server didn't start
        print("Failed to start server within the timeout period")
        process.terminate()
        return None
        
    except Exception as e:
        print(f"Error starting server: {e}")
        return None

def stop_server(process):
    """Stop the llama.cpp server process"""
    if process is not None:
        print("Stopping llama.cpp server...")
        process.terminate()
        process.wait(timeout=5)
        print("Server stopped")

if __name__ == "__main__":
    # Default model path
    model_path = "models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    
    # Get model path from command line if provided
    if len(sys.argv) > 1:
        model_path = sys.argv[1]
    
    # Run the server
    process = run_server(model_path)
    
    if process:
        try:
            print("Server is running. Press Ctrl+C to stop.")
            # Keep the server running until interrupted
            process.wait()
        except KeyboardInterrupt:
            pass
        finally:
            stop_server(process)