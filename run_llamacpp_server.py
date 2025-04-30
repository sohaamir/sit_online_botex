#!/usr/bin/env python
# Script to run llama.cpp server for botex experiments

import sys
import subprocess
import requests
import time
import os
import signal

# Path to your model
model_path = "models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"

# Command to run the server
cmd = [
    sys.executable, 
    "-m", "llama_cpp.server",
    "--model", model_path,
    "--host", "127.0.0.1",
    "--port", "8080",
    "--verbose", "true"
]

print(f"Running command: {' '.join(cmd)}")

# Start server with output piped to console
process = subprocess.Popen(
    cmd,
    stdout=sys.stdout,
    stderr=sys.stderr,
    text=True
)

# Check if server starts successfully
max_retries = 30
for i in range(max_retries):
    try:
        print(f"Waiting for server to start (attempt {i+1}/{max_retries})...")
        response = requests.get("http://localhost:8080/v1/models")
        if response.status_code == 200:
            print(f"Server started successfully at http://localhost:8080")
            print(f"Models available: {response.json()}")
            break
    except requests.exceptions.ConnectionError:
        time.sleep(1)
else:
    print("Failed to start server within the timeout period")
    process.terminate()
    sys.exit(1)

# Handle the /health endpoint issue by overwriting the check_server_health function
print("\nNOTE: To make botex work with llama.cpp, you need to run: ")
print("export BOTEX_SKIP_HEALTH_CHECK=1")
print("before running botex CLI")

print("\nServer is running! Press Ctrl+C to stop...")
try:
    # Keep the server running until interrupted
    while True:
        process.poll()
        if process.returncode is not None:
            print(f"Server process exited with code {process.returncode}")
            break
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping server...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        print("Server didn't terminate, forcing...")
        process.kill()