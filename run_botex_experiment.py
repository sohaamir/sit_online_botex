#!/usr/bin/env python3
"""
run_botex_experiment.py - Run social influence task with multiple LLM backends

This script allows running the social influence task experiment with various LLM backends:
- Google Gemini via API
- OpenAI (GPT-4, etc.) via API
- Anthropic Claude via API
- TinyLLaMA locally via llama.cpp

Usage:
    python run_botex_experiment.py [OPTIONS]

    Use --help to see all options
"""

from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from pathlib import Path
import subprocess
import webbrowser
import platform
import argparse
import datetime
import requests
import logging
import shutil
import random
import botex
import time
import json
import sys
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("run_multi_model")

# Custom log filter to exclude noisy HTTP request logs
class LogFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        if "HTTP Request:" in message or "Throttling: Request error:" in message:
            return False
        return True

for handler in logging.getLogger().handlers:
    handler.addFilter(LogFilter())

def parse_arguments():
    """Parse command line arguments, using defaults from environment if not provided"""
    # First load environment variables
    load_dotenv("botex.env")

    parser = argparse.ArgumentParser(description="Run social influence task with LLM bots")
    
    # General experiment configuration
    parser.add_argument("-c", "--config", default="botex.env",
                        help="Path to the environment file containing the botex configuration")
    parser.add_argument("-o", "--output-dir", default=os.environ.get("EXPERIMENT_OUTPUT_DIR", "botex_data"),
                        help="Directory to store experiment output")
    parser.add_argument("-s", "--sessions", type=int, default=1,
                        help="Number of concurrent sessions to run")
    
    # LLM model selection
    parser.add_argument("-m", "--model", default=None,
                        choices=["gemini", "openai", "anthropic", "tinyllama", "any"],
                        help="LLM implementation to use (gemini, openai, anthropic, tinyllama, or any)")
    
    # Model-specific parameters
    parser.add_argument("-k", "--api-key", default=None,
                        help="API key for cloud models (if not set in .env)")
    parser.add_argument("--max-tokens", type=int, default=None,
                        help="Maximum number of tokens for model responses")
    parser.add_argument("--temperature", type=float, default=None,
                        help="Temperature setting for the model")
    
    # Questionnaire role configuration (NEW)
    parser.add_argument("--q-role", default="typical",
                        choices=["typical", "patient"],
                        help="Role for questionnaire completion (typical: neurotypical individual, patient: individual with psychopathology)")
    
    # llama.cpp specific settings
    parser.add_argument("--model-path", default=os.environ.get("LLAMACPP_LOCAL_LLM_PATH"),
                        help="Path to local model file (for tinyllama)")
    parser.add_argument("--server-path", default=os.environ.get("LLAMACPP_SERVER_PATH"),
                        help="Path to llama.cpp server executable")
    parser.add_argument("--server-url", default=os.environ.get("LLAMACPP_SERVER_URL"),
                        help="URL for llama.cpp server")
    
    # botex database
    parser.add_argument("-b", "--botex-db", default=os.environ.get("BOTEX_DB", "botex.sqlite3"),
                        help="Path to botex SQLite database file")
    
    # oTree settings
    parser.add_argument("-u", "--otree-url", default=os.environ.get("OTREE_SERVER_URL", "http://localhost:8000"),
                        help="oTree server URL")
    parser.add_argument("-r", "--otree-rest-key", default=os.environ.get("OTREE_REST_KEY"),
                        help="oTree REST API key")
    parser.add_argument("-p", "--participants", type=int, 
                        default=int(os.environ.get("OTREE_NPARTICIPANTS", "5")),
                        help="Number of participants in the session")
    parser.add_argument("-n", "--humans", type=int,
                        default=int(os.environ.get("OTREE_NHUMANS", "0")),
                        help="Number of human participants")
    parser.add_argument("--session-config", default=os.environ.get("OTREE_SESSION_CONFIG", "social_influence_task"),
                        help="oTree session configuration name")
    
    # Debugging and control options
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose logging")
    parser.add_argument("-x", "--no-throttle", action="store_true",
                        help="Disable throttling of API requests")
    
    args = parser.parse_args()
    
    # If model is 'any', use whatever model has keys available
    if args.model == 'any' or args.model is None:
        # Check environment variables for API keys in priority order
        if os.environ.get("ANTHROPIC_API_KEY"):
            args.model = "anthropic"
            logger.info("No model specified, using Anthropic Claude (found API key)")
        elif os.environ.get("OPENAI_API_KEY"):
            args.model = "openai"
            logger.info("No model specified, using OpenAI (found API key)")
        elif os.environ.get("GEMINI_API_KEY") or os.environ.get("OTREE_GEMINI_API_KEY"):
            args.model = "gemini"
            logger.info("No model specified, using Google Gemini (found API key)")
        elif os.environ.get("LLAMACPP_LOCAL_LLM_PATH"):
            args.model = "tinyllama"
            logger.info("No model specified, using TinyLLama local model")
        else:
            logger.error("No model specified and couldn't determine from environment")
            sys.exit(1)
    
    # Set API key based on model if not explicitly provided
    if args.api_key is None:
        if args.model == "gemini":
            # Try both environment variable formats
            args.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("OTREE_GEMINI_API_KEY")
            if not args.api_key:
                logger.error("No Gemini API key found. Please set GEMINI_API_KEY in botex.env or provide with --api-key")
                sys.exit(1)
        elif args.model == "openai":
            args.api_key = os.environ.get("OPENAI_API_KEY")
            if not args.api_key:
                logger.error("No OpenAI API key found. Please set OPENAI_API_KEY in botex.env or provide with --api-key")
                sys.exit(1)
        elif args.model == "anthropic":
            args.api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not args.api_key:
                logger.error("No Anthropic API key found. Please set ANTHROPIC_API_KEY in botex.env or provide with --api-key")
                sys.exit(1)
    
    # Set model string based on the selected model
    if not hasattr(args, 'model_string'):
        if args.model == "gemini":
            args.model_string = os.environ.get("GEMINI_MODEL", "gemini/gemini-1.5-flash")
        elif args.model == "openai":
            args.model_string = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        elif args.model == "anthropic":
            args.model_string = os.environ.get("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        elif args.model == "tinyllama":
            args.model_string = "llamacpp"
        else:
            logger.error(f"Model {args.model} not supported")
            sys.exit(1)
    
    # Set max tokens if not specified
    if args.max_tokens is None:
        if args.model == "tinyllama":
            args.max_tokens = int(os.environ.get("LLAMACPP_MAX_TOKENS", "256"))
        else:
            args.max_tokens = int(os.environ.get("MAX_TOKENS_DEFAULT", "1024"))
    
    # Set temperature if not specified
    if args.temperature is None:
        if args.model == "tinyllama":
            args.temperature = float(os.environ.get("LLAMACPP_TEMPERATURE", "0.7"))
        else:
            args.temperature = 0.7
    
    return args

def get_general_instructions():
    """General instructions that apply to both questionnaires and task"""
    return """You are participating in an online research study that may include questionnaires and/or experimental tasks, potentially involving other human or artificial participants. 

    GENERAL PARTICIPATION GUIDELINES:
    - Respond honestly and thoughtfully to all questions and tasks
    - Follow the instructions provided on each page carefully  
    - If compensation information is mentioned, consider it as applying to you
    - Be patient during waiting periods - this is normal in multiplayer experiments
    - Always respond in valid JSON format when requested
    
    The study consists of different components:
    - Questionnaires asking about your thoughts, feelings, and behaviors
    - Experimental tasks that may involve decisions and interactions with others
    
    Each component has its own specific instructions which will be provided."""

def get_questionnaire_instructions():
    """Specific instructions for questionnaire components"""
    return """QUESTIONNAIRE COMPLETION INSTRUCTIONS:
    
    When you encounter questionnaire pages:
    - Read each question carefully and completely
    - Consider your genuine thoughts, feelings, and typical behaviors
    - Answer based on your assigned role and psychological state
    - Don't overthink individual items - respond intuitively
    - Be consistent in your responses throughout all questionnaires
    - There are no right or wrong answers - just answer honestly from your perspective
    
    The questionnaires assess various psychological and social aspects such as:
    - Social anxiety and avoidance behaviors
    - Mood and emotional experiences  
    - Social interaction patterns
    - Personality characteristics
    - Cognitive and perceptual experiences"""

def get_task_instructions():
    """Specific instructions for experimental task components"""
    return """EXPERIMENTAL TASK INSTRUCTIONS:
    
    When you encounter experimental task pages:
    - Read all instructions carefully before making decisions
    - Pay attention to information about other participants' choices
    - Make decisions that align with your goals in the task
    - Consider both your own experiences and social information when making choices
    - Wait patiently when other participants are making their decisions
    - Follow any specific formatting requirements for your responses"""

def get_questionnaire_role_instructions(role="typical"):
    """Generate role-specific instructions for questionnaire completion"""
    
    if role == "patient":
        return """YOUR ROLE - Individual with Psychopathology:
        
        You are someone who is currently experiencing significant psychological difficulties. Your responses should reflect the perspective of someone dealing with mental health challenges.
        
        Your psychological profile:
        - You experience persistent feelings of sadness, hopelessness, or emptiness
        - You have high levels of anxiety, particularly in social situations
        - You often feel isolated and disconnected from others
        
        When answering questionnaires:
        - Reflect these ongoing psychological difficulties in your responses
        - Be honest about the severity of your symptoms"""
        
    else:  # typical (neurotypical)
        return """YOUR ROLE - Neurotypical Individual:
        
        You are someone with typical psychological functioning and mental health. Your responses should reflect the perspective of a psychologically healthy individual.
        
        Your psychological profile:
        - You experience normal variations in mood but generally feel emotionally stable
        - You have typical levels of anxiety that don't significantly impair your functioning
        - You feel connected to others and maintain healthy social relationships
        
        When answering questionnaires:
        - Reflect normal, healthy psychological functioning
        - Answer from the perspective of someone who is mentally well-adjusted"""

def get_bot_prompts(q_role="typical"):
    """Create the complete prompt system with all components"""
    
    # Combine all instructions
    general_instructions = get_general_instructions()
    questionnaire_instructions = get_questionnaire_instructions() 
    task_instructions = get_task_instructions()
    role_instructions = get_questionnaire_role_instructions(q_role)
    
    # Create the comprehensive system prompt
    system_prompt = f"""{general_instructions}

{questionnaire_instructions}

{task_instructions}

{role_instructions}

Remember: Always analyze each page carefully and respond in valid JSON format when requested."""

    # Create the page analysis prompt
    analyze_prompt = """Perfect. This is your summary of the study so far: 

{summary} 

You have now proceeded to the next page. This is the body text of the web page: 

{body} 

I need you to answer {nr_q} question(s) and update your summary.

RESPONSE FORMATTING:
For each question, provide:
- 'reason': Your reasoning or thought process leading to your response
- 'answer': Your final answer to the question

QUESTIONNAIRE RESPONSES:
- Answer according to your assigned psychological role and profile
- Be consistent with your established character throughout
- Provide brief reasoning that explains your perspective

TASK RESPONSES:  
- Consider the specific instructions provided in the task
- Reference relevant information about other participants if applicable
- Explain your decision-making process clearly

The following JSON string contains the questions: {questions_json}

Respond with this format: {{"answers": {{"question_id": {{"reason": "Your reasoning", "answer": "Your answer"}}}}, "summary": "Updated summary of the study", "confused": false}}"""

    return {
        "system": system_prompt,
        "analyze_page_q": analyze_prompt
    }

def get_tinyllama_prompts(q_role="typical"):
    """Return simplified prompts optimized for TinyLLaMA"""
    
    # Simplified role instruction
    if q_role == "patient":
        role_context = "You have mental health difficulties. Answer questionnaires reflecting psychological problems. "
    else:
        role_context = "You are mentally healthy. Answer questionnaires as a typical person. "
    
    # Very simplified system prompt
    system_prompt = f"""You are in a research study. {role_context}Answer in JSON format only. Keep responses brief."""
    
    # Simplified analysis prompt  
    analyze_prompt = """Summary: {summary}

Page: {body}

Answer {nr_q} questions: {questions_json}

JSON format: {{"answers": {{...}}, "summary": "Brief summary", "confused": false}}

Keep all text very short."""
    
    return {
        "system": system_prompt,
        "analyze_page_q": analyze_prompt
    }

def export_ordered_response_data(csv_file, botex_db, session_id):
    """Export botex response data with comprehension questions at the top and specific ordering"""
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
                response['round'] == 1):  # Round 1 is typically comprehension checks
                comprehension_responses.append(response)
            else:
                task_responses.append(response)
        
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
        import csv
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['session_id', 'participant_id', 'round', 'question_id', 'answer', 'reason'])
            writer.writeheader()
            writer.writerows(ordered_responses)
            logger.info(f"Successfully wrote {len(ordered_responses)} responses to {csv_file}")
            
    except Exception as e:
        logger.error(f"Error in export_ordered_response_data: {str(e)}")
        
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

