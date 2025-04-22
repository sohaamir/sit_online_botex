# This script runs the social influence task experiment using the botex package with concurrent sessions.

from concurrent.futures import ThreadPoolExecutor
from os import environ, makedirs, path
from dotenv import load_dotenv
import subprocess
import threading
import datetime
import sqlite3
import logging
import shutil
import botex
import json
import csv
import sys
import re
import os


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

# Number of sessions to run concurrently
NUM_SESSIONS = 1  # Change this to run more or fewer concurrent sessions

# LLM model vars - using Gemini by default
LLM_MODEL = environ.get('LLM_MODEL', "gemini/gemini-1.5-flash")
LLM_API_KEY = environ.get('OTREE_GEMINI_API_KEY')

# Verify API key exists
if not LLM_API_KEY:
    logger.error("OTREE_GEMINI_API_KEY not found in environment variables")
    print("\nError: OTREE_GEMINI_API_KEY not found in environment variables")
    print("Make sure to set this in your .env file")
    sys.exit(1)

# Thread-local storage for session-specific resources
thread_local = threading.local()

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

# Behaviour prompts for bots
def get_behaviour_prompts():
    """Returns the behavior prompts for the LLM bots"""
    return {
        "system": """You are participating in a social experiment where your goal is to maximize points by making choices and placing bets. 

        EXPERIMENT OVERVIEW:
        The experiment involves completing a probabilistic reversal learning task, where you will make a choice between two options. 
        As such, the reward contingencies will switch across blocks, but you will not know when or how often this will happen.
        Making it more difficult is that the reward contingencies are probabilistic, meaning that the higher reward option will not always give you a reward, but it will give you a higher reward on average.
        So, even if you select the higher reward option, you may not always get a reward, but it is still the best option to select OVERALL within a block. 
        And the other way around, if you select the lower reward option, you may get a reward, but it is the worse option to select OVERALL within a block.

        You will also make bets reflecting your confidence in your choice. The higher the bet, the more points you can win, but also the more points you can lose if you are wrong.

        You will be making these choices and bets in a group of 5 participants, including yourself. 
        You will be able to see the choices of other participants, which you can use to inform your own choices, both within a trial and across trials.
        However, you may also use your own experience to inform your choices and bets. 

        We are ultimately interested to see how participants flexibly integrate information from others and their own experience to make the best possible choice and bet.

        Here are some further instructions on how to behave when making your choices and bets:

        CHOICE STRATEGY: During the task itself, you should aim to make choices by dynamically integrating information regarding the choices of others within the group with your own experience.
        The extent to which you should do so is up to you, feel free to follow your judgement based on the information you have available.
        However, you should not adapt a fixed strategy (i.e., making the same choice repeatedly), but rather adapt your strategy to the current situation, by:
        - Understanding that the task is a probabilistic reversal learning task, where the reward contingencies switch across blocks
        - Within blocks, the higher reward option will not always give you a reward, but it will give you a higher reward on average
        - Understanding that other players are also learning the task at the same time as you, and that their choices may not be optimal
        - Being flexible with interpreting the choices of others and be willing to go against the majority if you think that you are right and they are wrong
        - Being willing to change your choice if you think that others are right and you are wrong
        - Ultimately, incorporating your own experience and the choices of others to make the best possible choice
        Remember that dynamically integrating information from others and your own experience is key to maximizing your points in this task.

        BETTING STRATEGY: During the task itself, you should adapt a dynamic betting strategy which changes bets according to the confidence level for each choice. 
        You should not adapt a fixed strategy (i.e., making the same bet repeatedly), but rather adapt your strategy to the current situation, by:
        - Being willing to take risks and make high bets (3) if you are confident that your choice is correct (high confidence)
        - Being willing to bet moderately (2) if you think your choice is correct but not completely sure (moderate confidence)
        - Being willing to play it safe and make low bets (1) if you are unsure that your choice is correct (low confidence)
        Remember that dynamically adapting your bets to reflect your confidence is key to maximizing your points in this task.
        This is often a better strategy for getting a higher points score - which is your goal for the experiment - than repeatedly selecting a conservative or moderate bet (i.e., repeatedly selecting 2).

        Further instructions on the task and how you will complete it be provided during the experiment itself.
        
        When interacting the the experiment, you should analyze each page carefully and respond with a valid JSON.""",
                    
        "analyze_page_q": """Perfect. This is your summary of the survey/experiment so far: \n\n {summary} \n\n You have now proceeded to the next page. This is the body text of the web page: \n\n {body} \n\n 

        I need you to do two things, but remember your adaptive choosing and betting strategy:

        First, this page contains {nr_q} question(s) and I need you to answer all questions in the variable 'answers'. You should be willing to:
        - Understand that other players are also learning the task and that their choices may not be optimal
        - Be flexible with interpreting the choices of others and be willing to go against the majority if you think that you are right and they are wrong
        - Being willing to change your choice if you think that others are right and you are wrong
        - Incorporate your own experience and the choices of others to make the best possible choice
        - Take risks and make high bets (3) if you are confident that your choice is correct
        - Bet moderately (2) if you think your choice is correct but not completely sure
        - Play it safe and make low bets (1) if you unsure about your choice

        Second, I need you to update the summary. The new summary should include a summary of the content of the page, the old summary given above, the questions asked and the answers you have given. 

        The following JSON string contains the questions: {questions_json} 

        For each identified question, you must provide two variables: 'reason' contains your reasoning or thought that leads you to a response or answer and 'answer' which contains your response.

        Taken together, a correct answer to a text with two questions would have the form {{""answers"": {{""ID of first question"": {{""reason"": ""Your reasoning for how you want to answer the first question"", ""answer"":""Your final answer to the first question""}}, ""ID of the second question"": {{""reason"": ""Your reasoning for how you want to answer the second question"", ""answer"": ""Your final answer to the second question""}}}},""summary"": ""Your summary"", ""confused"": ""set to `true` if you are confused by any part of the instructions, otherwise set it to `false`""}}"""
    }

