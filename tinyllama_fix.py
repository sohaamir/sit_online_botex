# tinyllama_fix.py

from botex import llamacpp, bot
import types
import json
import logging
import requests
from tinyllama_prompts import get_tinyllama_prompt

# Fix 1: Patch the health check function
original_health_check = llamacpp.is_llamacpp_server_reachable

def patched_health_check(url, timeout=6):
    if "localhost:8080" in url:
        print(f"Health check bypassed for llama.cpp server at {url}")
        return True
    return original_health_check(url, timeout)

# Fix 2: Patch the model metadata function with appropriate limits
def patched_set_params(self):
    print(f"Using TinyLLaMA-optimized parameters")
    self.local_llm_path = "tinyllama-1.1b" 
    self.context_length = 2048
    self.num_slots = 1
    self.max_tokens = 256  # Very conservative output limit
    self.temperature = 0.7
    self.top_p = 0.9
    self.top_k = 40
    print(f"Set context_length={self.context_length}, max_tokens={self.max_tokens}")

# Fix 3: Patch the completion function to handle token limits
def patched_completion(self, messages, response_format=None):
    """TinyLLaMA-optimized completion function"""
    print(f"Using TinyLLaMA-optimized completion function")
    url = f"{self.api_base}/v1/chat/completions"
    
    # Always just keep the first message (system) and last message (current query)
    if len(messages) > 2:
        messages = [messages[0], messages[-1]]
        print(f"Truncated to essential messages only")
    
    # Further truncate content if needed
    for i, msg in enumerate(messages):
        if len(msg["content"]) > 800:
            if i == 0:  # System message
                messages[i]["content"] = msg["content"][:500] + "..."
            else:  # User message - keep more of this one
                messages[i]["content"] = msg["content"][:800] + "..."
            print(f"Truncated message {i} content")
    
    # Create minimal payload
    payload = {
        "model": self.local_llm_path,
        "messages": messages,
        "temperature": self.temperature,
        "max_tokens": 256  # Hard conservative limit
    }
    
    print(f"Requesting completion with {len(messages)} messages")
    
    # Send the request with error handling
    attempts = 0
    last_error = None
    
    while attempts < 3:
        try:
            response = requests.post(url, json=payload, timeout=120)
            
            if response.status_code != 200:
                print(f"Error response: {response.text[:200]}")
                
                # Context length problems - try more aggressive truncation
                if "context_length" in response.text and attempts < 2:
                    if len(messages) > 1:
                        # Keep only the latest message in extreme cases
                        messages = [{"role": "user", "content": messages[-1]["content"][:400]}]
                        payload["messages"] = messages
                        payload["max_tokens"] = 128  # Even more conservative
                        print(f"Extreme truncation: single message, max_tokens={payload['max_tokens']}")
                    else:
                        # If we're already at one message, cut it further
                        messages[0]["content"] = messages[0]["content"][:300]
                        payload["max_tokens"] = 100
                        print(f"Final attempt with heavily truncated content")
                    
                    attempts += 1
                    continue
            
            response.raise_for_status()
            result = response.json()
            
            # Minimal response format
            adapted_response = {
                "id": "tinyllama_response",
                "object": "chat.completion",
                "created": 0,
                "model": "tinyllama",
                "usage": {"completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0},
                "choices": result.get("choices", [])
            }
            
            return llamacpp.ChatCompletionResponse(**adapted_response)
            
        except Exception as e:
            attempts += 1
            last_error = e
            print(f"Error in TinyLLaMA completion ({attempts}/3): {e}")
            
    raise Exception(f"All completion attempts failed: {last_error}")

# Fix 4: Patch botex message handling to use our specialized prompts
original_prepare_message = bot.prepare_message

def patched_prepare_message(prompt_type, summary="", full_conv_history=False, **kwargs):
    print(f"Using TinyLLaMA-optimized prompt for {prompt_type}")
    
    # Use our specialized TinyLLaMA prompts
    prompt_context = {
        "summary": summary,
        **kwargs
    }
    
    # Construct minimal prompt using our specialized function
    content = get_tinyllama_prompt(prompt_type, prompt_context)
    return {"role": "user", "content": content}

# Apply all patches
llamacpp.is_llamacpp_server_reachable = patched_health_check
llamacpp.LlamaCpp.set_params_from_running_api = patched_set_params
llamacpp.LlamaCpp.completion = patched_completion
bot.prepare_message = patched_prepare_message

print("TinyLLaMA-optimized patches applied successfully!")