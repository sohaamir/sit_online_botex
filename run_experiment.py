#!/usr/bin/env python3
"""
run_experiment.py - Simple wrapper for running social influence task with different LLM models

Usage:
    python run_experiment.py [model] [sessions] [options]

Options:
    --strategy STRATEGY    Bot strategy (standard, risk_taking, social_follower)
    --max-tokens TOKENS    Maximum tokens for responses
    --humans N            Number of human participants

Examples:
    # Run with OpenAI model
    python run_model.py openai 1
    
    # Run with Anthropic model
    python run_model.py anthropic 1
    
    # Run with Gemini model
    python run_model.py gemini 1
    
    # Run with local TinyLLaMA model
    python run_model.py tinyllama 1
    
    # Run with specific strategy
    python run_model.py openai 1 --strategy risk_taking
"""

import sys
import os
import argparse
import subprocess
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv("botex.env")
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Run social influence task with different LLM models")
    parser.add_argument("model", choices=["openai", "anthropic", "gemini", "tinyllama", "any"],
                        help="LLM model to use")
    parser.add_argument("sessions", type=int, default=1, 
                        help="Number of sessions to run")
    parser.add_argument("--strategy", choices=["standard", "risk_taking", "social_follower"],
                        default=os.environ.get("BOT_STRATEGY", "standard"),
                        help="Bot strategy to use")
    parser.add_argument("--max-tokens", type=int, 
                        default=int(os.environ.get("MAX_TOKENS_DEFAULT", "1024")),
                        help="Maximum number of tokens")
    parser.add_argument("--humans", type=int, 
                        default=int(os.environ.get("OTREE_NHUMANS", "0")),
                        help="Number of human participants")
    
    args = parser.parse_args()
    
    # Create model-specific output directory
    output_dir = f"botex_data_{args.model}"
    
    # Build command for run_multi_model_experiment.py
    cmd = [
        "python", "run_multi_model_experiment.py",
        "--model", args.model,
        "--sessions", str(args.sessions),
        "--strategy", args.strategy,
        "--max-tokens", str(args.max_tokens),
        "--humans", str(args.humans),
        "--output-dir", output_dir
    ]
    
    # Run the command
    print(f"Running experiment with {args.model} model...")
    print(f"Output will be saved to {output_dir}")
    
    result = subprocess.run(cmd)
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())