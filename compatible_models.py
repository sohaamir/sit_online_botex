#!/usr/bin/env python3
"""
Comprehensive Model Discovery Script for Botex Compatibility

This script systematically tests models from all major providers to determine
which ones support the structured outputs required by botex.
"""
import litellm
import pydantic
import os
import sys
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

try:
    import litellm
    from pydantic import BaseModel, Field
except ImportError:
    print("Please install: pip install litellm pydantic")
    sys.exit(1)

@dataclass
class ModelResult:
    model: str
    provider: str
    response_format_supported: bool
    schema_support: bool
    botex_compatible: bool
    api_test_result: Optional[str] = None
    notes: str = ""

class TestSchema(BaseModel):
    """Simple test schema for API testing"""
    understanding: bool = Field(description="Whether you understood the task")
    message: str = Field(description="A simple response message")

# Comprehensive list of models to test organized by provider
TEST_MODELS = {
    "OpenAI": [
        "gpt-4o",
        "gpt-4o-mini", 
        "gpt-4o-2024-08-06",
        "gpt-4o-mini-2024-07-18",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ],
    "Anthropic": [
        "anthropic/claude-3-5-sonnet-20241022",
        "anthropic/claude-3-5-haiku-20241022", 
        "anthropic/claude-3-opus-20240229",
        "anthropic/claude-3-sonnet-20240229",
        "anthropic/claude-3-haiku-20240307",
    ],
    "Google": [
        "gemini/gemini-1.5-pro",
        "gemini/gemini-1.5-flash",
        "gemini/gemini-1.5-flash-8b",
        "gemini/gemini-2.0-flash-exp",
        "vertex_ai/gemini-1.5-pro",
        "vertex_ai/gemini-1.5-flash",
    ],
    "Azure OpenAI": [
        "azure/gpt-4o",
        "azure/gpt-4o-mini",
        "azure/gpt-4-turbo",
        "azure/gpt-35-turbo",
    ],
    "Cohere": [
        "cohere/command-r-plus",
        "cohere/command-r",
        "cohere/command",
    ],
    "Mistral": [
        "mistral/mistral-large-latest",
        "mistral/mistral-medium-latest", 
        "mistral/mistral-small-latest",
        "mistral/codestral-latest",
    ],
    "Deepseek": [
        "deepseek/deepseek-chat",
        "deepseek/deepseek-reasoner",
    ],
    "Groq": [
        "groq/llama-3.1-70b-versatile",
        "groq/llama-3.1-8b-instant",
        "groq/mixtral-8x7b-32768",
        "groq/llama3-8b-8192",
        "groq/llama3-70b-8192",
        "groq/gemma-7b-it",
    ],
    "Together AI": [
        "together_ai/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "together_ai/mistralai/Mixtral-8x7B-Instruct-v0.1",
        "together_ai/microsoft/DialoGPT-medium",
    ],
    "Fireworks AI": [
        "fireworks_ai/accounts/fireworks/models/llama-v3p1-70b-instruct",
        "fireworks_ai/accounts/fireworks/models/llama-v3p1-8b-instruct",
        "fireworks_ai/accounts/fireworks/models/mixtral-8x7b-instruct",
    ],
    "OpenRouter": [
        "openrouter/anthropic/claude-3.5-sonnet",
        "openrouter/openai/gpt-4o",
        "openrouter/google/gemini-pro",
        "openrouter/meta-llama/llama-3.1-70b-instruct",
    ],
    "Bedrock (AWS)": [
        "bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0",
        "bedrock/anthropic.claude-3-haiku-20240307-v1:0",
        "bedrock/meta.llama3-1-70b-instruct-v1:0",
        "bedrock/mistral.mistral-large-2402-v1:0",
    ],
    "Perplexity": [
        "perplexity/llama-3.1-sonar-large-128k-online",
        "perplexity/llama-3.1-sonar-small-128k-online",
        "perplexity/llama-3.1-8b-instruct",
    ],
    "Hugging Face": [
        "huggingface/meta-llama/Meta-Llama-3.1-8B-Instruct",
        "huggingface/microsoft/DialoGPT-medium",
        "huggingface/google/flan-t5-large",
    ],
    "Ollama (Local)": [
        "ollama/llama3.1",
        "ollama/llama3.1:8b",
        "ollama/mistral",
        "ollama/codellama",
        "ollama_chat/llama3.1",  # Alternative format for better chat
    ],
    "VLLM": [
        "openai/meta-llama/Meta-Llama-3.1-8B-Instruct",  # Via VLLM server
        "openai/microsoft/DialoGPT-medium",
    ],
    "Replicate": [
        "replicate/meta/meta-llama-3-70b-instruct",
        "replicate/mistralai/mixtral-8x7b-instruct-v0.1",
    ],
    "AI21": [
        "ai21/jamba-1.5-large",
        "ai21/jamba-1.5-mini",
    ],
    "Anyscale": [
        "anyscale/meta-llama/Llama-2-70b-chat-hf",
        "anyscale/mistralai/Mixtral-8x7B-Instruct-v0.1",
    ],
}

