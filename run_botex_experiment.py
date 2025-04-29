# This script runs the social influence task experiment using the botex package with concurrent sessions.

from concurrent.futures import ThreadPoolExecutor
from os import environ, makedirs, path
from dotenv import load_dotenv
import subprocess
import threading
import datetime
import logging
import botex
import json
import csv
import sys
import re
import os

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
    """Returns the behavior prompts for the LLM bots with enhanced historical information tracking"""
    return {
        "system": """You are participating in an online survey and/or experiment, potentially involving other human or artificial participants. The user provides you with a series of independent prompts. 
        Most prompts will also contain scraped text data from a webpage containing the survey/experiment, and detailed tasks for you on how to analyze this text data. 
        The scraped web page texts contain instructions on how the experiment/survey is conducted. These instructions might include information on how participants are being compensated or paid for their participation. 
        If this is the case, please act as if this compensation also applies to you and make sure to include this information in the summary so that you will recall it in later prompts. 
        Most importantly, the scraped texts can include questions and/or tasks which the user wants you to answer. They might also contain comprehension checks, repeated information from prior pages, and potentially text bits that do not directly belong to the experiment. 

        EXPERIMENT OVERVIEW:
        - You are participating in a social experiment where your goal is to maximize points by making choices and placing bets. 
        - This is a probabilistic reversal learning task with two options (A and B). The reward contingencies switch across blocks without warning. 
        - Within each block, one option is more likely to give rewards, but rewards are probabilistic - even the better option will sometimes give losses.
        - You'll make choices and bets (reflecting choice confidence), in a group of 5 participants, who are learning the task at the same time as you. 
        - Therefore, you will be able to see others' choices; the extent to which this influences your own choices is up to you.
        
        CHOICE STRATEGY:
        - In the very first round only, you should choose randomly between B and A, do not explicitly favor one option over the other
        - Throughout the task, be FLEXIBLE in your choices based on both social information and your own experience of rewards
        - Remember that the other players are learning the task at the same time as you and might be wrong in their choices
        - Feel completely free to update your choice both WITHIN trials (from Choice 1 to Choice 2) AND ACROSS trials (from the immediately previous Choice 2 to current round Choice 1) based on the decisions of the group and your own experience and beliefs
        - Never fixate on one strategy - constantly adapt based on changing evidence
        
        BETTING STRATEGY:
        - Your bets (either 1, 2, or 3) should directly reflect your confidence in your choice
        - Bet 1 when uncertain about your choice, bet 2 when moderately confident, and bet 3 when fairly confident
        - Feel completely free to change your bet both WITHIN trials (from Bet 1 to Bet 2) AND ACROSS trials (from the immediately previous Bet 2 to current round Bet 1) based on the decisions of the group and your own experience and beliefs
        - Never fixate on one strategy - constantly adapt based on changing evidence
        - Betting conservatively is often a suboptimal strategy - to score the most points and get the highest bonus - vary your bets based on genuine confidence
        - This means betting 3 when you're confident or feel like taking a risk even when not confident. Doing so often leads to a higher score, which is the goal of the task

        INTEGRATING HISTORICAL INFORMATION:
        - Because the task is probabilistic, you should try to learn from your own rewards and the choices of others over time
        - You should be influenced by the choices of others in the immediate past respective to your choice i.e., using the previous round's group feedback for Choice 2 when making the current rounds Choice 1, and using the the current round's Choice 1 group feedback when making Choice 2
        - You should also be influenced by your own immediate choices and feedback when making these choices
        - However, you should retain only a vague memory of the last few rounds for your own feedback which you should use to learn the task structure and when the reversals may have occurred. This means that you should remember the last round quite clearly, but the rounds before that only vaguely
        - But all of this DOES NOT MEAN that you are more strongly influenced by your own choices - you are free to flexibly integrate social information and your own experience as you see fit
        - Remember that a round consists an initial choice, initial bet, second choice and second bet. A new round begins after the feedback for the second bet is given as indicated by the text 'ou have started a new round. Please make your initial choice and bet for this round, then submit the form'. IT IS IMPORTANT to keep track of rounds accurately
        
        When interacting with the experiment, analyze each page carefully and respond with a valid JSON.""",
                    
        "analyze_page_q": """Perfect. This is your summary of the survey/experiment so far: \n\n {summary} \n\n You have now proceeded to the next page. This is the body text of the web page: \n\n {body} \n\n 

        I need you to answer {nr_q} question(s) and update your summary. When making choices and bets, follow these critical guidelines:

        CHOICES:
        - Throughout the task, be FLEXIBLE in your choices based on both social information and your own experience
        - You should be influenced by the choices of others in the immediate past respective to your choice i.e., using the previous round's group feedback for Choice 2 when making the current rounds Choice 1, and using the the current round's Choice 1 group feedback when making Choice 2
        - You should also be influenced by your own immediate choices and feedback when making these choices
        - However, you should also retain a vague memory of the last few rounds regarding your own feedback and choice history, which you should use to learn the task structure and when the reversals may have occurred.
        - But all of this DOES NOT MEAN that you are more strongly influenced by your own choices - you are free to flexibly integrate social information and your own experience as you see fit
        - Remember that the other players are learning the task at the same time as you
        - Feel completely free to update your choice appropriately both WITHIN trials (from Choice 1 to Choice 2) AND ACROSS trials (from the immediately previous Choice 2 to current round Choice 1) based on the decisions of the group and your own experience and beliefs
        - Never fixate on one strategy - constantly adapt based on changing evidence

        BETTING:
        - Bet 1 when uncertain about your choice, bet 2 when moderately confident, and bet 3 when fairly confident
        - Betting conservatively can be a suboptimal strategy. To score the most points and get the highest bonus, vary your bets based on genuine confidence
        - Feel completely free to change your bet appropriately both WITHIN trials (from Bet 1 to Bet 2) AND ACROSS trials (from the immediately previous Bet 2 to current round Bet 1) based on the decisions of the group and your own experience and beliefs. How you do this is up to you
        - You should bet 3 when you're fairly confident or feel like taking a risk even when not confident. Taking calculated risks and backing yourself often leads to a higher score than betting conservatively

        HISTORICAL INFORMATION USAGE:
        When explaining your reasoning for CHOICES, you MUST specifically reference:
        1. WHICH round or rounds influenced your current decision
        2. WHAT pattern of rewards you've observed and remember
        3. HOW you're weighing social information against your own experience

        Your reasoning should demonstrate the integration of historical data, not just the most recent round.
        
        The following JSON string contains the questions: {questions_json} 

        For each identified question, you must provide two variables: 'reason' contains your reasoning or thought that leads you to a response or answer and 'answer' which contains your response.

        Taken together, a correct answer to a text with two questions would have the form {{""answers"": {{""ID of first question"": {{""reason"": ""Your reasoning for how you want to answer the first question"", ""answer"":""Your final answer to the first question""}}, ""ID of the second question"": {{""reason"": ""Your reasoning for how you want to answer the second question"", ""answer"": ""Your final answer to the second question""}}}},""summary"": ""Your summary"", ""confused"": ""set to `true` if you are confused by any part of the instructions, otherwise set it to `false`""}}"""
    }

