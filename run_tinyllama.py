# run_tinyllama.py
#!/usr/bin/env python

# Import patches first
import tinyllama_fix

# Then import everything else
from run_experiment import main

if __name__ == "__main__":
    print("Running experiment with TinyLLaMA-optimized settings")
    # Hardcoded minimal settings for TinyLLaMA
    main(
        experiment_name='social_influence_task',
        num_sessions=1,
        llm_model='llamacpp',
        api_key=None,
        api_base='http://localhost:8080',
        output_dir='botex_data/tinyllama',
        strategy_type='standard'
    )