#!/bin/bash
# run.sh - Run social influence task with native llama.cpp server

# Set experiment parameters
EXPERIMENT="social_influence_task"
SESSIONS=1
STRATEGY="standard"  # or "risk_taking" or "social_follower"
OUTPUT_DIR="botex_data"

# Ensure model directory exists
mkdir -p models

# Check if llama.cpp server is running, start if not
if ! curl -s "http://localhost:8080/v1/models" >/dev/null; then
    echo "Starting llama.cpp server..."
    # Replace with path to your llama-server binary and model
    ./llama.cpp/build/bin/llama-server --model models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf --host 127.0.0.1 --port 8080 &
    SERVER_PID=$!
    
    # Wait for server to start
    for i in {1..30}; do
        if curl -s "http://localhost:8080/v1/models" >/dev/null; then
            echo "llama.cpp server is running!"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "Failed to start llama.cpp server"
            exit 1
        fi
        sleep 1
    done
fi

# Run the experiment
python run_experiment.py $EXPERIMENT $SESSIONS --strategy $STRATEGY --output_dir $OUTPUT_DIR

echo "Experiment complete!"