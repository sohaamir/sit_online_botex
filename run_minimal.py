# save as run_minimal.py
import botex
import os
import sys
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# LLaMA.cpp server URL
LLAMACPP_SERVER_URL = "http://localhost:8080"
OTREE_SERVER_URL = "http://localhost:8000" 

def run_experiment():
    """Run a social influence task experiment using existing servers"""
    
    print(f"Using existing llama.cpp server at {LLAMACPP_SERVER_URL}")
    print(f"Using existing oTree server at {OTREE_SERVER_URL}")
    
    # Define output paths
    output_dir = "botex_data_minimal"
    os.makedirs(output_dir, exist_ok=True)
    botex_db = os.path.join(output_dir, "experiment.sqlite3")
    
    try:
        # Verify both servers are running
        if not botex.otree_server_is_running(server_url=OTREE_SERVER_URL):
            print("oTree server is not running! Start it first with: otree devserver")
            return False
            
        # Get session configs
        configs = botex.get_session_configs(otree_server_url=OTREE_SERVER_URL)
        print(f"Available configs: {[c['name'] for c in configs]}")
        
        # Initialize session
        print("\nInitializing session with 2 participants (1 human, 1 bot)...")
        session = botex.init_otree_session(
            config_name="social_influence_task",
            npart=2,
            botex_db=botex_db,
            otree_server_url=OTREE_SERVER_URL
        )
        
        print(f"Session initialized with ID: {session['session_id']}")
        print(f"Bot URLs: {session['bot_urls']}")
        print(f"Human URLs: {session['human_urls']}")
        print(f"\nMonitor URL: {OTREE_SERVER_URL}/SessionMonitor/{session['session_id']}")
        
        # Run bot
        if session['bot_urls']:
            print("\nRunning bot...")
            botex.run_single_bot(
                url=session['bot_urls'][0],
                session_name=session['session_id'],
                session_id=session['session_id'],
                participant_id=session['participant_code'][0],
                botex_db=botex_db,
                model="llamacpp",
                api_base=LLAMACPP_SERVER_URL,
                throttle=True  # Prevent rate limiting
            )
            
            # Export results
            responses_csv = os.path.join(output_dir, f"responses_{session['session_id']}.csv")
            print(f"\nExporting response data to {responses_csv}")
            botex.export_response_data(
                responses_csv,
                botex_db=botex_db,
                session_id=session['session_id']
            )
            
            print("\nExperiment complete!")
            print(f"You can view the results at: {responses_csv}")
            print(f"If you want to play as a human, open: {session['human_urls'][0]}")
            return True
        else:
            print("No bot URLs found in session!")
            return False
            
    except Exception as e:
        print(f"Error running experiment: {str(e)}")
        return False

if __name__ == "__main__":
    run_experiment()