def check_model_support(model: str) -> ModelResult:
    """Check if a model supports botex requirements"""
    
    # Determine provider from model string
    if "/" in model:
        provider = model.split("/")[0]
    else:
        provider = "openai"  # Default for models without prefix
    
    # Initialize result
    result = ModelResult(
        model=model,
        provider=provider,
        response_format_supported=False,
        schema_support=False,
        botex_compatible=False
    )
    
    try:
        # Check if response_format parameter is supported
        params = litellm.get_supported_openai_params(model=model)
        result.response_format_supported = "response_format" in params
        
        # Check if model supports response schema
        result.schema_support = litellm.supports_response_schema(model=model)
        
        # Model is botex compatible if it supports both or is llamacpp
        result.botex_compatible = (
            model == "llamacpp" or 
            (result.response_format_supported and result.schema_support)
        )
        
    except Exception as e:
        result.notes = f"Error checking support: {str(e)}"
    
    return result

def test_api_call(model: str, timeout: int = 10) -> str:
    """Test actual API call with structured output"""
    
    # Check for required API keys
    required_keys = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY", 
        "gemini": "GEMINI_API_KEY",
        "vertex_ai": "GOOGLE_APPLICATION_CREDENTIALS",
        "azure": "AZURE_API_KEY",
        "cohere": "COHERE_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "groq": "GROQ_API_KEY",
        "together_ai": "TOGETHER_API_KEY",
        "fireworks_ai": "FIREWORKS_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "bedrock": "AWS_ACCESS_KEY_ID",
        "perplexity": "PERPLEXITYAI_API_KEY",
        "huggingface": "HUGGINGFACE_API_KEY",
        "replicate": "REPLICATE_API_TOKEN",
        "ai21": "AI21_API_KEY",
    }
    
    provider = model.split("/")[0] if "/" in model else "openai"
    api_key_env = required_keys.get(provider)
    
    if api_key_env and not os.environ.get(api_key_env):
        return f"❌ {api_key_env} not set"
    
    try:
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "user", "content": "Respond in JSON format with 'understanding' (boolean) and 'message' (string)."}
            ],
            response_format=TestSchema.model_json_schema(),
            timeout=timeout,
            max_tokens=100,
        )
        
        # Try to parse the response as JSON to verify structure
        content = response.choices[0].message.content
        parsed = json.loads(content)
        
        if "understanding" in parsed and "message" in parsed:
            return "✅ Success"
        else:
            return "⚠️ JSON missing required fields"
            
    except Exception as e:
        return f"❌ {str(e)[:50]}..."

