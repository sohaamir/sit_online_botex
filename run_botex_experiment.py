# This script runs the social influence task experiment using the botex package.

from dotenv import load_dotenv
from os import environ, makedirs, path
import logging
import botex
import os
import datetime
import sys
import shutil
import subprocess
import glob
import pandas as pd
import numpy as np
import random
import json
import time
import tqdm

# Set up base output directory
base_output_dir = "botex_data"
makedirs(base_output_dir, exist_ok=True)

# Set up logging to console initially
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Load environment variables from .env file
if os.path.exists('.env'):
    load_dotenv()
    os.environ['OTREE_REST_KEY'] = environ.get('OTREE_REST_KEY', '')
    logger.info("Loaded environment variables from .env file")

# Number of sessions to run
NUM_SESSIONS = 1  # Change this to run more or fewer sessions

# LLM model vars - using Gemini by default
LLM_MODEL = environ.get('LLM_MODEL', "gemini/gemini-1.5-flash")
LLM_API_KEY = environ.get('OTREE_GEMINI_API_KEY')

# Verify API key exists
if not LLM_API_KEY:
    logger.error("OTREE_GEMINI_API_KEY not found in environment variables")
    print("\nError: OTREE_GEMINI_API_KEY not found in environment variables")
    print("Make sure to set this in your .env file")
    sys.exit(1)

