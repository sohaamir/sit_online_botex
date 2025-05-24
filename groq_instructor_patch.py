#!/usr/bin/env python3
"""
groq_instructor_patch.py - Groq instructor integration for botex without modifying source code

This module patches botex to use instructor.from_groq() for Groq models while leaving
the original botex source code unchanged.
"""

import logging
import os
from dotenv import load_dotenv

logger = logging.getLogger("botex")

# Load environment variables
load_dotenv("botex.env")

# Check if Groq is available
try:
    from groq import Groq
    import instructor
    GROQ_AVAILABLE = True
    print("✅ GROQ DEBUG: Groq and instructor packages imported successfully")
    logger.info("✅ Groq and instructor packages available")
except ImportError as e:
    print(f"❌ GROQ DEBUG: Failed to import Groq/instructor: {e}")
    logger.warning(f"Groq/instructor packages not available: {e}")
    GROQ_AVAILABLE = False

# Initialize Groq instructor client
groq_instructor_client = None

def initialize_groq_instructor():
    """Initialize Groq instructor client"""
    global groq_instructor_client
    
    print(f"🔍 GROQ DEBUG: Initializing Groq instructor client...")
    
    if not GROQ_AVAILABLE:
        print("❌ GROQ DEBUG: Groq package not available")
        return False
    
    groq_api_key = os.environ.get('GROQ_API_KEY')
    if not groq_api_key:
        print("❌ GROQ DEBUG: No API key found in environment")
        return False
    
    try:
        print("🔍 GROQ DEBUG: Creating Groq client...")
        groq_client = Groq(api_key=groq_api_key)
        
        print("🔍 GROQ DEBUG: Creating instructor client...")
        # Try different modes - JSON mode sometimes causes tool call issues
        try:
            groq_instructor_client = instructor.from_groq(groq_client, mode=instructor.Mode.TOOLS)
            print("✅ GROQ DEBUG: Groq instructor client initialized with TOOLS mode")
        except:
            # Fallback to JSON mode
            groq_instructor_client = instructor.from_groq(groq_client, mode=instructor.Mode.JSON)
            print("✅ GROQ DEBUG: Groq instructor client initialized with JSON mode")
        
        logger.info("✅ Groq instructor client initialized successfully")
        return True
    except Exception as e:
        print(f"❌ GROQ DEBUG: Failed to initialize Groq instructor client: {e}")
        logger.error(f"Failed to initialize Groq instructor client: {e}")
        return False

