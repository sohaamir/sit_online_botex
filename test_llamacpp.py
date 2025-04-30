# save as test_llamacpp.py
try:
    import llama_cpp
    print(f"llama_cpp version: {llama_cpp.__version__}")
    print("llama_cpp is correctly installed")
except ImportError:
    print("Error: llama_cpp is not installed correctly")
    print("Try reinstalling with: pip install llama-cpp-python")