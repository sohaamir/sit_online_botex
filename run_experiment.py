# run_experiment.py
#!/usr/bin/env python

import tinyllama_fix

# Explicitly disable health checks at the very top of the file
import os
os.environ['BOTEX_SKIP_HEALTH_CHECK'] = '1'

from dotenv import load_dotenv
import argparse
import logging
import sys

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
    parser.add_argument('llm', help='LLM model to use (e.g., "gemini/gemini-1.5-flash", "llamacpp")')
    
    # Optional arguments
    parser.add_argument('--api_key', help='API key for cloud models (if not set in .env)')
    parser.add_argument('--strategy', default='standard', choices=['standard', 'risk_taking', 'social_follower'],
                       help='Bot strategy to use (default: standard)')
    parser.add_argument('--output_dir', default='botex_data', help='Output directory for experiment data')

    args = parser.parse_args()
    
    # Configure experiment based on arguments
    experiment_name = args.name
    num_sessions = args.sessions
    llm_choice = args.llm.lower()
    
    # Set up model configuration - always assume server is running for llamacpp
    if llm_choice == "tinyllama" or llm_choice == "llamacpp":
        llm_model = "llamacpp"
        api_key = None
        api_base = "http://localhost:8080"  # Use absolute URL
        
        print(f"Using existing llama.cpp server at {api_base}")
    else:
        # Using cloud model (e.g., Gemini)
        llm_model = args.llm
        api_key = args.api_key
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

if __name__ == "__main__":
    main()