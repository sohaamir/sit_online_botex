# test_claude_litellm.py
import os
import json
import time
from dotenv import load_dotenv
import litellm

# Load environment variables
load_dotenv("botex.env")

# Get API key
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    print("Error: ANTHROPIC_API_KEY not found in environment variables")
    exit(1)

# Make litellm more verbose
litellm.set_verbose = True

# Test with the same prompt structure botex would use
system_prompt = """You are participating in an online survey and/or experiment. The user provides you with a series of independent prompts."""
user_prompt = """Do you understand your task? Please answer with the following structure: {"task": "Your summary of your task", "understood": true}"""

# Set the schema in the response_format
schema = {
    "type": "object", 
    "properties": {
        "task": {"type": "string"}, 
        "understood": {"type": "boolean"}
    },
    "required": ["task", "understood"]
}

# Prepare request parameters
params = {
    "model": "claude-3-haiku-20240307",
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    "max_tokens": 256,
    "temperature": 0.7,
    "api_key": api_key,
    "timeout": 60,
    "response_format": {"type": "json_object", "schema": schema}
}

# Run test
print("Testing Claude via litellm...")
start_time = time.time()

try:
    response = litellm.completion(**params)
    elapsed = time.time() - start_time
    
    print(f"Response received in {elapsed:.2f} seconds")
    print(f"Response: {response.choices[0].message.content}")
    
    # Try to parse as JSON
    try:
        result = json.loads(response.choices[0].message.content)
        print(f"Parsed JSON: {json.dumps(result, indent=2)}")
    except json.JSONDecodeError:
        print("Response is not valid JSON")
        
except Exception as e:
    elapsed = time.time() - start_time
    print(f"Error after {elapsed:.2f} seconds: {str(e)}")
    print("\nSuggested solution:")
    print("- Try updating litellm: pip install --upgrade litellm")
    print("- Check if you're using the correct model string format")
    print("- Verify your API key has the correct permissions")