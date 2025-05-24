import json

def filter_botex_compatible_models(model_data):
    """Filter models that are compatible with botex"""
    compatible_models = {}
    
    for model_name, model_info in model_data.items():
        # Check botex requirements
        supports_schema = model_info.get("supports_response_schema", False)
        is_chat_mode = model_info.get("mode") == "chat"
        
        if supports_schema and is_chat_mode:
            compatible_models[model_name] = model_info
    
    return compatible_models

# Usage
with open('model_prices_and_context_window.json', 'r') as f:
    all_models = json.load(f)

botex_compatible = filter_botex_compatible_models(all_models)

print(f"Found {len(botex_compatible)} botex-compatible models out of {len(all_models)} total models")

# Optionally save the filtered results
with open('botex_compatible_models.json', 'w') as f:
    json.dump(botex_compatible, f, indent=2)