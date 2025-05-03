#!/usr/bin/env python
# run_experiment.py - Script to run social influence task with LLM bots
# Uses botex CLI with native llama.cpp server

import argparse
import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv('botex.env')

def main():
    parser = argparse.ArgumentParser(description='Run social influence task with LLM bots')
    
    # Required arguments
    parser.add_argument('name', help='Name of the experiment (e.g., social_influence_task)')
    parser.add_argument('sessions', type=int, help='Number of concurrent sessions to run')
    parser.add_argument('--strategy', default='standard', 
                        choices=['standard', 'risk_taking', 'social_follower'],
                        help='Bot strategy to use (default: standard)')
    parser.add_argument('--output_dir', default='botex_data', 
                        help='Output directory for experiment data')
    
    args = parser.parse_args()
    
    # Configure environment variables for botex
    os.environ['OTREE_SESSION_CONFIG'] = args.name
    os.environ['OTREE_NPARTICIPANTS'] = '5'
    os.environ['OTREE_NHUMANS'] = '0'
    os.environ['BOTEX_SKIP_HEALTH_CHECK'] = '1'  # Skip health check for llama.cpp
    os.environ['BOTEX_STRATEGY'] = args.strategy  # Set strategy
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Create botex command
    botex_cmd = ["botex", "-v"]
    
    # Add output file
    csv_output = os.path.join(args.output_dir, f"{args.name}_{args.strategy}.csv")
    botex_cmd.extend(["-e", csv_output])
    
    # Run the experiment using botex CLI
    try:
        print(f"Running botex command: {' '.join(botex_cmd)}")
        result = subprocess.run(botex_cmd, check=True)
        print(f"Experiment completed with exit code: {result.returncode}")
        print(f"Results saved to {csv_output}")
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"Error running experiment: {e}")
        return e.returncode

if __name__ == "__main__":
    sys.exit(main())