def groq_instructor_completion(**kwargs):
    """
    Completion function specifically for Groq models using instructor.from_groq()
    """
    print(f"🚀 GROQ DEBUG: groq_instructor_completion called")
    print(f"🔍 GROQ DEBUG: groq_instructor_client exists = {groq_instructor_client is not None}")
    
    if not groq_instructor_client:
        print("❌ GROQ DEBUG: Groq instructor client not initialized")
        raise Exception("Groq instructor client not initialized")
    
    response_format = kwargs.pop("response_format")
    model = kwargs.get("model", "")
    
    print(f"🔍 GROQ DEBUG: Original model = {model}")
    
    # Remove groq/ prefix for the API call
    if model.startswith("groq/"):
        kwargs["model"] = model[5:]  # Remove "groq/" prefix
        print(f"🔍 GROQ DEBUG: Cleaned model = {kwargs['model']}")
    
    # Remove parameters that Groq doesn't support
    kwargs.pop("throttle", None)
    kwargs.pop("api_key", None)  # Groq client already has the API key
    
    print(f"🔍 GROQ DEBUG: Final kwargs keys = {list(kwargs.keys())}")
    print(f"🔍 GROQ DEBUG: Response format type = {type(response_format)}")
    
    # Try instructor approach first
    try:
        print(f"🤖 GROQ DEBUG: Attempting Groq instructor for model: {kwargs['model']}")
        logger.info(f"🤖 Using Groq instructor for model: {kwargs['model']}")
        
        # Use response_model instead of response_format for Groq instructor
        resp_instructor = groq_instructor_client.chat.completions.create(
            response_model=response_format,
            temperature=kwargs.get('temperature', 0.7),
            max_tokens=kwargs.get('max_tokens', 2048),
            messages=kwargs.get('messages', []),
            model=kwargs['model']
        )
        
        print(f"✅ GROQ DEBUG: Groq instructor completion successful")
        print(f"🔍 GROQ DEBUG: Response type = {type(resp_instructor)}")
        
        result = {
            'resp_str': resp_instructor.model_dump_json(),
            'finish_reason': 'stop'
        }
        
        print(f"🔍 GROQ DEBUG: Result keys = {list(result.keys())}")
        return result
        
    except Exception as instructor_error:
        print(f"⚠️ GROQ DEBUG: Instructor approach failed: {instructor_error}")
        logger.warning(f"Groq instructor failed, trying fallback: {instructor_error}")
        
        # Fallback: Use regular Groq completion and extract JSON
        try:
            print(f"🔄 GROQ DEBUG: Attempting fallback with regular Groq completion")
            
            # Create a direct Groq client for fallback
            groq_api_key = os.environ.get('GROQ_API_KEY')
            if not groq_api_key:
                raise Exception("GROQ_API_KEY not available for fallback")
            
            from groq import Groq
            fallback_client = Groq(api_key=groq_api_key)
            
            # Modify the last message to be more explicit about JSON-only response
            messages = kwargs.get('messages', [])
            if messages:
                last_message = messages[-1].copy()
                last_message['content'] += "\n\n🚨 CRITICAL: Respond with ONLY the JSON object. No explanations, no tool calls, no markdown. Start immediately with { and end with }."
                modified_messages = messages[:-1] + [last_message]
            else:
                modified_messages = messages
            
            fallback_response = fallback_client.chat.completions.create(
                messages=modified_messages,
                model=kwargs['model'],
                temperature=kwargs.get('temperature', 0.7),
                max_tokens=kwargs.get('max_tokens', 2048),
            )
            
            content = fallback_response.choices[0].message.content.strip()
            print(f"🔍 GROQ DEBUG: Fallback response content: {content[:200]}...")
            
            # Extract JSON from the response
            import json
            import re
            
            # Try to find and extract JSON object
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                print(f"🔍 GROQ DEBUG: Extracted JSON: {json_str[:100]}...")
                
                # Validate it's proper JSON
                try:
                    parsed_json = json.loads(json_str)
                    print(f"✅ GROQ DEBUG: JSON validation successful")
                    
                    result = {
                        'resp_str': json_str,
                        'finish_reason': 'stop'
                    }
                    
                    print(f"✅ GROQ DEBUG: Fallback completion successful")
                    return result
                    
                except json.JSONDecodeError as json_error:
                    print(f"❌ GROQ DEBUG: Invalid JSON extracted: {json_error}")
                    raise Exception(f"Invalid JSON in fallback response: {json_error}")
            else:
                print(f"❌ GROQ DEBUG: No JSON found in fallback response")
                raise Exception("No valid JSON found in fallback response")
                
        except Exception as fallback_error:
            print(f"❌ GROQ DEBUG: Fallback also failed: {fallback_error}")
            logger.error(f"Both Groq instructor and fallback failed: {fallback_error}")
            
            # Re-raise the original instructor error
            raise instructor_error

