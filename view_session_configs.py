#!/usr/bin/env python
import os
import sys
import json
from pprint import pprint

# Add current directory to Python path
sys.path.insert(0, os.getcwd())

try:
    import settings
    
    print("=== SESSION CONFIGS ===\n")
    
    for i, config in enumerate(settings.SESSION_CONFIGS):
        print(f"Config #{i+1}: {config['name']}")
        print("-" * 40)
        
        # Pretty print the config
        pprint(config)
        
        # Check for problematic fields
        print("\nChecking for serialization issues...")
        try:
            json.dumps(config)
            print("✓ No JSON serialization issues")
        except Exception as e:
            print(f"✗ JSON serialization error: {e}")
            
            # Find problematic fields
            for key, value in config.items():
                try:
                    json.dumps({key: value})
                except Exception as field_error:
                    print(f"  Problem field: {key} = {value}")
                    print(f"  Type: {type(value).__name__}")
                    print(f"  Error: {field_error}")
        
        print("\n" + "=" * 50 + "\n")
    
    # Also check session config defaults
    if hasattr(settings, 'SESSION_CONFIG_DEFAULTS'):
        print("=== SESSION CONFIG DEFAULTS ===")
        pprint(settings.SESSION_CONFIG_DEFAULTS)
        
        # Check for serialization issues in defaults
        try:
            json.dumps(settings.SESSION_CONFIG_DEFAULTS)
            print("\n✓ No JSON serialization issues in defaults")
        except Exception as e:
            print(f"\n✗ JSON serialization error in defaults: {e}")
            
            for key, value in settings.SESSION_CONFIG_DEFAULTS.items():
                try:
                    json.dumps({key: value})
                except Exception as field_error:
                    print(f"  Problem field: {key} = {value}")
                    print(f"  Type: {type(value).__name__}")
                    print(f"  Error: {field_error}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()