#!/usr/bin/env python3
"""
Check parameter support for all models in LiteLLM
Specifically focusing on response_format and JSON mode support
"""

import litellm
import json
from tabulate import tabulate

def check_model_support():
    results = []
    
    # Define model categories to check
    model_categories = {
        "OpenAI": ["gpt-4o-2024-05-13", "gpt-4.1-nano-2025-04-14", "gpt-3.5-turbo"],
        "Anthropic": ["anthropic/claude-3-haiku-20240307", "anthropic/claude-3-sonnet-20240229", "anthropic/claude-3-opus-20240229"],
        "Google": ["gemini/gemini-1.5-flash", "gemini/gemini-1.5-pro", "gemini/gemini-1.0-pro"],
        "Ollama": ["ollama/llama3"]
    }
    
    # Check each model
    for provider, models in model_categories.items():
        for model in models:
            try:
                # Get supported parameters
                params = litellm.get_supported_openai_params(model=model)
                
                # Check specific parameters
                supports_response_format = "response_format" in params
                supports_json = supports_response_format and litellm.supports_response_schema(model=model)
                
                # Store results
                results.append({
                    "Provider": provider,
                    "Model": model,
                    "Response Format": "✓" if supports_response_format else "✗",
                    "JSON Mode": "✓" if supports_json else "✗",
                    "Parameters": ", ".join(sorted(params))
                })
                
            except Exception as e:
                # Handle any errors
                results.append({
                    "Provider": provider,
                    "Model": model,
                    "Response Format": "Error",
                    "JSON Mode": "Error",
                    "Parameters": f"Error: {str(e)}"
                })
    
    return results

if __name__ == "__main__":
    print("\nChecking parameter support for all models in LiteLLM...\n")
    
    # Get results
    results = check_model_support()
    
    # Print table of results
    print(tabulate([
        [r["Provider"], r["Model"], r["Response Format"], r["JSON Mode"]]
        for r in results
    ], headers=["Provider", "Model", "Response Format", "JSON Mode"], tablefmt="grid"))
    
    # Print detailed parameter support for each model
    for result in results:
        model = result["Model"]
        print(f"\n\n{'-'*80}")
        print(f"Parameters supported by {model}:")
        print(f"{'-'*80}")
        print(result["Parameters"])