#!/usr/bin/env python
# run_experiment.py

from dotenv import load_dotenv
import requests
import argparse
import logging
import time
import sys
import os

# Import our server script
from run_llamacpp_server import run_server, stop_server

# Import the refactored run_botex_experiment module
from run_botex_experiment import main as run_experiment_main
from run_botex_experiment import LogFilter

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger()

# Apply filter to handlers
for handler in logger.handlers:
    handler.addFilter(LogFilter())

# Load environment variables
if os.path.exists('.env'):
    load_dotenv()

def main():
    parser = argparse.ArgumentParser(description='Run social influence task with LLM bots')
    
    # Required arguments
    parser.add_argument('name', help='Name of the experiment (e.g., social_influence_task)')
    parser.add_argument('sessions', type=int, help='Number of concurrent sessions to run')
    parser.add_argument('llm', help='LLM model to use (e.g., "gemini/gemini-1.5-flash", "tinyllama")')
    
    # Optional arguments
    parser.add_argument('--model_path', help='Path to local model file (default: models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf)')
    parser.add_argument('--api_key', help='API key for cloud models (if not set in .env)')
    parser.add_argument('--strategy', default='standard', choices=['standard', 'risk_taking', 'social_follower'],
                       help='Bot strategy to use (default: standard)')
    parser.add_argument('--output_dir', default='botex_data', help='Output directory for experiment data')

    args = parser.parse_args()
    
    # Configure experiment based on arguments
    experiment_name = args.name
    num_sessions = args.sessions
    llm_choice = args.llm.lower()
    
    # Set up model configuration
    llm_server_process = None
    api_key = args.api_key
    
    try:
        # If using local TinyLLaMA model
        if llm_choice == "tinyllama" or llm_choice == "llamacpp":
            # Find model path
            model_path = args.model_path
            if not model_path:
                model_path = "models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
            
            if not os.path.exists(model_path):
                print(f"Error: Model file not found at {model_path}")
                print("Please run ./download_model.sh first or specify correct model path")
                return
            
            # Start the server using our module approach
            llm_server_process = run_server(model_path)
            
            if not llm_server_process:
                print("Failed to start the llama.cpp server")
                return
            
            # Set model to "llamacpp" for botex
            llm_model = "llamacpp"
            api_key = None
            api_base = "http://localhost:8080"  # Default server URL
        else:
            # Using cloud model (e.g., Gemini)
            llm_model = args.llm
            api_base = None
            
            # If API key not provided as argument, try to get from environment
            if not api_key:
                if llm_model.startswith("gemini"):
                    api_key = os.environ.get('OTREE_GEMINI_API_KEY')
                elif llm_model.startswith("gpt"):
                    api_key = os.environ.get('OPENAI_API_KEY')
                
                if not api_key:
                    print(f"Error: API key not found for {llm_model}")
                    print("Set it in .env or provide with --api_key")
                    return
        
        # Run the experiment
        print(f"\nRunning {num_sessions} concurrent session(s) with {llm_model}")
        print(f"Bot strategy: {args.strategy}")
        
        # Call the main function from run_botex_experiment.py
        run_experiment_main(
            experiment_name=experiment_name,
            num_sessions=num_sessions,
            llm_model=llm_model,
            api_key=api_key,
            api_base=api_base,
            output_dir=args.output_dir,
            llm_server=None,  # Not using botex's server management
            strategy_type=args.strategy
        )
        
    finally:
        # Clean up llama.cpp server if it was started
        if llm_server_process:
            print("Stopping llama.cpp server...")
            stop_server(llm_server_process)

if __name__ == "__main__":
    main()