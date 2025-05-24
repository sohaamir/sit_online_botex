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
    print(f"🔍 GROQ DEBUG: GROQ_AVAILABLE = {GROQ_AVAILABLE}")
    
    if not GROQ_AVAILABLE:
        print("❌ GROQ DEBUG: Groq package not available")
        logger.warning("Groq package not installed. Install with: pip install groq")
        return False
    
    groq_api_key = os.environ.get('GROQ_API_KEY')
    print(f"🔍 GROQ DEBUG: API key found = {bool(groq_api_key)}")
    
    if not groq_api_key:
        print("❌ GROQ DEBUG: No API key found in environment")
        logger.warning("GROQ_API_KEY not found in environment variables")
        return False
    
    if len(groq_api_key) < 10:  # Basic sanity check
        print(f"❌ GROQ DEBUG: API key too short ({len(groq_api_key)} characters)")
        logger.warning("GROQ_API_KEY appears to be invalid (too short)")
        return False
    
    print(f"🔍 GROQ DEBUG: API key length = {len(groq_api_key)} characters")
    
    try:
        print("🔍 GROQ DEBUG: Creating Groq client...")
        groq_client = Groq(api_key=groq_api_key)
        print("🔍 GROQ DEBUG: Creating instructor client...")
        groq_instructor_client = instructor.from_groq(groq_client, mode=instructor.Mode.JSON)
        print("✅ GROQ DEBUG: Groq instructor client initialized successfully")
        logger.info("✅ Groq instructor client initialized successfully")
        return True
    except Exception as e:
        print(f"❌ GROQ DEBUG: Failed to initialize Groq instructor client: {e}")
        logger.error(f"Failed to initialize Groq instructor client: {e}")
        import traceback
        traceback.print_exc()
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
    
    try:
        print(f"🤖 GROQ DEBUG: Using Groq instructor for model: {kwargs['model']}")
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
        
    except Exception as e:
        print(f"❌ GROQ DEBUG: Groq instructor completion failed: {e}")
        logger.error(f"Groq instructor completion failed: {e}")
        import traceback
        traceback.print_exc()
        raise e

def patch_botex_for_groq():
    """
    Monkey-patch botex completion function to handle Groq models with instructor
    """
    print(f"🔍 GROQ DEBUG: Starting to patch botex...")
    
    try:
        import botex.completion
        print(f"🔍 GROQ DEBUG: botex.completion imported successfully")
        
        # Store the original completion function
        original_completion = botex.completion.completion
        original_model_supports_schema = botex.completion.model_supports_response_schema
        
        print(f"🔍 GROQ DEBUG: Original functions stored")
        
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
            result = original_model_supports_schema(model, custom_llm_provider)
            print(f"🔍 GROQ DEBUG: Non-Groq model {model} schema support = {result}")
            return result
        
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
        
        # Apply the patches
        botex.completion.model_supports_response_schema = patched_model_supports_response_schema
        botex.completion.completion = patched_completion
        
        print("✅ GROQ DEBUG: Successfully patched botex functions")
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