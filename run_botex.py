# Complete workflow
import botex
import logging

from run_botex_experiment import get_behaviour_prompts
logging.basicConfig(level=logging.INFO)

# Start oTree server
otree_process = botex.start_otree_server(project_path=".")

# Start llama.cpp server
llamacpp_config = {
    "server_path": "./llama_server",
    "local_llm_path": "models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
}
llama_process = botex.start_llamacpp_server(llamacpp_config)

# Initialize session
session = botex.init_otree_session(
    config_name="social_influence_task",
    npart=5,
    nhumans=0,  # All bots
    botex_db="botex.sqlite3"
)

# Run bots
botex.run_bots_on_session(
    session_id=session['session_id'],
    model="llamacpp",
    api_base="http://localhost:8080",
    botex_db="botex.sqlite3",
    user_prompts=get_behaviour_prompts()  # Your custom prompts
)

# Cleanup
botex.stop_llamacpp_server(llama_process)
botex.stop_otree_server(otree_process)