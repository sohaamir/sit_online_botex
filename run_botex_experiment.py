#!/usr/bin/env python3
"""
run_botex_experiment.py - Run social influence task with LLM bots using different backends

This script allows running the social influence task experiment with LLM bots using
one of three backends:
- Google Gemini via API
- OpenAI GPT-4o via API
- TinyLLaMA locally via llama.cpp

Usage:
    python run_botex_experiment.py [OPTIONS]

    Use --help to see all options
"""

from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from pathlib import Path
import subprocess
import argparse
import datetime
import logging
import openai
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
logger = logging.getLogger("run_botex_experiment")

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
                        choices=["gemini", "openai", "tinyllama"],
                        help="LLM implementation to use (gemini, openai, or tinyllama)")
    
    # Model-specific parameters
    parser.add_argument("-k", "--api-key", default=None,
                        help="API key for cloud models (if not set in .env)")
    parser.add_argument("--max-tokens", type=int, default=None,
                        help="Maximum number of tokens for model responses")
    parser.add_argument("--temperature", type=float, default=None,
                        help="Temperature setting for the model")
    
    # Bot behavior configuration
    parser.add_argument("--strategy", default=os.environ.get("BOT_STRATEGY", "standard"),
                        choices=["standard", "risk_taking", "social_follower"],
                        help="Bot strategy to use")
    
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
    
    # If model not specified, try to determine from environment
    if args.model is None:
        if os.environ.get("GEMINI_API_KEY") or os.environ.get("OTREE_GEMINI_API_KEY"):
            args.model = "gemini"
        elif os.environ.get("OPENAI_API_KEY"):
            args.model = "openai"
        elif os.environ.get("LLAMACPP_LOCAL_LLM_PATH"):
            args.model = "tinyllama"
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
    
    # Set max tokens if not specified
    if args.max_tokens is None:
        if args.model == "tinyllama":
            args.max_tokens = int(os.environ.get("LLAMACPP_MAX_TOKENS", "512"))
        else:
            args.max_tokens = int(os.environ.get("MAX_TOKENS_DEFAULT", "2048"))
    
    # Set temperature if not specified
    if args.temperature is None:
        if args.model == "tinyllama":
            args.temperature = float(os.environ.get("LLAMACPP_TEMPERATURE", "0.7"))
        else:
            args.temperature = 0.7
    
    return args

