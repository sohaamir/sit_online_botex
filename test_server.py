# save as test_server.py
import requests
import time
from run_llamacpp_server import run_server, stop_server

# Path to your model
model_path = "models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"

print(f"Starting server with model: {model_path}")
server_process = run_server(model_path)

if server_process:
    print("Server started successfully!")
    
    # Test if server is responding
    try:
        response = requests.get("http://localhost:8080/v1/models")
        if response.status_code == 200:
            print("Server API is accessible!")
            print(f"Available models: {response.json()}")
            
            # Test a simple completion
            data = {
                "model": "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say hello"}
                ],
                "temperature": 0.7,
                "max_tokens": 50
            }
            
            completion = requests.post(
                "http://localhost:8080/v1/chat/completions", 
                json=data
            )
            
            if completion.status_code == 200:
                response_text = completion.json()["choices"][0]["message"]["content"]
                print(f"Model response: {response_text}")
                print("Basic inference test PASSED!")
            else:
                print(f"Inference failed: {completion.status_code}")
                print(completion.text)
        else:
            print(f"Server returned status code {response.status_code}")
    except Exception as e:
        print(f"Error connecting to server: {e}")
    
    # Keep server running for 5 seconds
    print("Server will stop in 5 seconds...")
    time.sleep(5)
    
    # Stop the server
    stop_server(server_process)
    print("Server stopped")
else:
    print("Failed to start server")