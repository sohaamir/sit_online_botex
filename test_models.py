#!/usr/bin/env python3
"""
test_models.py - Test different LLM models with botex

This script demonstrates how botex connects to different models through LiteLLM.
It sends a simple prompt asking each model to identify itself.

Usage:
    python test_models.py [--model MODEL] [--prompt PROMPT]

Examples:
    # Test a specific model
    python test_models.py --model openai
    
    # Test all available models
    python test_models.py --model all
    
    # Use a custom prompt
    python test_models.py --model anthropic --prompt "Write a haiku about AI"
"""

import argparse
import os
import sys
import json
from dotenv import load_dotenv
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("model_test")

def parse_args():
    parser = argparse.ArgumentParser(description="Test different LLM models with botex")
    parser.add_argument("--model", choices=["openai", "anthropic", "gemini", "tinyllama", "all"], 
                      default="all", help="Model to test")
    parser.add_argument("--prompt", default="Identify yourself. What model are you? List your capabilities and limitations.",
                      help="Prompt to send to the model")
    return parser.parse_args()

def get_model_details(model_type):
    """Get model string and API key for the specified model type"""
    if model_type == "openai":
        model_string = os.environ.get("OPENAI_MODEL", "gpt-4.1-nano-2025-04-14")
        api_key = os.environ.get("OPENAI_API_KEY")
        return model_string, api_key
    
    elif model_type == "anthropic":
        model_string = os.environ.get("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        return model_string, api_key
    
    elif model_type == "gemini":
        model_string = os.environ.get("GEMINI_MODEL", "gemini/gemini-1.5-flash")
        api_key = os.environ.get("GEMINI_API_KEY")
        return model_string, api_key
    
    elif model_type == "tinyllama":
        model_string = "llamacpp"
        api_key = None
        return model_string, api_key
    
    return None, None

def test_model(model_type, prompt):
    """Test a specific model with the given prompt"""
    try:
        # Import litellm directly for this test
        import litellm
        
        model_string, api_key = get_model_details(model_type)
        if not model_string:
            logger.error(f"Model string not found for {model_type}")
            return False, f"Error: Model string not found for {model_type}"
        
        if model_type != "tinyllama" and not api_key:
            logger.error(f"API key not found for {model_type}")
            return False, f"Error: API key not found for {model_type}."
        
        logger.info(f"Testing {model_type} model: {model_string}")
        
        # For TinyLLama, check if server is running
        if model_type == "tinyllama":
            server_url = os.environ.get("LLAMACPP_SERVER_URL", "http://localhost:8080")
            try:
                import requests
                response = requests.get(f"{server_url}/health", timeout=5)
                if response.status_code != 200:
                    return False, f"Error: llama.cpp server not running at {server_url}"
            except Exception as e:
                return False, f"Error: Could not connect to llama.cpp server: {str(e)}"
            
            # Use botex's LlamaCpp class for tinyllama
            try:
                import botex
                llamacpp = botex.llamacpp.LlamaCpp(server_url)
                response = llamacpp.completion([
                    {"role": "system", "content": "You are a helpful AI assistant"},
                    {"role": "user", "content": prompt}
                ])
                return True, response.choices[0].message.content
            except Exception as e:
                return False, f"Error calling TinyLLama model: {str(e)}"
        
        # For API models, use litellm directly
        start_time = time.time()
        
        # Set up additional parameters
        params = {
            "model": model_string, 
            "messages": [
                {"role": "system", "content": "You are a helpful AI assistant"},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1024,
            "temperature": 0.7
        }
        
        # Add API key if needed
        if api_key:
            if model_type == "openai":
                os.environ["OPENAI_API_KEY"] = api_key
            elif model_type == "anthropic":
                os.environ["ANTHROPIC_API_KEY"] = api_key
            elif model_type == "gemini":
                os.environ["GEMINI_API_KEY"] = api_key
                
        # Make the actual API call through litellm
        response = litellm.completion(**params)
        
        # Extract and return the response
        elapsed_time = time.time() - start_time
        result = response.choices[0].message.content
        
        logger.info(f"Response received in {elapsed_time:.2f} seconds")
        return True, result
        
    except Exception as e:
        logger.error(f"Error testing {model_type} model: {str(e)}")
        return False, f"Error: {str(e)}"

def main():
    # Load environment variables
    load_dotenv("botex.env")
    
    # Parse command line arguments
    args = parse_args()
    
    # Determine which models to test
    models_to_test = []
    if args.model == "all":
        models_to_test = ["openai", "anthropic", "gemini", "tinyllama"]
    else:
        models_to_test = [args.model]
    
    # Test each model
    results = {}
    for model_type in models_to_test:
        print(f"\n{'='*50}")
        print(f"Testing {model_type.upper()} model...")
        print(f"{'='*50}")
        
        success, response = test_model(model_type, args.prompt)
        
        if success:
            print(f"\nResponse from {model_type}:")
            print(f"{'-'*30}")
            print(response)
        else:
            print(f"\nError testing {model_type}:")
            print(response)
        
        results[model_type] = {
            "success": success,
            "response": response
        }
    
    # Save results to file
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    output_file = f"model_test_results_{timestamp}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to {output_file}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())