def configure_tinyllama_params(args, user_prompts):
    """Configure parameters for TinyLLaMA bots to be used with run_bots_on_session"""
    
    # Add explicit brevity instructions to all prompts
    modified_prompts = {}
    for key, value in user_prompts.items():
        if isinstance(value, str):
            modified_prompts[key] = value + "\n\nIMPORTANT: Your responses must be extremely brief and concise."
    
    # Make sure temperature is high enough to avoid repetition
    temperature = max(args.temperature, 0.8)
    
    # Enforce low max tokens
    max_tokens = min(args.max_tokens, 256)
    
    # Define additional parameters for llamacpp
    additional_params = {
        'temperature': temperature,
        'max_tokens': max_tokens,
    }
    
    if args.model == 'llamacpp':
        additional_params['repetition_penalty'] = 1.1
    
    return modified_prompts, additional_params

def run_session(args, session_number):
    """Run a single experimental session with a botex bot"""
    try:
        # Import botex here to ensure environment variables are loaded first
        import botex
        
        # Create timestamp for this session
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = f"session_{session_number}_{timestamp}"
        
        # Calculate number of bots
        n_bots = args.participants - args.humans
        
        # Create model-specific suffix with detailed information INCLUDING questionnaire role
        if args.model == "tinyllama":
            # For TinyLLaMA, use a simpler descriptor
            model_full_name = "tinyllama"
        else:
            # For API models, extract the full model name from the model string
            # Remove any vendor prefix like 'gemini/' or 'anthropic/'
            if '/' in args.model_string:
                model_full_name = args.model_string.split('/')[-1]
            else:
                model_full_name = args.model_string
        
        # Updated suffix with humans, bots, detailed model info, AND questionnaire role
        model_suffix = f"_{args.model}_nhumans{args.humans}_nbots{n_bots}_{model_full_name}_qrole{args.q_role}"
        
        # Create session-specific output directory with enhanced suffix
        output_dir = os.path.join(args.output_dir, f"session_{session_id}{model_suffix}")
        os.makedirs(output_dir, exist_ok=True)
        
        # Create session-specific database and log files with enhanced suffix
        botex_db = os.path.join(output_dir, f"botex_{session_id}{model_suffix}.sqlite3")
        log_file = os.path.join(output_dir, f"experiment_log_{timestamp}{model_suffix}.txt")
        bot_actions_log = os.path.join(output_dir, f"bot_actions_{timestamp}{model_suffix}.txt")
        
        # Set up session-specific logging
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
        
        logger.info(f"Session {session_number}: Output directory: {output_dir}")
        logger.info(f"Session {session_number}: Log file: {log_file}")
        logger.info(f"Session {session_number}: Using model: {args.model_string}")
        logger.info(f"Session {session_number}: Questionnaire role: {args.q_role}")
        
        # Initialize an oTree session
        logger.info(f"Session {session_number}: Initializing oTree session with config: {args.session_config}")
        session = botex.init_otree_session(
            config_name=args.session_config,
            npart=args.participants,
            nhumans=args.humans,
            botex_db=botex_db,
            otree_server_url=args.otree_url,
            otree_rest_key=args.otree_rest_key
        )
        
        # Get the session ID from the returned data
        otree_session_id = session['session_id']
        logger.info(f"Session {session_number}: Initialized oTree session with ID: {otree_session_id}")
        
        # When exporting files, use the enhanced suffix:
        botex_responses_csv = os.path.join(output_dir, f"botex_{otree_session_id}_responses{model_suffix}.csv")
        botex_participants_csv = os.path.join(output_dir, f"botex_{otree_session_id}_participants{model_suffix}.csv")
        otree_wide_csv = os.path.join(output_dir, f"otree_{otree_session_id}_wide{model_suffix}.csv")
        
        # Get the monitor URL for display
        monitor_url = f"{args.otree_url}/SessionMonitor/{otree_session_id}"
        logger.info(f"Session {session_number}: Monitor URL: {monitor_url}")
        print(f"\nSession {session_number}: Starting bot with {args.model_string} (q-role: {args.q_role}). Monitor progress at {monitor_url}")

        # Automatically open Chrome with the monitor URL
        open_chrome_browser(monitor_url)
        
        # Run the bot only if bot URLs are available
        if session['bot_urls']:
            # Configure throttling
            throttle = not args.no_throttle
            
            # Prepare model-specific parameters
            if args.model == "tinyllama":
                # For TinyLLaMA, use special handling
                logger.info(f"Session {session_number}: Using TinyLLaMA with optimized settings")
                
                # Check if server is running
                server_url = args.server_url or "http://localhost:8080"
                llamacpp_server_running = False
                try:
                    import requests
                    response = requests.get(f"{server_url}/health", timeout=5)
                    if response.status_code == 200:
                        llamacpp_server_running = True
                        logger.info(f"Session {session_number}: llama.cpp server is running at {server_url}")
                except:
                    logger.warning(f"Session {session_number}: llama.cpp server not detected at {server_url}")
                
                # Start server if needed
                if not llamacpp_server_running:
                    logger.info(f"Session {session_number}: Starting llama.cpp server...")
                    server_process = botex.start_llamacpp_server({
                        "server_path": args.server_path,
                        "local_llm_path": args.model_path,
                        "server_url": server_url,
                        "maximum_tokens_to_predict": args.max_tokens,
                        "temperature": args.temperature,
                        "top_p": 0.9,
                        "top_k": 40,
                        "repeat_penalty": 1.1
                    })
                    logger.info(f"Session {session_number}: llama.cpp server started")
                else:
                    server_process = None
                
                # Get specialized TinyLLaMA prompts with questionnaire role
                user_prompts = get_tinyllama_prompts(args.q_role)
                modified_prompts, tinyllama_params = configure_tinyllama_params(args, user_prompts)

                # Run bots with optimized settings
                logger.info(f"Session {session_number}: Starting TinyLLaMA bots with optimized settings")
                botex.run_bots_on_session(
                    session_id=otree_session_id,
                    botex_db=botex_db,
                    user_prompts=modified_prompts,
                    throttle=throttle,
                    model="llamacpp",
                    api_base=server_url,
                    **tinyllama_params
                )
                
                # Clean up llama.cpp server if we started it
                if server_process is not None:
                    logger.info(f"Session {session_number}: Stopping llama.cpp server")
                    botex.stop_llamacpp_server(server_process)
                    logger.info(f"Session {session_number}: llama.cpp server stopped")
            else:
                # For API-based models (Gemini, OpenAI, Anthropic)
                model_params = {
                    "model": args.model_string,
                    "api_key": args.api_key,
                    "max_tokens": args.max_tokens,
                    "temperature": args.temperature
                }
                
                # Get standard prompts with questionnaire role
                user_prompts = get_bot_prompts(args.q_role)
                
                # Log partial API key for debugging
                if args.api_key:
                    masked_key = f"{'*' * (len(args.api_key) - 4)}{args.api_key[-4:]}" if len(args.api_key) > 4 else "****"
                    logger.info(f"Session {session_number}: API key provided: {masked_key}")
                else:
                    logger.warning(f"Session {session_number}: No API key provided")
                
                logger.info(f"Session {session_number}: Starting bot with {args.model_string}")
                botex.run_bots_on_session(
                    session_id=otree_session_id,
                    botex_db=botex_db,
                    user_prompts=user_prompts,
                    throttle=throttle,
                    **model_params
                )
            
            logger.info(f"Session {session_number}: Bot completed")
            
            # Save bot actions to JSON
            bot_actions_json = os.path.join(output_dir, f"bot_actions_{timestamp}{model_suffix}.json")
            with open(bot_actions_json, 'w') as f:
                json.dump(bot_actions, f, indent=2)
            logger.info(f"Session {session_number}: Bot actions saved to JSON: {bot_actions_json}")
            
            # Export botex participant data
            logger.info(f"Session {session_number}: Exporting botex participant data...")
            try:
                botex.export_participant_data(
                    botex_participants_csv,
                    botex_db=botex_db,
                    session_id=otree_session_id
                )
                logger.info(f"Session {session_number}: Participant data exported to {botex_participants_csv}")
            except Exception as e:
                logger.warning(f"Session {session_number}: Could not export participant data: {str(e)}")
            
            # Export botex response data with custom ordering
            logger.info(f"Session {session_number}: Exporting botex response data...")
            try:
                export_ordered_response_data(
                    botex_responses_csv,
                    botex_db=botex_db,
                    session_id=otree_session_id
                )
                logger.info(f"Session {session_number}: Response data exported to {botex_responses_csv}")
            except Exception as e:
                logger.warning(f"Session {session_number}: Error exporting responses: {str(e)}")
            
            # Export oTree data
            logger.info(f"Session {session_number}: Exporting oTree data...")
            try:
                botex.export_otree_data(
                    otree_wide_csv,
                    server_url=args.otree_url,
                    admin_name='admin',
                    admin_password=os.environ.get('OTREE_ADMIN_PASSWORD')
                )
                logger.info(f"Session {session_number}: oTree data exported to {otree_wide_csv}")
                
                # Normalize and export oTree data
                logger.info(f"Session {session_number}: Normalizing oTree data...")
                botex.normalize_otree_data(
                    otree_wide_csv, 
                    store_as_csv=True,
                    data_exp_path=output_dir,
                    exp_prefix=f"otree_{otree_session_id}{model_suffix}"
                )
                logger.info(f"Session {session_number}: oTree data normalized and exported")
            except Exception as e:
                logger.error(f"Session {session_number}: Failed to export oTree data: {str(e)}")
            
            # Create a summary file
            summary_file = os.path.join(output_dir, f"experiment_summary_{otree_session_id}{model_suffix}.txt")
            with open(summary_file, 'w') as f:
                f.write(f"Social Influence Task Experiment Summary - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*70 + "\n\n")
                f.write(f"Session ID: {otree_session_id}\n")
                f.write(f"Session Number: {session_number}\n")
                f.write(f"Model used: {args.model} ({args.model_string})\n")
                f.write(f"Questionnaire role: {args.q_role}\n")
                f.write(f"Max tokens: {args.max_tokens}\n")
                f.write(f"Temperature: {args.temperature}\n")
                f.write(f"Number of participants: {args.participants}\n")
                f.write(f"Number of human participants: {args.humans}\n\n")
                f.write("Files generated:\n")
                f.write(f"- Log file: {os.path.basename(log_file)}\n")
                f.write(f"- Bot actions log: {os.path.basename(bot_actions_log)}\n")
                f.write(f"- Bot actions JSON: {os.path.basename(bot_actions_json)}\n")
                f.write(f"- Bot participants: {os.path.basename(botex_participants_csv)}\n")
                f.write(f"- Bot responses: {os.path.basename(botex_responses_csv)}\n")
                f.write(f"- oTree wide data: {os.path.basename(otree_wide_csv)}\n")
            
            logger.info(f"Session {session_number}: Experiment completed successfully")
            return {"success": True, "session_id": otree_session_id, "output_dir": output_dir}
        else:
            logger.warning(f"Session {session_number}: No bot URLs found")
            return {"success": False, "error": "No bot URLs found"}
    
    except Exception as e:
        logger.error(f"Session {session_number}: Error: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}
    
    finally:
        # Clean up logging handlers
        if 'file_handler' in locals():
            logger.removeHandler(file_handler)
            file_handler.close()
        if 'bot_actions_handler' in locals():
            logger.removeHandler(bot_actions_handler)
            bot_actions_handler.close()
        if 'json_handler' in locals():
            logger.removeHandler(json_handler)

def open_chrome_browser(url, max_attempts=5):
    """Open the specified URL in a browser with retry logic"""
    
    for attempt in range(max_attempts):
        try:
            # macOS-specific approach for Chrome
            if platform.system() == 'Darwin':
                try:
                    # Try to use Google Chrome specifically
                    subprocess.run(['open', '-a', 'Google Chrome', url], check=True)
                    logger.info(f"Opened Chrome with URL: {url}")
                    return True
                except subprocess.CalledProcessError:
                    # Fall back to default browser if Chrome isn't available
                    webbrowser.open(url)
                    logger.info(f"Opened default browser with URL: {url}")
                    return True
            else:
                # For other platforms use the webbrowser module
                webbrowser.open(url)
                logger.info(f"Opened browser with URL: {url}")
                return True
                
        except Exception as e:
            logger.warning(f"Browser opening attempt {attempt+1}/{max_attempts} failed: {str(e)}")
            if attempt < max_attempts - 1:
                time.sleep(1)  # Wait before retrying
    
    logger.error(f"Failed to open browser after {max_attempts} attempts")
    return False

def main():
    """Main function to run the experiment"""
    # Parse arguments
    args = parse_arguments()
    
    # Set up logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Log the configuration
    logger.info(f"Starting experiment with {args.model} model ({args.model_string})")
    logger.info(f"Questionnaire role: {args.q_role}")
    logger.info(f"Number of sessions: {args.sessions}")
    logger.info(f"Max tokens: {args.max_tokens}")
    
    # Import botex here to ensure environment variables are loaded first
    try:
        import botex
    except ImportError:
        logger.error("Failed to import botex. Make sure it's installed: pip install botex")
        sys.exit(1)
    
    # Start oTree server if not already running
    otree_server_running = False
    try:
        import requests
        response = requests.get(f"{args.otree_url}/")
        if response.status_code == 200:
            otree_server_running = True
            logger.info(f"oTree server is running at {args.otree_url}")
    except:
        logger.warning(f"oTree server not detected at {args.otree_url}")
    
    # Start oTree server if needed
    if not otree_server_running:
        logger.info("Starting oTree server...")
        try:
            subprocess.run(["otree", "resetdb", "--noinput"], check=True)
            logger.info("oTree database reset successful")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to reset oTree database: {e}")
            sys.exit(1)
        
        otree_process = botex.start_otree_server(project_path=".")
        logger.info(f"oTree server started at {args.otree_url}")
    else:
        otree_process = None
    
    try:
        # Run the sessions
        if args.sessions == 1:
            # Run a single session directly
            result = run_session(args, 1)
            if result["success"]:
                print(f"\nSession completed successfully: {result['session_id']}")
                print(f"Output directory: {result['output_dir']}")
            else:
                print(f"\nSession failed: {result.get('error', 'Unknown error')}")
        else:
            # Run multiple sessions concurrently
            with ThreadPoolExecutor(max_workers=args.sessions) as executor:
                futures = [executor.submit(run_session, args, i+1) for i in range(args.sessions)]
                
                # Wait for all sessions to complete
                results = []
                for i, future in enumerate(futures, 1):
                    try:
                        result = future.result()
                        results.append(result)
                        if result["success"]:
                            print(f"Session {i} completed successfully: {result['session_id']}")
                        else:
                            print(f"Session {i} failed: {result.get('error', 'Unknown error')}")
                    except Exception as e:
                        print(f"Session {i} failed with exception: {str(e)}")
                
                # Print summary
                successes = sum(1 for r in results if r.get("success", False))
                print(f"\nCompleted {successes} out of {args.sessions} sessions successfully")
    
    finally:
        # Stop oTree server if we started it
        if otree_process is not None:
            logger.info("Stopping oTree server...")
            botex.stop_otree_server(otree_process)
            logger.info("oTree server stopped")

if __name__ == "__main__":
    main()