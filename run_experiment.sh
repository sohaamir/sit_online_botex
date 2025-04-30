#!/bin/bash
# Script to run social influence task experiment using botex

# Default values
MODEL="gemini"
STRATEGY="standard"
API_KEY=""
OUTPUT_DIR="botex_data"
LLAMACPP_PID=""

# Helper function for cleanup
cleanup() {
  if [ -n "$LLAMACPP_PID" ]; then
    echo "Stopping llama.cpp server..."
    kill $LLAMACPP_PID 2>/dev/null
  fi
}

# Register cleanup function
trap cleanup EXIT

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      MODEL="$2"
      shift 2
      ;;
    --api-key)
      API_KEY="$2"
      shift 2
      ;;
    --strategy)
      STRATEGY="$2"
      shift 2
      ;;
    --output)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [--model gemini|tinyllama] [--api-key KEY] [--strategy standard|risk_taking|social_follower] [--output DIR]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Create strategy-specific prompts file if needed
if [ "$STRATEGY" != "standard" ]; then
  echo "Using $STRATEGY strategy - this would typically load different prompts"
  # In a real implementation, you would modify bot_prompts.csv here
  # for different strategies
fi

# Setup based on model type
if [ "$MODEL" = "gemini" ]; then
  echo "Setting up for Gemini API..."
  
  # Get API key from environment if not provided
  if [ -z "$API_KEY" ]; then
    source .env 2>/dev/null
    API_KEY="$OTREE_GEMINI_API_KEY"
    
    if [ -z "$API_KEY" ]; then
      echo "Error: API key required for Gemini. Provide with --api-key or set OTREE_GEMINI_API_KEY in .env"
      exit 1
    fi
  fi
  
  # Run experiment with botex CLI using Gemini
  echo "Starting experiment with Gemini API..."
  botex -v -m "gemini/gemini-1.5-flash" -k "$API_KEY" -c botex.env -e "${OUTPUT_DIR}/responses.csv"
  
elif [ "$MODEL" = "tinyllama" ] || [ "$MODEL" = "llamacpp" ]; then
  echo "Setting up for llama.cpp with TinyLLaMA..."
  
  # Check if server is already running
  if curl -s "http://localhost:8080/v1/models" >/dev/null 2>&1; then
    echo "llama.cpp server is already running"
  else
    echo "Starting llama.cpp server..."
    python run_llamacpp_server.py &
    LLAMACPP_PID=$!
    
    # Wait for server to start
    for i in {1..30}; do
      if curl -s "http://localhost:8080/v1/models" >/dev/null 2>&1; then
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
  
  # Disable health checks for llamacpp
  export BOTEX_SKIP_HEALTH_CHECK=1
  
  # Run experiment with botex CLI using llama.cpp
  echo "Starting experiment with llama.cpp..."
  botex -v -m "llamacpp" -a "http://localhost:8080" -c botex.env -e "${OUTPUT_DIR}/responses.csv"
  
else
  echo "Error: Unknown model '$MODEL'. Use 'gemini' or 'tinyllama'."
  exit 1
fi

echo "Experiment completed! Results saved to $OUTPUT_DIR"