def patch_botex_for_groq():
    """
    Monkey-patch botex completion function to handle Groq models with instructor
    """
    print(f"🔍 GROQ DEBUG: Starting to patch botex...")
    
    try:
        # Import botex to access its completion functions
        import botex
        print(f"🔍 GROQ DEBUG: botex imported successfully")
        
        # Try different ways to access the completion module
        completion_module = None
        completion_function = None
        model_supports_function = None
        
        # Method 1: Try accessing as submodule
        try:
            from botex import completion as completion_module
            completion_function = completion_module.completion
            model_supports_function = completion_module.model_supports_response_schema
            print(f"🔍 GROQ DEBUG: Accessed completion via submodule import")
        except (ImportError, AttributeError):
            pass
        
        # Method 2: Try accessing directly from botex
        if completion_function is None:
            try:
                completion_function = botex.completion
                print(f"🔍 GROQ DEBUG: Accessed completion function directly from botex")
                # For model_supports_response_schema, we might need to access it differently
                if hasattr(botex, 'model_supports_response_schema'):
                    model_supports_function = botex.model_supports_response_schema
                else:
                    # Create a default function that works for most cases
                    def default_model_supports_response_schema(model: str, custom_llm_provider: str = None) -> bool:
                        if model == "llamacpp": 
                            return True
                        if model and "/" in model and model.split("/")[0].lower() == "groq":
                            return False
                        if custom_llm_provider and custom_llm_provider.lower() == "groq":
                            return False
                        # Default to True for other models
                        return True
                    model_supports_function = default_model_supports_response_schema
                    print(f"🔍 GROQ DEBUG: Using default model_supports_response_schema function")
            except AttributeError:
                pass
        
        # Method 3: Try importing the completion module directly
        if completion_function is None:
            try:
                import botex.completion as completion_module
                completion_function = completion_module.completion
                model_supports_function = completion_module.model_supports_response_schema
                print(f"🔍 GROQ DEBUG: Accessed completion via direct module import")
            except (ImportError, AttributeError):
                pass
        
        if completion_function is None:
            raise Exception("Could not find completion function in botex")
        
        print(f"🔍 GROQ DEBUG: Found completion function: {completion_function}")
        print(f"🔍 GROQ DEBUG: Found model_supports function: {model_supports_function}")
        
        # Store the original functions
        original_completion = completion_function
        original_model_supports_schema = model_supports_function
        
        def patched_model_supports_response_schema(model: str, custom_llm_provider: str = None) -> bool:
            """
            Patched version that forces Groq models to use instructor fallback
            """
            print(f"🔍 GROQ DEBUG: Checking model support for: {model}")
            
            # Force Groq models to return False (use instructor fallback)
            if model and "/" in model and model.split("/")[0].lower() == "groq":
                print(f"🔧 GROQ DEBUG: Detected Groq model {model}, forcing instructor fallback")
                logger.info(f"🔧 GROQ PATCH: Forcing {model} to use instructor fallback")
                return False
            
            if custom_llm_provider and custom_llm_provider.lower() == "groq":
                print(f"🔧 GROQ DEBUG: Detected Groq provider for {model}, forcing instructor fallback")
                logger.info(f"🔧 GROQ PATCH: Forcing {model} (provider: {custom_llm_provider}) to use instructor fallback")
                return False
            
            # Use original function for non-Groq models
            if original_model_supports_schema:
                result = original_model_supports_schema(model, custom_llm_provider)
                print(f"🔍 GROQ DEBUG: Non-Groq model {model} schema support = {result}")
                return result
            else:
                # Fallback logic
                return True
        
        def patched_completion(**kwargs):
            """
            Patched completion function that handles Groq models specially
            """
            model = kwargs.get("model", "")
            print(f"🔍 GROQ DEBUG: Completion called for model: {model}")
            
            # Check if this is a Groq model
            if model and "/" in model and model.split("/")[0].lower() == "groq":
                print(f"🔧 GROQ DEBUG: Detected Groq model, checking instructor client...")
                if groq_instructor_client:
                    print(f"🔧 GROQ DEBUG: Using Groq instructor for {model}")
                    logger.info(f"🔧 GROQ PATCH: Using Groq instructor for {model}")
                    return groq_instructor_completion(**kwargs)
                else:
                    print(f"❌ GROQ DEBUG: Groq instructor client not available, falling back")
                    logger.warning("🔧 GROQ PATCH: Groq instructor client not available, falling back to original")
            else:
                print(f"🔍 GROQ DEBUG: Non-Groq model, using original completion")
            
            # Use original completion for non-Groq models
            return original_completion(**kwargs)
        
        # Apply the patches based on how we accessed the functions
        if completion_module:
            # We have the module, patch it directly
            completion_module.model_supports_response_schema = patched_model_supports_response_schema
            completion_module.completion = patched_completion
            print("✅ GROQ DEBUG: Successfully patched completion module functions")
        else:
            # We accessed functions directly from botex, patch them there
            botex.completion = patched_completion
            if hasattr(botex, 'model_supports_response_schema'):
                botex.model_supports_response_schema = patched_model_supports_response_schema
            print("✅ GROQ DEBUG: Successfully patched botex functions directly")
        
        logger.info("✅ GROQ PATCH: Successfully patched botex for Groq compatibility")
        return True
        
    except Exception as e:
        print(f"❌ GROQ DEBUG: Failed to patch botex: {e}")
        logger.error(f"❌ GROQ PATCH: Failed to patch botex: {e}")
        import traceback
        traceback.print_exc()
        return False

def apply_groq_patch():
    """
    Main function to apply the Groq patch
    """
    print(f"🔍 GROQ DEBUG: Starting Groq patch application...")
    
    if not GROQ_AVAILABLE:
        print("❌ GROQ DEBUG: Groq packages not available, skipping patch")
        logger.info("Groq packages not available, skipping Groq patch")
        return False
    
    # Initialize Groq instructor client
    print(f"🔍 GROQ DEBUG: Initializing Groq instructor...")
    if not initialize_groq_instructor():
        print("❌ GROQ DEBUG: Failed to initialize Groq instructor, skipping patch")
        logger.warning("Failed to initialize Groq instructor, skipping Groq patch")
        return False
    
    # Apply the patch
    print(f"🔍 GROQ DEBUG: Applying botex patch...")
    success = patch_botex_for_groq()
    
    if success:
        print("✅ GROQ DEBUG: Groq patch applied successfully!")
    else:
        print("❌ GROQ DEBUG: Failed to apply Groq patch")
    
    return success

# Auto-apply the patch when this module is imported
if __name__ != "__main__":
    print(f"🔍 GROQ DEBUG: Module imported, applying patch...")
    apply_groq_patch()
    print(f"🔍 GROQ DEBUG: Patch application complete")