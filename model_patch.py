# model_patch.py
import litellm
from importlib import import_module

def patch_botex():
    """Patch botex to properly recognize Claude models for structured outputs"""
    # Import the botex completion module
    botex_completion = import_module('botex.completion')
    
    # Save the original function
    original_supports_fn = botex_completion.model_supports_response_schema
    
    # Define patched function
    def patched_supports_response_schema(model, custom_llm_provider=None):
        # Directly support Claude models
        if "claude" in model:
            return True
            
        # Call original function for other models
        return original_supports_fn(model, custom_llm_provider)
    
    # Apply the patch
    botex_completion.model_supports_response_schema = patched_supports_response_schema
    print("✅ Botex patched to support Claude models for structured outputs")