def generate_report(results: List[ModelResult], test_apis: bool = False) -> None:
    """Generate a comprehensive compatibility report"""
    
    print("\n" + "="*100)
    print("                         BOTEX MODEL COMPATIBILITY REPORT")
    print("="*100)
    
    # Summary statistics
    total_models = len(results)
    compatible_models = sum(1 for r in results if r.botex_compatible)
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total models tested: {total_models}")
    print(f"   Botex compatible: {compatible_models}")
    print(f"   Compatibility rate: {compatible_models/total_models*100:.1f}%")
    
    # Group by provider
    by_provider = {}
    for result in results:
        if result.provider not in by_provider:
            by_provider[result.provider] = []
        by_provider[result.provider].append(result)
    
    print(f"\n📋 DETAILED RESULTS:")
    print(f"{'Provider':<15} | {'Model':<50} | {'Format':<6} | {'Schema':<6} | {'Compatible':<10} {'API Test' if test_apis else ''}")
    print("-" * (90 + (12 if test_apis else 0)))
    
    for provider, provider_results in sorted(by_provider.items()):
        for i, result in enumerate(sorted(provider_results, key=lambda x: x.model)):
            provider_name = provider if i == 0 else ""
            model_short = result.model.replace(f"{provider}/", "") if "/" in result.model else result.model
            
            format_icon = "✅" if result.response_format_supported else "❌"
            schema_icon = "✅" if result.schema_support else "❌"
            compat_icon = "✅" if result.botex_compatible else "❌"
            
            line = f"{provider_name:<15} | {model_short:<50} | {format_icon:<6} | {schema_icon:<6} | {compat_icon:<10}"
            
            if test_apis and hasattr(result, 'api_test_result'):
                line += f" {result.api_test_result}"
            
            print(line)
            
            if result.notes:
                print(f"{'':17}   Note: {result.notes}")
    
    # Compatible models summary
    compatible = [r for r in results if r.botex_compatible]
    if compatible:
        print(f"\n✅ BOTEX-COMPATIBLE MODELS ({len(compatible)} total):")
        by_provider_compat = {}
        for result in compatible:
            if result.provider not in by_provider_compat:
                by_provider_compat[result.provider] = []
            by_provider_compat[result.provider].append(result.model)
        
        for provider, models in sorted(by_provider_compat.items()):
            print(f"\n  {provider.upper()}:")
            for model in sorted(models):
                model_short = model.replace(f"{provider}/", "") if "/" in model else model
                print(f"    • {model_short}")
    
    # Usage instructions
    print(f"\n📝 USAGE INSTRUCTIONS:")
    print(f"   1. Add compatible models to your botex.env file")
    print(f"   2. Set required API keys as environment variables")
    print(f"   3. Use model names in your player_models.csv file")
    print(f"   4. Note: Some providers may require additional setup (auth, billing, etc.)")

def main():
    print("🔍 Discovering botex-compatible models across all providers...")
    print("This may take a few minutes as we test many models...")
    
    # Flatten all models for testing
    all_models = []
    for provider_models in TEST_MODELS.values():
        all_models.extend(provider_models)
    
    print(f"\nTesting {len(all_models)} models from {len(TEST_MODELS)} providers...")
    
    # Test models (with some parallelization for speed)
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_model = {
            executor.submit(check_model_support, model): model 
            for model in all_models
        }
        
        for future in as_completed(future_to_model):
            model = future_to_model[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                # Create error result
                provider = model.split("/")[0] if "/" in model else "openai"
                error_result = ModelResult(
                    model=model,
                    provider=provider,
                    response_format_supported=False,
                    schema_support=False,
                    botex_compatible=False,
                    notes=f"Test failed: {str(e)}"
                )
                results.append(error_result)
    
    # Ask if user wants to test APIs
    test_apis = input("\n🧪 Do you want to test actual API calls? (requires API keys) [y/N]: ").lower().startswith('y')
    
    if test_apis:
        print("\n🔬 Testing API calls for compatible models...")
        compatible_models = [r for r in results if r.botex_compatible]
        
        for result in compatible_models:
            print(f"Testing {result.model}...", end=" ")
            result.api_test_result = test_api_call(result.model)
            print(result.api_test_result)
    
    # Generate comprehensive report
    generate_report(results, test_apis)
    
    print(f"\n💡 TIP: Focus on providers where you already have API keys or can easily get them.")
    print(f"    Free tiers are available for: Gemini, Groq, Hugging Face, and Ollama (local)")

if __name__ == "__main__":
    main()