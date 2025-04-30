# save as test_model_loading.py
from llama_cpp import Llama
import time

model_path = "models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
print(f"Trying to load model: {model_path}")

try:
    print("Loading model (this may take a minute)...")
    # Try to load the model directly (not as a server)
    model = Llama(
        model_path=model_path,
        n_ctx=512,  # Smaller context for testing
        verbose=True  # Show detailed loading info
    )
    print("Model loaded successfully!")
    
    # Test a simple completion
    prompt = "Hello, my name is"
    print(f"Testing completion with prompt: '{prompt}'")
    
    output = model.create_completion(
        prompt,
        max_tokens=10,
        temperature=0.7,
        echo=True
    )
    print("Model output:")
    print(output)
    
except Exception as e:
    print(f"Error loading model: {e}")