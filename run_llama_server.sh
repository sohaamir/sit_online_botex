#!/bin/bash
# run_llama_server.sh - Script to run the llama.cpp server binary

MODEL_PATH="models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
SERVER_PATH="./llama_server"
HOST="127.0.0.1"
PORT=8080

# Check if the server binary exists
if [ ! -f "$SERVER_PATH" ]; then
    echo "Error: llama.cpp server binary not found at $SERVER_PATH"
    echo "Please run ./install_llama_cpp.sh first to install llama.cpp"
    exit 1
fi

# Check if the model exists
if [ ! -f "$MODEL_PATH" ]; then
    echo "Error: Model file not found at $MODEL_PATH"
    echo "Please run ./download_model.sh first to download the model"
    exit 1
fi

echo "Starting llama.cpp server with model: $MODEL_PATH"
echo "Server will be available at http://$HOST:$PORT"

# Run the server with the appropriate options
$SERVER_PATH \
    --model $MODEL_PATH \
    --host $HOST \
    --port $PORT \
    --ctx-size 2048 \
    --n-gpu-layers 0 \
    --parallel 1 \
    --temp 0.7 \
    --threads 4 \
    --embedding

# This command will keep running until stopped with Ctrl+C