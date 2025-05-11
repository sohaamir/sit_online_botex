import os
import json
from dotenv import load_dotenv
import litellm

# Load environment variables to get API keys
load_dotenv()

def check_model_support(model, provider=None):
    """Check if a model supports response_format parameter according to litellm"""
    try:
        params = litellm.get_supported_openai_params(
            model=model, 
            custom_llm_provider=provider
        )
        
        supports_schema = litellm.supports_response_schema(
            model=model,
            custom_llm_provider=provider
        )
        
        return {
            "model": model,
            "provider": provider,
            "supported_params": params,
            "response_format_supported": "response_format" in params,
            "litellm_reports_schema_support": supports_schema
        }
    except Exception as e:
        return {
            "model": model,
            "provider": provider,
            "error": str(e)
        }

def test_actual_response(model, provider=None):
    """Test if the model can actually produce structured JSON responses"""
    try:
        # Define a simple Pydantic-like schema
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "is_student": {"type": "boolean"}
            },
            "required": ["name", "age", "is_student"]
        }
        
        # Set up model parameters
        model_params = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Please return info about John Doe who is 25 years old and is a student."}
            ],
            "max_tokens": 500
        }
        
        # Add API key if needed
        if provider == "anthropic" or "claude" in model.lower():
            if os.environ.get("ANTHROPIC_API_KEY"):
                os.environ["ANTHROPIC_API_KEY"] = os.environ.get("ANTHROPIC_API_KEY")
        
        # Try with response_format
        format_error = None
        try:
            model_params["response_format"] = {"type": "json_object", "schema": schema}
            response_with_format = litellm.completion(**model_params)
            json_result = json.loads(response_with_format.choices[0].message.content)
            format_works = isinstance(json_result, dict) and all(k in json_result for k in ["name", "age", "is_student"])
        except Exception as e:
            format_works = False
            format_error = str(e)
        
        # Try with system prompt instruction
        model_params.pop("response_format", None)
        model_params["messages"][0]["content"] = "You are a helpful assistant. Always respond in JSON format matching this schema: " + json.dumps(schema)
        
        response_with_instruction = litellm.completion(**model_params)
        try:
            instruction_json = json.loads(response_with_instruction.choices[0].message.content)
            instruction_works = isinstance(instruction_json, dict) and all(k in instruction_json for k in ["name", "age", "is_student"])
        except:
            instruction_works = False
        
        return {
            "model": model,
            "provider": provider,
            "response_format_parameter_works": format_works,
            "format_error": format_error if not format_works else None,
            "system_instruction_works": instruction_works,
            "sample_response": response_with_instruction.choices[0].message.content[:200]
        }
    except Exception as e:
        return {
            "model": model,
            "provider": provider,
            "error": str(e)
        }

# Models to test
models_to_check = [
    # OpenAI models (known to support response_format)
    {"model": "gpt-4o-2024-05-13", "provider": None},
    
    # Claude models - different formats
    {"model": "claude-3-haiku-20240307", "provider": "anthropic"},
    {"model": "anthropic/claude-3-haiku-20240307", "provider": None},
    {"model": "claude-3-sonnet-20240229", "provider": "anthropic"},
    {"model": "claude-3-opus-20240229", "provider": "anthropic"},
    
    # Claude via Bedrock
    {"model": "anthropic.claude-3-sonnet-20240229", "provider": "bedrock"},
]

# Run tests
print("\n=== CHECKING MODEL PARAMETER SUPPORT ===")
support_results = []
for model_info in models_to_check:
    result = check_model_support(**model_info)
    support_results.append(result)
    print(f"\n{model_info['model']} ({model_info['provider'] or 'default'}):")
    print(f"  Response format supported: {result.get('response_format_supported', 'ERROR')}")
    print(f"  LiteLLM reports schema support: {result.get('litellm_reports_schema_support', 'ERROR')}")
    if "error" in result:
        print(f"  Error: {result['error']}")

print("\n\n=== PRACTICAL JSON OUTPUT TEST ===")
practical_results = []
for model_info in models_to_check:
    try:
        result = test_actual_response(**model_info)
        practical_results.append(result)
        print(f"\n{model_info['model']} ({model_info['provider'] or 'default'}):")
        print(f"  response_format parameter works: {result.get('response_format_parameter_works', 'ERROR')}")
        print(f"  System instruction works: {result.get('system_instruction_works', 'ERROR')}")
        if "sample_response" in result:
            print(f"  Sample: {result['sample_response'][:100]}...")
        if "error" in result:
            print(f"  Error: {result['error']}")
    except Exception as e:
        print(f"\n{model_info['model']} ({model_info['provider'] or 'default'}):")
        print(f"  Error in test: {str(e)}")

# Save complete results to file
with open("litellm_model_support_test.json", "w") as f:
    json.dump({
        "parameter_support": support_results,
        "practical_tests": practical_results
    }, f, indent=2)

print(f"\nComplete results saved to litellm_model_support_test.json")