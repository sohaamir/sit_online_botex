# This script runs the social influence task experiment using the botex package.

from os import environ, makedirs, path
from dotenv import load_dotenv
import subprocess
import datetime
import sqlite3
import logging
import shutil
import botex
import json
import csv
import sys
import os
import re

# Set up base output directory
base_output_dir = "botex_data"
makedirs(base_output_dir, exist_ok=True)

# Custom log filter to exclude HTTP request and throttling error logs
class LogFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        # Filter out HTTP request logs and throttling errors
        if "HTTP Request:" in message or "Throttling: Request error:" in message:
            return False
        return True

# Set up logging to show detailed bot interactions, but filter out HTTP requests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Apply filter to all existing handlers
logger = logging.getLogger()
for handler in logger.handlers:
    handler.addFilter(LogFilter())

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

# Custom function to export response data with specific ordering
def export_ordered_response_data(csv_file, botex_db, session_id):
    """Export botex response data with comprehension questions at the top"""
    try:
        # Use botex's built-in function to get the raw responses
        responses = botex.read_responses_from_botex_db(botex_db=botex_db, session_id=session_id)
        
        if not responses:
            logger.warning(f"No responses found for session {session_id}")
            with open(csv_file, 'w', newline='') as f:
                f.write("session_id,participant_id,round,question_id,answer,reason\n")
                f.write(f"# No responses found for session {session_id}\n")
            return
            
        logger.info(f"Found {len(responses)} responses for session {session_id}")
        
        # Separate comprehension questions from other responses
        comprehension_responses = []
        task_responses = []
        
        for response in responses:
            question_id = response.get('question_id', '')
            # Identify comprehension questions
            if ('comprehension' in question_id.lower() or 
                question_id.lower().startswith('q') or
                re.search(r'q[1-4]$', question_id.lower())):
                comprehension_responses.append(response)
            else:
                task_responses.append(response)
        
        # Sort comprehension questions numerically if possible
        def get_question_number(response):
            match = re.search(r'q(\d+)', response.get('question_id', '').lower())
            if match:
                return int(match.group(1))
            return 999
        
        comprehension_responses.sort(key=get_question_number)
        
        # Define the desired order of task questions
        order_map = {
            'id_choice1': 1,
            'id_bet1': 2,
            'id_choice2': 3,
            'id_bet2': 4,
        }
        
        # Sort task responses by round and question_id order
        task_responses.sort(key=lambda x: (int(x['round']), order_map.get(x['question_id'], 999)))
        
        # Combine with comprehension questions at the top
        ordered_responses = comprehension_responses + task_responses
        
        # Write to CSV with the correct order
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['session_id', 'participant_id', 'round', 'question_id', 'answer', 'reason'])
            writer.writeheader()
            writer.writerows(ordered_responses)
            logger.info(f"Successfully wrote {len(ordered_responses)} responses to {csv_file}")
            logger.info(f"Placed {len(comprehension_responses)} comprehension questions at the top")
            
    except Exception as e:
        logger.error(f"Error in export_ordered_response_data: {str(e)}", exc_info=True)
        
        # Fallback to standard export
        try:
            logger.info(f"Trying standard botex export function...")
            botex.export_response_data(
                csv_file,
                botex_db=botex_db,
                session_id=session_id
            )
            logger.info(f"Standard export successful")
        except Exception as e2:
            logger.warning(f"Standard export also failed: {str(e2)}")
            with open(csv_file, 'w', newline='') as f:
                f.write("session_id,participant_id,round,question_id,answer,reason\n")
                f.write(f"# Error exporting responses: {str(e)}\n")

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
        
        # Create timestamp for this session
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create a temporary database for the session initialization
        temp_db = os.path.join(base_output_dir, f"temp_botex_{timestamp}.sqlite3")
        
        # Initialize a session
        logger.info(f"Session {session_number}: Initializing social influence task session...")
        session = botex.init_otree_session(
            config_name='social_influence_task',  # Your task's config name
            npart=5,  # Social influence task needs 5 participants
            nhumans=1,  # Only 1 bot will be controlled by LLM
            otree_server_url="http://localhost:8000",
            botex_db=temp_db  # Use temporary database for initialization
        )
        
        session_id = session['session_id']
        logger.info(f"Session {session_number}: Initialized with ID: {session_id}")
        
        # Create session-specific output directory
        output_dir = os.path.join(base_output_dir, f"session_{session_id}")
        makedirs(output_dir, exist_ok=True)
        
        # Create session-specific database
        botex_db = path.join(output_dir, f"botex_{session_id}.sqlite3")
        
        # Copy the temporary database to the session database
        if os.path.exists(temp_db):
            shutil.copy2(temp_db, botex_db)
            os.remove(temp_db)  # Remove the temporary database
            logger.info(f"Session {session_number}: Created session database: {botex_db}")
        
        # Set up the log file in the session-specific directory
        log_file = path.join(output_dir, f"experiment_log_{timestamp}.txt")
        
        # Add file handler to logger with filter
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        file_handler.addFilter(LogFilter())
        logger.addHandler(file_handler)
        
        # Create a separate filtered log file just for bot actions
        bot_actions_log = path.join(output_dir, f"bot_actions_{timestamp}.txt")
        bot_actions_handler = logging.FileHandler(bot_actions_log)
        bot_actions_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        bot_actions_handler.addFilter(LogFilter())
        logger.addHandler(bot_actions_handler)
        
        # Dictionary to collect bot actions for JSON
        bot_actions = []
        
        # Add a handler to capture actions for JSON
        class JsonCaptureHandler(logging.Handler):
            def emit(self, record):
                message = self.format(record)
                if "Bot's analysis of page" in message or "Bot has answered question" in message:
                    bot_actions.append(message)
        
        json_handler = JsonCaptureHandler()
        json_handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(json_handler)
        
        logger.info(f"Session {session_number}: Output directory: {output_dir}")
        logger.info(f"Session {session_number}: Log file: {log_file}")
        logger.info(f"Session {session_number}: Bot actions log: {bot_actions_log}")
        logger.info(f"Session {session_number}: Database: {botex_db}")
        
        # Define output filenames
        botex_responses_csv = path.join(output_dir, f"botex_{session_id}_responses.csv")
        botex_participants_csv = path.join(output_dir, f"botex_{session_id}_participants.csv")
        otree_wide_csv = path.join(output_dir, f"otree_{session_id}_wide.csv")
        
        # Run the bot on the session
        monitor_url = f"http://localhost:8000/SessionMonitor/{session_id}"
        logger.info(f"Session {session_number}: Starting bot. You can monitor progress at {monitor_url}")
        print(f"\nSession {session_number}: Starting bot. You can monitor progress at {monitor_url}")
        
        # Now we only run a single bot instead of all bots
        if session['bot_urls']:
            # There should be one bot URL in the list
            logger.info(f"Session {session_number}: Running single bot")
            botex.run_single_bot(
                url=session['bot_urls'][0],
                session_name=session_id,  # Set session name explicitly
                session_id=session_id,    # Set session id explicitly  
                participant_id=session['participant_code'][0],  # Set the participant code explicitly
                botex_db=botex_db,        # Use session-specific database
                model=LLM_MODEL,
                api_key=LLM_API_KEY,
                throttle=True,  # Enable throttling to avoid rate limits
                # Add increased delays to avoid rate limits
                **{"initial_delay": 2.0, "backoff_factor": 2.0}
            )
        else:
            logger.warning(f"Session {session_number}: No bot URLs found")
        
        # Save bot actions to JSON
        bot_actions_json = path.join(output_dir, f"bot_actions_{timestamp}.json")
        with open(bot_actions_json, 'w') as f:
            json.dump(bot_actions, f, indent=2)
        logger.info(f"Session {session_number}: Bot actions saved to JSON: {bot_actions_json}")
        
        # Export botex participant data - only for this session
        logger.info(f"Session {session_number}: Exporting botex participant data...")
        try:
            botex.export_participant_data(
                botex_participants_csv,
                botex_db=botex_db,
                session_id=session_id  # Filter by session ID
            )
            logger.info(f"Session {session_number}: Participant data successfully exported")
        except Exception as e:
            logger.warning(f"Session {session_number}: Could not export participant data: {str(e)}")
        
        # Export botex response data with our custom ordered function
        logger.info(f"Session {session_number}: Exporting botex response data with custom ordering...")
        try:
            export_ordered_response_data(
                botex_responses_csv,
                botex_db=botex_db,
                session_id=session_id
            )
            logger.info(f"Session {session_number}: Bot responses successfully exported with custom ordering")
        except Exception as e:
            logger.warning(f"Session {session_number}: Error exporting ordered responses: {str(e)}")
            
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
            f.write(f"Number of participants: 5 (1 LLM bot, 4 automated)\n\n")
            f.write("Files generated:\n")
            f.write(f"- Log file: {path.basename(log_file)}\n")
            f.write(f"- Bot actions log: {path.basename(bot_actions_log)}\n")
            f.write(f"- Bot actions JSON: {path.basename(bot_actions_json)}\n")
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
            f.write("- One LLM bot made decisions, while 4 other players had pre-determined choices\n")
            f.write("- Participants could see others' choices and adjust their decisions\n")
            f.write("- Options had different reward probabilities\n")
        
        logger.info(f"Session {session_number}: Experiment complete. All outputs saved to {output_dir} folder")
        
        # Remove file handlers for this session
        logger.removeHandler(file_handler)
        logger.removeHandler(bot_actions_handler)
        logger.removeHandler(json_handler)
        file_handler.close()
        bot_actions_handler.close()
        
        return True

    except Exception as e:
        logger.error(f"Session {session_number}: Error running experiment: {str(e)}", exc_info=True)
        print(f"\nSession {session_number}: Error running experiment: {str(e)}")
        return False

    finally:
        # Clean up temporary database if it exists
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

print(f"\nRunning {NUM_SESSIONS} session(s). Results will be stored in the '{base_output_dir}' directory.")
for i in range(1, NUM_SESSIONS + 1):
    run_session(i)