# Function to run a single session
def run_session(session_number):
    otree_process = None
    try:
        # Reset oTree database
        logger.info(f"Session {session_number}: Resetting oTree database...")
        try:
            subprocess.run(["otree", "resetdb", "--noinput"], check=True)
            logger.info(f"Session {session_number}: oTree database reset successful")
        except subprocess.CalledProcessError as e:
            logger.error(f"Session {session_number}: Failed to reset oTree database: {e}")
            print(f"Failed to reset oTree database: {e}")
            return False
        
        # Start oTree server
        logger.info(f"Session {session_number}: Starting oTree server...")
        otree_process = botex.start_otree_server(project_path=".")
        
        # Get the available session configurations
        logger.info(f"Session {session_number}: Getting session configurations...")
        session_configs = botex.get_session_configs(
            otree_server_url="http://localhost:8000"
        )
        
        # Set up temporary database for session initialization
        temp_db = os.path.join(base_output_dir, "temp_botex.sqlite3")
        if os.path.exists(temp_db):
            os.remove(temp_db)
        
        # Initialize a session with the temporary database
        logger.info(f"Session {session_number}: Initializing social influence task session...")
        session = botex.init_otree_session(
            config_name='social_influence_task_botex',  # Your task's config name
            npart=1,  # Social influence task needs 1 participant
            otree_server_url="http://localhost:8000",
            botex_db=temp_db
        )
        
        session_id = session['session_id']
        logger.info(f"Session {session_number}: Initialized with ID: {session_id}")
        
        # Create session-specific output directory
        output_dir = os.path.join(base_output_dir, f"session_{session_id}")
        makedirs(output_dir, exist_ok=True)
        
        # Set up the log file in the session-specific directory
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = path.join(output_dir, f"experiment_log_{timestamp}.txt")
        
        # Add file handler to logger
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        
        logger.info(f"Session {session_number}: Output directory: {output_dir}")
        logger.info(f"Session {session_number}: Log file: {log_file}")
        
        # Create final database in the session directory
        botex_db = path.join(output_dir, f"botex_{session_id}.sqlite3")
        
        # Copy the temporary database to the session directory
        if os.path.exists(temp_db):
            shutil.copy2(temp_db, botex_db)
            logger.info(f"Session {session_number}: Copied database to: {botex_db}")
        
        # Define output filenames
        botex_responses_csv = path.join(output_dir, f"botex_{session_id}_responses.csv")
        botex_participants_csv = path.join(output_dir, f"botex_{session_id}_participants.csv")
        otree_wide_csv = path.join(output_dir, f"otree_{session_id}_wide.csv")
        
        # Run the bots on the session
        monitor_url = f"http://localhost:8000/SessionMonitor/{session_id}"
        logger.info(f"Session {session_number}: Starting bots. You can monitor their progress at {monitor_url}")
        print(f"\nSession {session_number}: Starting bots. You can monitor progress at {monitor_url}")
        
        # Run bots on the session with throttling
        botex.run_bots_on_session(
            session_id=session_id,
            botex_db=botex_db,
            model=LLM_MODEL,
            api_key=LLM_API_KEY,
            throttle=True  # Use throttling to avoid rate limits
        )
        
        # Export botex participant data
        logger.info(f"Session {session_number}: Exporting botex participant data...")
        try:
            botex.export_participant_data(
                botex_participants_csv,
                botex_db=botex_db,
                session_id=session_id
            )
            logger.info(f"Session {session_number}: Participant data successfully exported")
        except Exception as e:
            logger.warning(f"Session {session_number}: Could not export participant data: {str(e)}")
        
        # Export botex response data
        logger.info(f"Session {session_number}: Exporting botex response data...")
        try:
            botex.export_response_data(
                botex_responses_csv,
                botex_db=botex_db,
                session_id=session_id
            )
            logger.info(f"Session {session_number}: Bot responses successfully exported")
        except Exception as e:
            logger.warning(f"Session {session_number}: No bot responses could be exported: {str(e)}")
            
            # Creating an empty response file with header
            with open(botex_responses_csv, 'w') as f:
                f.write("session_id,participant_id,round,question_id,answer,reason\n")
                f.write(f"# No responses recorded for session {session_id}\n")
        
        # Export oTree data
        logger.info(f"Session {session_number}: Exporting oTree data...")
        try:
            botex.export_otree_data(
                otree_wide_csv,
                server_url="http://localhost:8000",
                admin_name='admin',
                admin_password=environ.get('OTREE_ADMIN_PASSWORD', 'admin')
            )
            
            # Normalize and export to CSV
            logger.info(f"Session {session_number}: Normalizing oTree data...")
            normalized_data = botex.normalize_otree_data(
                otree_wide_csv, 
                store_as_csv=True,
                data_exp_path=output_dir,
                exp_prefix=f"otree_{session_id}"
            )
        except Exception as e:
            logger.error(f"Session {session_number}: Failed to export oTree data: {str(e)}")
        
        # Create a summary file
        summary_file = path.join(output_dir, f"experiment_summary_{session_id}.txt")
        with open(summary_file, 'w') as f:
            f.write(f"Social Influence Task Experiment Summary - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*70 + "\n\n")
            f.write(f"Session ID: {session_id}\n")
            f.write(f"Session Number: {session_number} of {NUM_SESSIONS}\n")
            f.write(f"Model used: {LLM_MODEL}\n")
            f.write(f"Number of participants: 5\n\n")
            f.write("Files generated:\n")
            f.write(f"- Log file: {path.basename(log_file)}\n")
            f.write(f"- Bot participants: {path.basename(botex_participants_csv)}\n")
            f.write(f"- Bot responses: {path.basename(botex_responses_csv)}\n")
            f.write(f"- oTree wide data: {path.basename(otree_wide_csv)}\n")
            
            # List normalized oTree data files
            normalized_files = [f for f in os.listdir(output_dir) if f.startswith(f"otree_{session_id}_") and f.endswith(".csv")]
            if normalized_files:
                f.write("\nNormalized oTree data:\n")
                for file in normalized_files:
                    f.write(f"- {file}\n")
            
            # Add specific information about the social influence task
            f.write("\nSocial Influence Task Details:\n")
            f.write("- Each participant made choices between options A and B over 5 rounds\n")
            f.write("- Participants could see others' choices and adjust their decisions\n")
            f.write("- Options had 75%/25% reward probabilities\n")
            
            # Analyze successful completion
            try:
                completed_players = 0
                player_files = [f for f in normalized_files if "player" in f]
                if player_files and os.path.exists(os.path.join(output_dir, player_files[0])):
                    
                    df = pd.read_csv(os.path.join(output_dir, player_files[0]))
                    if not df.empty:
                        completed_rounds = df['round'].max()
                        completed_players = df['participant_code'].nunique()
                        f.write(f"\nCompletion stats:\n")
                        f.write(f"- Completed players: {completed_players}/5\n")
                        f.write(f"- Completed rounds: {completed_rounds}/5\n")
            except Exception as e:
                f.write(f"\nFailed to analyze completion stats: {str(e)}\n")
        
        logger.info(f"Session {session_number}: Experiment complete. All outputs saved to {output_dir} folder")
        
        # Remove file handler for this session
        logger.removeHandler(file_handler)
        file_handler.close()
        
        return True

    except Exception as e:
        logger.error(f"Session {session_number}: Error running experiment: {str(e)}", exc_info=True)
        print(f"\nSession {session_number}: Error running experiment: {str(e)}")
        return False

    finally:
        # Clean up temporary database
        if 'temp_db' in locals() and os.path.exists(temp_db):
            try:
                os.remove(temp_db)
            except:
                pass
        
        # Stop the oTree server
        if otree_process:
            try:
                logger.info(f"Session {session_number}: Stopping oTree server...")
                botex.stop_otree_server(otree_process)
                logger.info(f"Session {session_number}: oTree server stopped")
            except Exception as e:
                logger.error(f"Session {session_number}: Error stopping oTree server: {str(e)}")

print(f"\nAll {NUM_SESSIONS} sessions completed. Results are stored in the '{base_output_dir}' directory.")