def get_bot_prompt_strategy(strategy="standard"):
    """Return the appropriate bot prompts based on the strategy"""
    
    base_system_prompt = """You are participating in an online survey and/or experiment, potentially involving other human or artificial participants. The user provides you with a series of independent prompts. 
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

        HISTORICAL INFORMATION USAGE:
        - Because the task is probabilistic, you should try to learn from your own rewards and the choices of others over time
        - You should be influenced by the choices of others in the immediate past respective to your choice
        - You should also be influenced by your own immediate choices and feedback
        - However, you should retain only a vague memory of the last few rounds for your own feedback
        - Remember that a round consists of an initial choice, initial bet, second choice and second bet
        
        When interacting with the experiment, analyze each page carefully and respond with a valid JSON."""
    
    # Strategy-specific prompts
    if strategy == "risk_taking":
        # More risk-taking strategy
        strategy_prompt = """
        CHOICE STRATEGY:
        - In the very first round only, you should choose randomly between B and A
        - Throughout the task, be FLEXIBLE and somewhat BOLD in your choices
        - You should be willing to go against the majority opinion more often
        - When you see a potential pattern, act on it more aggressively
        - Feel completely free to update your choice both WITHIN trials and ACROSS trials
        - Never fixate on one strategy - constantly adapt based on changing evidence
        
        BETTING STRATEGY:
        - Your bets should reflect a higher risk tolerance than average
        - Be more willing to place bet 3 (high confidence) even with moderate certainty
        - Bet 1 only when genuinely uncertain, prefer bet 2 or 3 when you have any confidence
        - You should prioritize higher rewards by placing higher bets more often
        - Never bet 1 more than two rounds in a row - show more confidence!
        - Betting conservatively is often suboptimal - to maximize your score, TAKE RISKS
        """
    elif strategy == "social_follower":
        # More socially influenced strategy
        strategy_prompt = """
        CHOICE STRATEGY:
        - In the very first round only, you should choose randomly between B and A
        - Throughout the task, prioritize SOCIAL INFORMATION over your own experiences
        - When the majority of other players choose an option, strongly consider following them
        - Be more likely to switch your choice if you see others choosing differently
        - Still be flexible in your choices, but weight social information more heavily
        - Never fixate on one strategy - constantly adapt based on changing evidence
        
        BETTING STRATEGY:
        - Your bets should directly reflect your confidence in your choice
        - Bet 1 when uncertain about your choice, bet 2 when moderately confident, and bet 3 when fairly confident
        - When following the majority, bet higher (more confidently)
        - When going against the majority, bet lower (less confidently)
        - Adjust your bet based on how unanimous the other players are
        - Betting conservatively when uncertain is your preferred approach
        """
    else:  # standard strategy
        strategy_prompt = """
        CHOICE STRATEGY:
        - In the very first round only, you should choose randomly between B and A
        - Throughout the task, be FLEXIBLE in your choices based on both social information and your own experience
        - Remember that the other players are learning the task at the same time as you
        - Feel completely free to update your choice both WITHIN trials and ACROSS trials
        - Never fixate on one strategy - constantly adapt based on changing evidence
        
        BETTING STRATEGY:
        - Your bets should directly reflect your confidence in your choice
        - Bet 1 when uncertain about your choice, bet 2 when moderately confident, and bet 3 when fairly confident
        - Feel completely free to change your bet both WITHIN trials and ACROSS trials
        - Never fixate on one strategy - constantly adapt based on changing evidence
        - Betting conservatively is often a suboptimal strategy - vary your bets based on genuine confidence
        """
    
    # Combine base prompt with strategy-specific instructions
    combined_system_prompt = base_system_prompt + "\n\n" + strategy_prompt
    
    # Create the full prompts dictionary
    prompts = {
        "system": combined_system_prompt,
        
        "analyze_page_q": """Perfect. This is your summary of the survey/experiment so far: \n\n {summary} \n\n You have now proceeded to the next page. This is the body text of the web page: \n\n {body} \n\n 

        I need you to answer {nr_q} question(s) and update your summary. When making choices and bets, follow these critical guidelines:

        CHOICES:
        - Throughout the task, be FLEXIBLE in your choices based on both social information and your own experience
        - You should be influenced by the choices of others in the immediate past respective to your choice
        - You should also be influenced by your own immediate choices and feedback
        - However, you should also retain a vague memory of the last few rounds regarding your own feedback
        - Feel completely free to update your choice appropriately both WITHIN trials and ACROSS trials
        - Never fixate on one strategy - constantly adapt based on changing evidence

        BETTING:
        - Bet 1 when uncertain about your choice, bet 2 when moderately confident, and bet 3 when fairly confident
        - Betting conservatively can be a suboptimal strategy. To score the most points, vary your bets based on genuine confidence
        - Feel completely free to change your bet appropriately both WITHIN trials and ACROSS trials

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
    
    # Customize the prompts based on strategy
    if strategy == "risk_taking":
        prompts["analyze_page_q"] = prompts["analyze_page_q"].replace(
            "Bet 1 when uncertain about your choice, bet 2 when moderately confident, and bet 3 when fairly confident",
            "Be more willing to place bet 3 (high confidence) even with moderate certainty. Prefer bet 2 or 3 when you have any confidence."
        ).replace(
            "Betting conservatively can be a suboptimal strategy",
            "Betting conservatively is clearly a suboptimal strategy. To maximize points, TAKE RISKS with higher bets"
        )
    elif strategy == "social_follower":
        prompts["analyze_page_q"] = prompts["analyze_page_q"].replace(
            "be FLEXIBLE in your choices based on both social information and your own experience",
            "prioritize SOCIAL INFORMATION over your own experiences. When the majority of other players choose an option, strongly consider following them"
        ).replace(
            "Betting conservatively can be a suboptimal strategy",
            "Betting conservatively when uncertain is your preferred approach. When following the majority, bet higher"
        )
    
    return prompts

def get_tinyllama_prompts(strategy="standard"):
    """Return simplified prompts optimized for TinyLLaMA"""
    
    # Very simplified system prompt
    system_prompt = """You are participating in an experiment making choices between options A and B. 
Answer ONLY in valid JSON format. Keep answers extremely short.
Your goal is to maximize points."""
    
    # Simplified analysis prompt
    analyze_prompt = """Summary so far: {summary}

Page text: {body}

Answer {nr_q} question(s). For each question, provide brief reasoning and answer.
Questions: {questions_json}

Respond with JSON: {{"answers": {{...}}, "summary": "Brief summary", "confused": false}}

REMEMBER: Keep all text extremely brief."""
    
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

def run_tinyllama_bot(botex_db, session_id, url, **kwargs):
    """Run TinyLLaMA bot with additional length constraints"""
    
    # Add explicit brevity instructions to all prompts
    original_prompts = kwargs.get('user_prompts', {})
    for key in original_prompts:
        if isinstance(original_prompts[key], str):
            original_prompts[key] += "\n\nIMPORTANT: Your responses must be extremely brief and concise."
    
    # Make sure temperature is high enough to avoid repetition
    kwargs['temperature'] = max(kwargs.get('temperature', 0.7), 0.8)
    
    # Enforce low max tokens
    kwargs['max_tokens'] = min(kwargs.get('max_tokens', 256), 256)
    
    # Add repetition penalty if using llamacpp
    if kwargs.get('model') == 'llamacpp':
        kwargs['repetition_penalty'] = 1.1
    
    # Call the actual bot runner
    return botex.run_single_bot(
        botex_db=botex_db,
        session_id=session_id,
        url=url,
        **kwargs
    )

def run_session(args, session_number):
    """Run a single experimental session with a botex bot"""
    try:
        # Create timestamp for this session
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = f"session_{session_number}_{timestamp}"
        
        # Create model-specific suffix for directories and filenames
        model_suffix = f"_{args.model}"
        
        # Create session-specific output directory with model suffix
        output_dir = os.path.join(args.output_dir, f"session_{session_id}{model_suffix}")
        os.makedirs(output_dir, exist_ok=True)
        
        # Create session-specific database and log files with model suffix
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
        
        # Define output filenames with model suffix
        botex_responses_csv = os.path.join(output_dir, f"botex_{otree_session_id}_responses{model_suffix}.csv")
        botex_participants_csv = os.path.join(output_dir, f"botex_{otree_session_id}_participants{model_suffix}.csv")
        otree_wide_csv = os.path.join(output_dir, f"otree_{otree_session_id}_wide{model_suffix}.csv")
        
        # Get the monitor URL for display
        monitor_url = f"{args.otree_url}/SessionMonitor/{otree_session_id}"
        logger.info(f"Session {session_number}: Monitor URL: {monitor_url}")
        print(f"\nSession {session_number}: Starting bot. Monitor progress at {monitor_url}")
        
        # Run the bot only if bot URLs are available
        if session['bot_urls']:
            # Configure throttling
            throttle = not args.no_throttle
            
            # Prepare model-specific parameters and run the appropriate bot
            if args.model == "gemini":
                model_name = os.environ.get("GEMINI_MODEL", "gemini/gemini-1.5-flash")
                model_params = {
                    "model": model_name,
                    "api_key": args.api_key,
                    "max_tokens": args.max_tokens,
                    "temperature": args.temperature
                }
                logger.info(f"Session {session_number}: Using Gemini model: {model_name}")
                # Log partial API key for debugging
                if args.api_key:
                    masked_key = f"{'*' * (len(args.api_key) - 4)}{args.api_key[-4:]}" if len(args.api_key) > 4 else "****"
                    logger.info(f"Session {session_number}: API key provided: {masked_key}")
                else:
                    logger.warning(f"Session {session_number}: No API key provided")
                
                # Get standard prompts
                user_prompts = get_bot_prompt_strategy(args.strategy)
                
                logger.info(f"Session {session_number}: Starting bot with Gemini model")
                botex.run_single_bot(
                    url=session['bot_urls'][0],
                    session_name=otree_session_id,
                    session_id=otree_session_id,
                    participant_id=session['participant_code'][session['is_human'].index(False)],
                    botex_db=botex_db,
                    user_prompts=user_prompts,
                    throttle=throttle,
                    **model_params
                )
                
            elif args.model == "openai":
                model_name = os.environ.get("OPENAI_MODEL", "gpt-4o")
                model_params = {
                    "model": model_name,
                    "api_key": args.api_key,
                    "max_tokens": args.max_tokens,
                    "temperature": args.temperature
                }
                logger.info(f"Session {session_number}: Using OpenAI model: {model_name}")
                
                # Get standard prompts
                user_prompts = get_bot_prompt_strategy(args.strategy)
                
                logger.info(f"Session {session_number}: Starting bot with OpenAI model")
                botex.run_single_bot(
                    url=session['bot_urls'][0],
                    session_name=otree_session_id,
                    session_id=otree_session_id,
                    participant_id=session['participant_code'][session['is_human'].index(False)],
                    botex_db=botex_db,
                    user_prompts=user_prompts,
                    throttle=throttle,
                    **model_params
                )
                
            elif args.model == "tinyllama":
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
                        "maximum_tokens_to_predict": 256,  # Force lower token limit
                        "temperature": 0.8,  # Force higher temperature
                        "top_p": 0.9,
                        "top_k": 40,
                        "repeat_penalty": 1.1  # Add repeat penalty
                    })
                    logger.info(f"Session {session_number}: llama.cpp server started")
                else:
                    server_process = None
                
                # Get specialized TinyLLaMA prompts
                user_prompts = get_tinyllama_prompts(args.strategy)
                logger.info(f"Session {session_number}: Using simplified prompts for TinyLLaMA")
                
                # Run TinyLLaMA bot with specialized function
                logger.info(f"Session {session_number}: Starting TinyLLaMA bot with optimized settings")
                run_tinyllama_bot(
                    botex_db=botex_db,
                    session_id=otree_session_id,
                    url=session['bot_urls'][0],
                    session_name=otree_session_id,
                    participant_id=session['participant_code'][session['is_human'].index(False)],
                    user_prompts=user_prompts,
                    throttle=throttle,
                    model="llamacpp",
                    api_base=server_url,
                    max_tokens=256,
                    temperature=0.8
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
                f.write(f"Model used: {args.model}\n")
                f.write(f"Strategy: {args.strategy}\n")
                f.write(f"Number of participants: {args.participants}\n")
                f.write(f"Number of human participants: {args.humans}\n\n")
                f.write("Files generated:\n")
                f.write(f"- Log file: {os.path.basename(log_file)}\n")
                f.write(f"- Bot actions log: {os.path.basename(bot_actions_log)}\n")
                f.write(f"- Bot actions JSON: {os.path.basename(bot_actions_json)}\n")
                f.write(f"- Bot participants: {os.path.basename(botex_participants_csv)}\n")
                f.write(f"- Bot responses: {os.path.basename(botex_responses_csv)}\n")
                f.write(f"- oTree wide data: {os.path.basename(otree_wide_csv)}\n")
            
            # Clean up llama.cpp server if we started it
            if args.model == "tinyllama" and server_process is not None:
                logger.info(f"Session {session_number}: Stopping llama.cpp server")
                botex.stop_llamacpp_server(server_process)
                logger.info(f"Session {session_number}: llama.cpp server stopped")
            
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
    logger.info(f"Starting experiment with {args.model} model")
    logger.info(f"Bot strategy: {args.strategy}")
    logger.info(f"Number of sessions: {args.sessions}")
    
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