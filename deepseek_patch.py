#!/usr/bin/env python3
"""
deepseek_baml_patch.py - DeepSeek integration using BAML for structured parsing
"""

import logging
import os
import json
import re
from dotenv import load_dotenv

logger = logging.getLogger("botex")

# Load environment variables
load_dotenv("botex.env")

# Check if BAML is available
try:
    from baml_py import BamlRuntime
    BAML_AVAILABLE = True
    logger.info("✅ BAML package available for DeepSeek integration")
except ImportError as e:
    logger.warning(f"BAML package not available: {e}")
    BAML_AVAILABLE = False

# Global BAML runtime instance
baml_runtime = None

def initialize_baml_runtime():
    """Initialize BAML runtime for structured parsing"""
    global baml_runtime
    
    if not BAML_AVAILABLE:
        return None
    
    try:
        # Initialize BAML runtime with required env_vars parameter
        env_vars = {
            'DEEPSEEK_API_KEY': os.environ.get('DEEPSEEK_API_KEY', ''),
        }
        
        baml_runtime = BamlRuntime.from_directory("baml_src", env_vars=env_vars)
        logger.info("✅ BAML runtime initialized successfully")
        return baml_runtime
    except Exception as e:
        logger.error(f"Failed to initialize BAML runtime: {e}")
        return None

def deepseek_completion_with_baml(**kwargs):
    """
    Custom completion function for DeepSeek using BAML
    """
    logger.info("🚀 DEEPSEEK: Using BAML completion")
    
    response_format = kwargs.pop("response_format")
    model = kwargs.get("model", "")
    
    # Remove deepseek/ prefix for API call
    if model.startswith("deepseek/"):
        kwargs["model"] = model[8:]
    
    # Remove botex-specific parameters
    kwargs.pop("throttle", None)
    deepseek_api_key = kwargs.pop("api_key", None) or os.environ.get('DEEPSEEK_API_KEY')
    
    try:
        # Step 1: Get raw response from DeepSeek
        import litellm
        
        if deepseek_api_key:
            kwargs["api_key"] = deepseek_api_key
        
        # Get raw response
        raw_response = litellm.completion(**kwargs)
        raw_content = raw_response.choices[0].message.content.strip()
        
        logger.info(f"📝 DeepSeek raw response: {raw_content[:200]}...")
        
        # Step 2: Try direct JSON parsing first (fastest)
        try:
            json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed_json = json.loads(json_str)
                response_format.model_validate(parsed_json)
                
                logger.info("✅ Direct JSON parsing successful")
                return {
                    'resp_str': json_str,
                    'finish_reason': 'stop'
                }
        except Exception as e:
            logger.info(f"Direct parsing failed: {e}")
        
        # Step 3: Use BAML for intelligent parsing
        if baml_runtime:
            try:
                schema_dict = response_format.model_json_schema()
                schema_str = json.dumps(schema_dict, indent=2)
                
                # Use BAML to parse
                result = baml_runtime.ParseBotexResponse(
                    raw_response=raw_content,
                    expected_schema=schema_str
                )
                
                # Convert to JSON
                if hasattr(result, 'model_dump_json'):
                    parsed_json_str = result.model_dump_json()
                else:
                    parsed_json_str = json.dumps(result.__dict__)
                
                # Validate
                parsed_dict = json.loads(parsed_json_str)
                response_format.model_validate(parsed_dict)
                
                logger.info("✅ BAML parsing successful")
                return {
                    'resp_str': parsed_json_str,
                    'finish_reason': 'stop'
                }
                
            except Exception as e:
                logger.warning(f"BAML parsing failed: {e}")
        
        # Step 4: Fallback parsing
        logger.warning("Using fallback parsing")
        basic_response = {
            "answers": {},
            "summary": f"Failed to parse: {raw_content[:100]}...",
            "confused": True
        }
        
        return {
            'resp_str': json.dumps(basic_response),
            'finish_reason': 'stop'
        }
        
    except Exception as e:
        logger.error(f"DeepSeek completion failed: {e}")
        raise e

def patch_botex_completion():
    """
    Patch the botex completion system to intercept DeepSeek models
    """
    try:
        # Import and patch the completion module
        import botex.completion as completion_module
        
        # Store original functions
        original_completion = completion_module.completion
        original_model_supports = completion_module.model_supports_response_schema
        
        def patched_model_supports_response_schema(model: str, custom_llm_provider: str = None) -> bool:
            """Ensure DeepSeek models are handled by our custom function"""
            
            # Force DeepSeek models to return False (use fallback/instructor path)
            if model and "/" in model and model.split("/")[0].lower() == "deepseek":
                logger.info(f"🔧 DEEPSEEK PATCH: {model} → forced fallback")
                return False
            
            if custom_llm_provider and custom_llm_provider.lower() == "deepseek":
                logger.info(f"🔧 DEEPSEEK PATCH: {model} (provider: deepseek) → forced fallback")
                return False
            
            # Use original for other models
            return original_model_supports(model, custom_llm_provider)
        
        def patched_completion(**kwargs):
            """Intercept completion calls for DeepSeek models"""
            model = kwargs.get("model", "")
            
            # Check if this is a DeepSeek model and intercept EARLY
            if model and "/" in model and model.split("/")[0].lower() == "deepseek":
                logger.info(f"🔧 DEEPSEEK PATCH: Intercepting {model} for BAML processing")
                return deepseek_completion_with_baml(**kwargs)
            
            # For all other models, use the original completion function
            return original_completion(**kwargs)
        
        # Apply the patches
        completion_module.model_supports_response_schema = patched_model_supports_response_schema
        completion_module.completion = patched_completion
        
        logger.info("✅ DEEPSEEK PATCH: Successfully patched botex completion")
        return True
        
    except Exception as e:
        logger.error(f"❌ DEEPSEEK PATCH: Failed to patch: {e}")
        import traceback
        traceback.print_exc()
        return False

def apply_deepseek_patch():
    """Main function to apply the DeepSeek + BAML patch"""
    global baml_runtime
    
    logger.info("🔧 DEEPSEEK PATCH: Starting application...")
    
    # Initialize BAML if available
    if BAML_AVAILABLE:
        baml_runtime = initialize_baml_runtime()
        if baml_runtime:
            logger.info("✅ BAML runtime ready")
        else:
            logger.warning("⚠️ BAML initialization failed, using fallback")
    else:
        logger.warning("⚠️ BAML not available, using fallback only")
    
    # Apply the completion patches (CRITICAL)
    success = patch_botex_completion()
    
    if success:
        logger.info("✅ DEEPSEEK PATCH: Integration ready!")
        logger.info(f"   • BAML parsing: {'enabled' if baml_runtime else 'disabled'}")
        logger.info("   • Completion interception: enabled")
        logger.info("   • Fallback parsing: enabled")
    else:
        logger.error("❌ DEEPSEEK PATCH: Integration failed!")
    
    return success

# Auto-apply when imported
if __name__ != "__main__":
    print("🔧 DEEPSEEK: Applying patch...")
    success = apply_deepseek_patch()
    if success:
        print("✅ DEEPSEEK: Patch applied successfully!")
    else:
        print("❌ DEEPSEEK: Patch failed!")