# Add custom behavior prompts for different strategies
def get_custom_behaviour_prompts(strategy_type="standard"):
    """Returns behavior prompts with specific strategies"""
    
    base_prompts = get_behaviour_prompts()
    
    if strategy_type == "risk_taking":
        # Modify prompts to encourage higher bets and risk-taking
        base_prompts["system"] += """
        ADDITIONAL STRATEGY GUIDELINES:
        - You should be more willing to bet 3 even with moderate confidence
        - Be more willing to go against the majority when you have a strong hunch
        - Weight recent reward outcomes higher than social consensus
        - Be less risk-averse and more willing to explore options that might be less popular
        - When making a choice that differs from the majority, bet higher to maximize potential rewards
        """
    elif strategy_type == "social_follower":
        # Modify prompts to follow social influence more closely
        base_prompts["system"] += """
        ADDITIONAL STRATEGY GUIDELINES:
        - Prioritize social information from others above your own experience
        - When the majority chooses a different option than you, strongly consider switching
        - Be more conservative with bets when going against the group
        - Pay special attention to players who seem to be performing well
        - Update your choices more readily based on group consensus than on your own reward history
        """
    
    return base_prompts

# Function to run a single session with session-specific resources
def run_session(session_number, experiment_name, llm_model, api_key, shared_otree_server=None, output_dir="botex_data", strategy_type="standard"):
    """Run a single session with a unique database and logs"""
    session_specific = {}
    try:
        # Create timestamp for this session
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = f"session_{session_number}_{timestamp}"
        
        # Create session-specific output directory
        output_dir = os.path.join(output_dir, f"session_{session_id}")
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
        logger.info(f"Session {session_number}: Using model: {llm_model}")
        logger.info(f"Session {session_number}: Strategy type: {strategy_type}")
        
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
        logger.info(f"Session {session_number}: Initializing {experiment_name} session...")
        session = botex.init_otree_session(
            config_name=experiment_name,  # Use the provided experiment name
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
        
        # Get behavior prompts based on strategy type
        behavior_prompts = get_custom_behaviour_prompts(strategy_type)
        
        # Build bot parameters
        bot_kwargs = {
            "session_name": session_id,
            "session_id": session_id,
            "participant_id": session['participant_code'][0],
            "botex_db": botex_db,
            "model": llm_model,
            "throttle": True,  # Enable throttling to avoid rate limits
            "user_prompts": behavior_prompts,
            # Add increased delays to avoid rate limits with smaller models
            "initial_delay": 2.0,
            "backoff_factor": 2.0
        }
        
        # Add API key if using cloud model
        if api_key and llm_model != "llamacpp":
            bot_kwargs["api_key"] = api_key
            
        # Now run a single bot
        if session['bot_urls']:
            # There should be one bot URL in the list
            logger.info(f"Session {session_number}: Running single bot with {strategy_type} strategy using {llm_model}")
            botex.run_single_bot(
                url=session['bot_urls'][0],
                **bot_kwargs
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
            f.write(f"Session Number: {session_number}\n")
            f.write(f"Model used: {llm_model}\n")
            f.write(f"Bot strategy: {strategy_type}\n")
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
            f.write("- Each participant made choices between options A and B over 64 rounds\n")
            f.write(f"- One LLM bot ({llm_model}) made decisions with a {strategy_type} strategy\n")
            if strategy_type == "risk_taking":
                f.write("- Bot was prompted to prefer higher bets and be more willing to go against the majority\n")
            elif strategy_type == "social_follower":
                f.write("- Bot was prompted to prioritize social information and follow the group more closely\n")
            else:
                f.write("- Bot used standard balanced prompts for decision making\n")
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

def main(experiment_name='social_influence_task', num_sessions=1, llm_model="gemini/gemini-1.5-flash", 
         api_key=None, output_dir="botex_data", llm_server=None, strategy_type="standard"):
    """Main function to run multiple concurrent sessions"""
    print(f"\nRunning {num_sessions} concurrent sessions using {llm_model}.")
    print(f"Results will be stored in the '{output_dir}' directory.")
    
    # Get API key from environment if not provided and using cloud model
    if api_key is None and llm_model != "llamacpp":
        if llm_model.startswith("gemini"):
            api_key = environ.get('OTREE_GEMINI_API_KEY')
        elif llm_model.startswith("gpt"):
            api_key = environ.get('OPENAI_API_KEY')
            
        # Verify API key exists for cloud models
        if not api_key and llm_model != "llamacpp":
            logger.error(f"API key not found for model {llm_model}")
            print(f"\nError: API key not found for model {llm_model}")
            print("Make sure to set this in your .env file or provide it as an argument")
            return False
    
    # Start a single shared oTree server for all sessions
    try:
        # We'll use the server provided or start our own
        shared_otree_server = llm_server
        local_otree_server = False
        
        if shared_otree_server is None:
            # Reset oTree database once
            logger.info("Resetting oTree database...")
            subprocess.run(["otree", "resetdb", "--noinput"], check=True)
            logger.info("oTree database reset successful")
            
            # Start a single oTree server for all sessions
            logger.info("Starting shared oTree server...")
            shared_otree_server = botex.start_otree_server(project_path=".")
            logger.info("Shared oTree server started successfully")
            local_otree_server = True
        
        # Run sessions concurrently using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=num_sessions) as executor:
            # Submit all sessions and get futures
            futures = []
            for i in range(1, num_sessions + 1):
                future = executor.submit(
                    run_session, 
                    i, 
                    experiment_name,
                    llm_model,
                    api_key,
                    shared_otree_server,
                    output_dir,
                    strategy_type
                )
                futures.append(future)
            
            # Wait for all to complete and get results
            results = []
            for i, future in enumerate(futures, 1):
                try:
                    result = future.result()
                    results.append(result)
                    if result.get('success', False):
                        print(f"Session {i} completed successfully: {result['session_id']}")
                    else:
                        print(f"Session {i} failed: {result.get('error', 'Unknown error')}")
                except Exception as e:
                    print(f"Session {i} failed with exception: {str(e)}")
            
            # Print summary
            successes = sum(1 for r in results if r.get('success', False))
            print(f"\nCompleted {successes} out of {num_sessions} sessions successfully")
            
        return successes == num_sessions  # Return True if all sessions completed successfully
    
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}", exc_info=True)
        print(f"\nError in main execution: {str(e)}")
        return False
    
    finally:
        # Stop the shared oTree server only if we started it
        if local_otree_server and 'shared_otree_server' in locals():
            try:
                logger.info("Stopping shared oTree server...")
                botex.stop_otree_server(shared_otree_server)
                logger.info("Shared oTree server stopped")
            except Exception as e:
                logger.error(f"Error stopping shared oTree server: {str(e)}")

if __name__ == "__main__":
    # When run directly, use default parameters
    main()