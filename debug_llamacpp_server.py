# save as debug_llamacpp_server.py
import sys
import subprocess
import os
import time

# Path to your model
model_path = "models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"

# Command to run the server with verbose logging
cmd = [
    sys.executable, 
    "-m", "llama_cpp.server",
    "--model", model_path,
    "--host", "127.0.0.1",
    "--port", "8080",
    "--verbose"  # Add verbose flag
]

print(f"Running command: {' '.join(cmd)}")

# Start server with direct output to console
process = subprocess.Popen(
    cmd,
    stdout=sys.stdout,  # Direct output to console
    stderr=sys.stderr,
    text=True
)

# Wait to see if it starts
try:
    print("Server process started. Press Ctrl+C to stop...")
    process.wait()
except KeyboardInterrupt:
    print("Stopping server...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        print("Server didn't terminate, forcing...")
        process.kill()