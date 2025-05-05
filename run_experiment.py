#!/usr/bin/env python3
"""
run_experiment.py - Simple wrapper for running social influence task experiments

This simplified script provides an easy-to-use interface for the more complex
run_botex_experiment.py script.

Usage:
    python run_experiment.py <name> <sessions> <llm> [options]

Example:
    # Run with Gemini model
    python run_experiment.py social_influence_task 1 gemini
    
    # Run with OpenAI model
    python run_experiment.py social_influence_task 1 openai
    
    # Run with local TinyLLaMA model
    python run_experiment.py social_influence_task 1 tinyllama
    
    # Run with specific strategy
    python run_experiment.py social_influence_task 1 gemini --strategy risk_taking
"""

import sys
import argparse
from run_botex_experiment import parse_arguments, main as run_experiment

def parse_simple_args():
    """Parse simplified command line arguments"""
    parser = argparse.ArgumentParser(description="Run social influence task with LLM bots")
    
    # Positional arguments
    parser.add_argument("name", help="Name of the experiment (config name)")
    parser.add_argument("sessions", type=int, help="Number of concurrent sessions to run")
    parser.add_argument("llm", choices=["gemini", "openai", "tinyllama"], 
                      help="LLM model to use")
    
    # Optional arguments
    parser.add_argument("--model-path", help="Path to local model file (for tinyllama)")
    parser.add_argument("--api-key", help="API key for cloud models (if not set in .env)")
    parser.add_argument("--strategy", choices=["standard", "risk_taking", "social_follower"],
                      default="standard", help="Bot strategy to use")
    parser.add_argument("--output-dir", default="botex_data", 
                      help="Directory to store output data")
    
    return parser.parse_args()

def main():
    """Main function to run the experiment with simplified args"""
    # Get the simplified arguments
    simple_args = parse_simple_args()
    
    # Add model name to output directory
    model_specific_output_dir = f"{simple_args.output_dir}_{simple_args.llm}"
    
    # Create a list of arguments to pass to the main run_botex_experiment script
    sys_args = [
        "--session-config", simple_args.name,
        "--sessions", str(simple_args.sessions),
        "--model", simple_args.llm,
        "--strategy", simple_args.strategy,
        "--output-dir", model_specific_output_dir
    ]
    
    # Add optional arguments if provided
    if simple_args.model_path:
        sys_args.extend(["--model-path", simple_args.model_path])
    if simple_args.api_key:
        sys_args.extend(["--api-key", simple_args.api_key])
    
    # Replace sys.argv with our constructed args
    old_argv = sys.argv
    sys.argv = [old_argv[0]] + sys_args
    
    # Run the main experiment
    run_experiment()
    
    # Restore original sys.argv
    sys.argv = old_argv

if __name__ == "__main__":
    main()