# Function to run a single session with session-specific resources
def run_session(session_number, shared_otree_server=None):
    """Run a single session with a unique database and logs"""
    session_specific = {}
    try:
        # Create timestamp for this session
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = f"session_{session_number}_{timestamp}"
        
        # Create session-specific output directory
        output_dir = os.path.join(base_output_dir, f"session_{session_id}")
        makedirs(output_dir, exist_ok=True)
        
        # Create session-specific database
        botex_db = path.join(output_dir, f"botex_{session_id}.sqlite3")
        
        # Set up session-specific logging
        log_file = path.join(output_dir, f"experiment_log_{timestamp}.txt")
        bot_actions_log = path.join(output_dir, f"bot_actions_{timestamp}.txt")
        
        # Add file handlers to logger with filter
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        file_handler.addFilter(LogFilter())
        logger.addHandler(file_handler)
        
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
        
        session_specific['handlers'] = [file_handler, bot_actions_handler, json_handler]
        
        logger.info(f"Session {session_number}: Output directory: {output_dir}")
        logger.info(f"Session {session_number}: Log file: {log_file}")
        logger.info(f"Session {session_number}: Bot actions log: {bot_actions_log}")
        logger.info(f"Session {session_number}: Database: {botex_db}")
        
        # Start or use shared oTree server
        if shared_otree_server is None:
            # Reset oTree database (only if starting a new server)
            logger.info(f"Session {session_number}: Resetting oTree database...")
            try:
                subprocess.run(["otree", "resetdb", "--noinput"], check=True)
                logger.info(f"Session {session_number}: oTree database reset successful")
            except subprocess.CalledProcessError as e:
                logger.error(f"Session {session_number}: Failed to reset oTree database: {e}")
                print(f"Failed to reset oTree database: {e}")
                return False
            
            # Start a new oTree server
            logger.info(f"Session {session_number}: Starting oTree server...")
            otree_process = botex.start_otree_server(project_path=".")
            session_specific['otree_process'] = otree_process
        else:
            # Use the shared server
            otree_process = shared_otree_server
            logger.info(f"Session {session_number}: Using shared oTree server")
        
        # Initialize a session
        logger.info(f"Session {session_number}: Initializing social influence task session...")
        session = botex.init_otree_session(
            config_name='social_influence_task',  # Your task's config name
            npart=5,  # Social influence task needs 5 participants
            nhumans=1,  # Only 1 bot will be controlled by LLM
            otree_server_url="http://localhost:8000",
            botex_db=botex_db  # Use session-specific database
        )
        
        session_id = session['session_id']
        logger.info(f"Session {session_number}: Initialized with ID: {session_id}")
        
        # Define output filenames
        botex_responses_csv = path.join(output_dir, f"botex_{session_id}_responses.csv")
        botex_participants_csv = path.join(output_dir, f"botex_{session_id}_participants.csv")
        otree_wide_csv = path.join(output_dir, f"otree_{session_id}_wide.csv")
        
        # Run the bot on the session
        monitor_url = f"http://localhost:8000/SessionMonitor/{session_id}"
        logger.info(f"Session {session_number}: Starting bot. You can monitor progress at {monitor_url}")
        print(f"\nSession {session_number}: Starting bot. You can monitor progress at {monitor_url}")
        
        # Now run a single bot
        if session['bot_urls']:
            # There should be one bot URL in the list
            logger.info(f"Session {session_number}: Running single bot with risk-taking prompts")
            botex.run_single_bot(
                url=session['bot_urls'][0],
                session_name=session_id,  # Set session name explicitly
                session_id=session_id,    # Set session id explicitly  
                participant_id=session['participant_code'][0],  # Set the participant code explicitly
                botex_db=botex_db,        # Use session-specific database
                model=LLM_MODEL,
                api_key=LLM_API_KEY,
                throttle=True,  # Enable throttling to avoid rate limits
                user_prompts=get_behaviour_prompts(),  # Add custom behaviour prompts
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
            f.write(f"Number of participants: 5 (1 LLM bot, 4 automated)\n")
            f.write(f"Custom prompts: Risk-taking behavior\n\n")
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
            f.write("- Each participant made choices between options A and B over 64 rounds\n")
            f.write("- One LLM bot made decisions with a risk-taking strategy\n")
            f.write("- Bot was prompted to prefer higher bets and be more willing to go against the majority\n")
            f.write("- Other 4 players had pre-determined choices\n")
            f.write("- Options had different reward probabilities that changed across blocks\n")
        
        logger.info(f"Session {session_number}: Experiment complete. All outputs saved to {output_dir} folder")
        
        # Record success status
        session_specific['success'] = True
        session_specific['session_id'] = session_id
        session_specific['output_dir'] = output_dir
        
        return session_specific
    
    except Exception as e:
        logger.error(f"Session {session_number}: Error running experiment: {str(e)}", exc_info=True)
        print(f"\nSession {session_number}: Error running experiment: {str(e)}")
        session_specific['success'] = False
        session_specific['error'] = str(e)
        return session_specific
    
    finally:
        # Remove handlers specific to this session
        if 'handlers' in session_specific:
            for handler in session_specific['handlers']:
                logger.removeHandler(handler)
                try:
                    handler.close()
                except:
                    pass
                
        # Stop the oTree server if we started it
        if 'otree_process' in session_specific and shared_otree_server is None:
            try:
                logger.info(f"Session {session_number}: Stopping oTree server...")
                botex.stop_otree_server(session_specific['otree_process'])
                logger.info(f"Session {session_number}: oTree server stopped")
            except Exception as e:
                logger.error(f"Session {session_number}: Error stopping oTree server: {str(e)}")

def main():
    """Main function to run multiple concurrent sessions"""
    print(f"\nRunning {NUM_SESSIONS} concurrent sessions. Results will be stored in the '{base_output_dir}' directory.")
    
    # Start a single shared oTree server for all sessions
    try:
        # Reset oTree database once
        logger.info("Resetting oTree database...")
        subprocess.run(["otree", "resetdb", "--noinput"], check=True)
        logger.info("oTree database reset successful")
        
        # Start a single oTree server for all sessions
        logger.info("Starting shared oTree server...")
        shared_otree_server = botex.start_otree_server(project_path=".")
        logger.info("Shared oTree server started successfully")
        
        # Run sessions concurrently using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=NUM_SESSIONS) as executor:
            # Submit all sessions and get futures
            futures = []
            for i in range(1, NUM_SESSIONS + 1):
                future = executor.submit(run_session, i, shared_otree_server)
                futures.append(future)
            
            # Wait for all to complete and get results
            results = []
            for i, future in enumerate(futures, 1):
                try:
                    result = future.result()
                    results.append(result)
                    if result['success']:
                        print(f"Session {i} completed successfully: {result['session_id']}")
                    else:
                        print(f"Session {i} failed: {result.get('error', 'Unknown error')}")
                except Exception as e:
                    print(f"Session {i} failed with exception: {str(e)}")
            
            # Print summary
            successes = sum(1 for r in results if r.get('success', False))
            print(f"\nCompleted {successes} out of {NUM_SESSIONS} sessions successfully")
            
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}", exc_info=True)
        print(f"\nError in main execution: {str(e)}")
    
    finally:
        # Stop the shared oTree server
        if 'shared_otree_server' in locals():
            try:
                logger.info("Stopping shared oTree server...")
                botex.stop_otree_server(shared_otree_server)
                logger.info("Shared oTree server stopped")
            except Exception as e:
                logger.error(f"Error stopping shared oTree server: {str(e)}")

if __name__ == "__main__":
    main()