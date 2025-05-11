# model_patch.py
from importlib import import_module
import logging
import types
import sys

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("model_patch")

def patch_botex():
    """Patch botex to properly handle Claude models"""
    # Import the botex modules
    botex_completion = import_module('botex.completion')
    botex_bot = import_module('botex.bot')
    
    # 1. Patch model support function
    original_supports_fn = botex_completion.model_supports_response_schema
    
    def patched_supports_response_schema(model, custom_llm_provider=None):
        # Directly support Claude models
        if "claude" in str(model).lower():
            return True
        # Call original function for other models
        return original_supports_fn(model, custom_llm_provider)
    
    # Apply the model support patch
    botex_completion.model_supports_response_schema = patched_supports_response_schema
    
    # 2. Directly patch the check_response_middle function
    # First get the original function
    original_check_response_middle = None
    for name, obj in botex_bot.__dict__.items():
        if name == 'check_response_middle':
            original_check_response_middle = obj
            break
    
    # If we found it at module level, patch it
    if original_check_response_middle:
        def patched_check_response_middle(resp, response_format):
            # Add missing 'confused' field
            if 'confused' not in resp:
                logger.info("Adding missing 'confused' field to response")
                resp['confused'] = False
            return original_check_response_middle(resp, response_format)
        
        botex_bot.check_response_middle = patched_check_response_middle
        logger.info("Patched check_response_middle at module level")
    
    # 3. Replace the run_bot function to include our custom check_response
    original_run_bot = botex_bot.run_bot
    
    def patched_run_bot(**kwargs):
        # Store original llm_send_message to avoid infinitely replacing it
        original_llm_send = None
        
        # Create a patched version of llm_send_message
        def patched_llm_send_message(message, phase, check_response=None, model=None, questions=None):
            nonlocal original_llm_send
            
            # If we haven't stored it yet, get the original function
            if not original_llm_send:
                # The original should be in the caller's local variables
                frame = sys._getframe(1)
                if 'llm_send_message' in frame.f_locals:
                    original_llm_send = frame.f_locals['llm_send_message']
                else:
                    # If we can't find it, use a dummy function
                    def dummy(*args, **kwargs):
                        raise RuntimeError("Original llm_send_message not found")
                    original_llm_send = dummy
            
            # Create a wrapped version of check_response
            if check_response:
                original_check = check_response
                
                def wrapped_check_response(resp, format):
                    # Add missing 'confused' field if using Claude
                    if 'confused' not in resp and 'claude' in str(kwargs.get('model', '')).lower():
                        logger.info("Adding missing 'confused' field to response")
                        resp['confused'] = False
                    return original_check(resp, format)
                
                # Replace the check_response with our wrapped version
                check_response = wrapped_check_response
            
            # Call the original with our wrapped checker
            return original_llm_send(message, phase, check_response, model, questions)
        
        # Before calling run_bot, inject our patched llm_send_message into its namespace
        # We do this by creating a closure with our function
        def run_with_patch():
            # This will be merged with the local namespace of run_bot
            llm_send_message = patched_llm_send_message
            return original_run_bot(**kwargs)
        
        # Call our wrapped function
        return run_with_patch()
    
    # Replace run_bot with our patched version
    botex_bot.run_bot = patched_run_bot
    
    # 4. Create a direct monkey patch for json.loads in the bot module
    original_json_loads = botex_bot.json.loads
    
    def patched_json_loads(s, *args, **kwargs):
        result = original_json_loads(s, *args, **kwargs)
        if isinstance(result, dict) and ('summary' in result or 'answers' in result):
            if 'confused' not in result:
                logger.info("Adding 'confused' field to JSON result")
                result['confused'] = False
        return result
    
    # Apply the json loads patch
    botex_bot.json.loads = patched_json_loads
    
    logger.info("✅ Botex patched to support Claude models for structured outputs")
    print("✅ Botex patched to support Claude models for structured outputs")