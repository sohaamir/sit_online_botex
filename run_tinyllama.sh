#!/bin/bash
# run_tinyllama.sh - Run the experiment with optimized TinyLLaMA settings

# Start llama.cpp server with optimized settings
echo "Starting llama.cpp server with optimized settings..."
./run_llama_server.sh --max-tokens 256 --temperature 0.8 --repeat-penalty 1.1 &
SERVER_PID=$!

# Wait for server to start
sleep 5

# Run the experiment
echo "Running experiment with TinyLLaMA..."
python run_experiment.py social_influence_task 1 tinyllama --max-tokens 256

# Clean up
echo "Stopping llama.cpp server..."
kill $SERVER_PID