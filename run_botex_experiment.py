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
import csv
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

def load_model_mapping(file_path, num_participants):
    """
    Load player-model mapping from a CSV file.
    
    Args:
        file_path (str): Path to the CSV file
        num_participants (int): Expected number of participants
        
    Returns:
        tuple: (player_models dict, is_human list) or (None, None) if file not found
    """
    if not os.path.exists(file_path):
        logger.info(f"No player model mapping file found at {file_path}")
        return None, None
        
    player_models = {}
    is_human_list = []
    
    try:
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                player_id = int(row['player_id'])
                model_name = row['model_name'].strip()
                
                # If model is "human", mark as human; otherwise it's a bot
                if model_name.lower() == "human":
                    player_models[player_id] = "human"
                    is_human_list.append((player_id, True))
                else:
                    player_models[player_id] = model_name
                    is_human_list.append((player_id, False))
        
        # Sort by player_id to ensure correct order
        is_human_list.sort(key=lambda x: x[0])
        
        # Create the final is_human boolean list
        is_human_boolean_list = [item[1] for item in is_human_list]
        
        # Fill in missing players with default behavior (human)
        while len(is_human_boolean_list) < num_participants:
            player_id = len(is_human_boolean_list) + 1
            player_models[player_id] = "human"
            is_human_boolean_list.append(True)
            logger.info(f"Player {player_id} not specified in mapping file, defaulting to human")
                
        return player_models, is_human_boolean_list
        
    except Exception as e:
        logger.error(f"Error loading model mapping: {str(e)}")
        return None, None

def get_available_models():
    """
    Get all available models from environment variables.
    
    Returns:
        dict: Dictionary mapping model names to their full model strings and provider
    """
    available_models = {}
    
    # Gemini models
    gemini_models_str = os.environ.get('GEMINI_MODELS', 'gemini-1.5-flash')  # Default fallback
    gemini_models = [m.strip() for m in gemini_models_str.split(',') if m.strip()]
    for model in gemini_models:
        model_name = model.strip()
        available_models[model_name] = {
            'full_name': f"gemini/{model_name}", 
            'provider': 'gemini',
            'api_key_env': 'GEMINI_API_KEY'
        }
    
    # OpenAI models
    openai_models_str = os.environ.get('OPENAI_MODELS', '')
    if openai_models_str:
        openai_models = [m.strip() for m in openai_models_str.split(',') if m.strip()]
        for model in openai_models:
            model_name = model.strip()
            available_models[model_name] = {
                'full_name': model_name,
                'provider': 'openai',
                'api_key_env': 'OPENAI_API_KEY'
            }
    
    # Anthropic models
    anthropic_models_str = os.environ.get('ANTHROPIC_MODELS', '')
    if anthropic_models_str:
        anthropic_models = [m.strip() for m in anthropic_models_str.split(',') if m.strip()]
        for model in anthropic_models:
            model_name = model.strip()
            available_models[model_name] = {
                'full_name': model_name,
                'provider': 'anthropic',
                'api_key_env': 'ANTHROPIC_API_KEY'
            }
    
    # Local models
    local_models_str = os.environ.get('LOCAL_LLM_MODELS', '')
    if local_models_str:
        local_models = [m.strip() for m in local_models_str.split(',') if m.strip()]
        for model in local_models:
            model_name = model.strip()
            available_models[model_name] = {
                'full_name': 'llamacpp',
                'provider': 'local',
                'api_key_env': None
            }
    
    return available_models

def validate_player_models(player_models, available_models, participants=None, humans=None):
    """
    Validate that all player models are available.
    
    Args:
        player_models (dict): Mapping of player IDs to model names
        available_models (dict): Available models
        participants (int): Total number of participants
        humans (int): Number of human participants
        
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check if all participants are human
    if humans is not None and participants is not None and humans == participants:
        logger.info(f"All {participants} participants are human - no model assignments needed")
        return True, None
    
    if not player_models:
        return True, None
        
    for player_id, model_name in player_models.items():
        # Skip validation for human participants
        if model_name.lower() == "human":
            continue
            
        if model_name not in available_models:
            return False, f"Player {player_id} is assigned model '{model_name}' which is not available in botex.env"
    
    # Enhanced validation when humans > 0
    if humans is not None and humans > 0 and participants is not None:
        # Count actual bots from the mapping
        bot_count = sum(1 for model in player_models.values() if model.lower() != "human")
        human_count = sum(1 for model in player_models.values() if model.lower() == "human")
        
        logger.info(f"From CSV mapping: {human_count} humans, {bot_count} bots")
        
        if len(player_models) < participants:
            logger.warning(f"Only {len(player_models)} models specified but {participants} participants expected.")
        
        if bot_count > 0:
            logger.info(f"Model assignments will apply to {bot_count} bot participants.")
    
    return True, None

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
    
    # Model mapping file
    parser.add_argument("--model-mapping", default="player_models.csv",
                        help="Path to CSV file mapping player IDs to models")
    
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
    
    # Questionnaire role configuration
    parser.add_argument("--q-role", default="none",
                    choices=["none", "typical", "patient"],
                    help="Role for questionnaire completion (typical: neurotypical individual, patient: individual with psychopathology, none: no specific role)")
    
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
    
    If you encounter questionnaire pages:
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
    
    If you encounter experimental task pages:
    - In the very first round, choose randomly between the two options (A) and (B). Do not arbitrarily choose option A over option B
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

def get_bot_prompts(q_role=None):
    """Create the complete prompt system with all components"""
    
    # Combine all instructions - but make questionnaire instructions optional
    general_instructions = get_general_instructions()
    task_instructions = get_task_instructions()
    
    # Create the system prompt, starting with just general and task instructions
    system_prompt = f"""{general_instructions}

{task_instructions}"""
    
    # Only add questionnaire instructions and role instructions if a role is specified
    if q_role in ["patient", "typical"]:
        questionnaire_instructions = get_questionnaire_instructions() 
        role_instructions = get_questionnaire_role_instructions(q_role)
        
        system_prompt += f"""

{questionnaire_instructions}

{role_instructions}"""
    
    # Add the final reminder
    system_prompt += """

Remember: Always analyze each page carefully and respond in valid JSON format when requested."""

    # Create the page analysis prompt - modify to conditionally include questionnaire guidance
    analyze_prompt = """Perfect. This is your summary of the study so far: 

{summary} 

You have now proceeded to the next page. This is the body text of the web page: 

{body} 

I need you to answer {nr_q} question(s) and update your summary.

RESPONSE FORMATTING:
For each question, provide:
- 'reason': Your reasoning or thought process leading to your response
- 'answer': Your final answer to the question
"""

    # Only add questionnaire-specific instructions if a role is specified
    if q_role in ["patient", "typical"]:
        analyze_prompt += """
QUESTIONNAIRE RESPONSES:
- Answer according to your assigned psychological role and profile
- Be consistent with your established character throughout
- Provide brief reasoning that explains your perspective
"""

    # Always include task responses guidance
    analyze_prompt += """
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
    """Run a single experimental session using standard botex workflow"""
    try:
        # Import botex here to ensure environment variables are loaded first
        import botex
        
        # Create timestamp for this session
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = f"session_{session_number}_{timestamp}"
        
        # Load available models and player model mappings
        available_models = get_available_models()
        player_models = None
        is_human_list = None
        
        if os.path.exists(args.model_mapping):
            player_models, is_human_list = load_model_mapping(args.model_mapping, args.participants)
            if player_models:
                # Calculate actual humans and bots from explicit assignment
                if is_human_list:
                    n_humans_actual = sum(1 for is_human in is_human_list if is_human)
                    n_bots = sum(1 for is_human in is_human_list if not is_human)
                    logger.info(f"Session {session_number}: Explicit assignment - {n_humans_actual} humans, {n_bots} bots")
                else:
                    n_humans_actual = args.humans
                    n_bots = args.participants - args.humans
                
                is_valid, error_msg = validate_player_models(
                    player_models, available_models, args.participants, n_humans_actual
                )
                if not is_valid:
                    return {"success": False, "error": error_msg}
        else:
            # No explicit mapping, use command line arguments
            n_bots = args.participants - args.humans
            n_humans_actual = args.humans
        
        # Create simplified model suffix
        if player_models and n_bots > 0:
            model_suffix = f"_mixed_nhumans{n_humans_actual}_nbots{n_bots}_qrole{args.q_role}"
        elif n_bots > 0:
            model_suffix = f"_{args.model}_nhumans{n_humans_actual}_nbots{n_bots}_qrole{args.q_role}"
        else:
            model_suffix = f"_humans_only_nhumans{n_humans_actual}_qrole{args.q_role}"
        
        # Create session-specific output directory
        output_dir = os.path.join(args.output_dir, f"session_{session_id}{model_suffix}")
        os.makedirs(output_dir, exist_ok=True)
        
        # Create session-specific database file
        botex_db = os.path.join(output_dir, f"botex_{session_id}{model_suffix}.sqlite3")
        
        logger.info(f"Session {session_number}: Output directory: {output_dir}")
        
        # Pre-calculate model assignments
        initial_session_config_fields = {}

        if player_models:
            for player_id, model_name in player_models.items():
                initial_session_config_fields[f'player_{player_id}_intended_model'] = model_name
                
                # If this player is explicitly a bot, store the bot assignment
                if is_human_list and player_id <= len(is_human_list) and not is_human_list[player_id - 1]:
                    initial_session_config_fields[f'bot_position_{player_id}_model'] = model_name
            
            # Fallback: If no explicit assignment, assume last positions are bots
            if not is_human_list:
                bot_positions = list(range(args.humans + 1, args.participants + 1))
                for bot_position in bot_positions:
                    if bot_position in player_models:
                        initial_session_config_fields[f'bot_position_{bot_position}_model'] = player_models[bot_position]

        # Initialize session with explicit assignment
        if is_human_list:
            session = botex.init_otree_session(
                config_name=args.session_config,
                npart=args.participants,
                is_human=is_human_list,  # Use explicit assignment
                botex_db=botex_db,
                otree_server_url=args.otree_url,
                otree_rest_key=args.otree_rest_key,
                modified_session_config_fields=initial_session_config_fields
            )

        # Get the session ID
        otree_session_id = session['session_id']
        logger.info(f"Session {session_number}: Initialized oTree session with ID: {otree_session_id}")

        # Log the explicit assignments for verification
        if player_models:
            for i, is_human in enumerate(session['is_human']):
                player_position = i + 1
                participant_code = session['participant_code'][i]
                if is_human:
                    logger.info(f"Session {session_number}: Player {player_position} (participant {participant_code}) -> HUMAN")
                else:
                    if player_position in player_models:
                        assigned_model = player_models[player_position]
                        logger.info(f"Session {session_number}: Player {player_position} (participant {participant_code}) -> {assigned_model}")

        # Log the actual bot assignments for verification
        if player_models and session['bot_urls']:
            for i, is_human in enumerate(session['is_human']):
                if not is_human:
                    participant_code = session['participant_code'][i]
                    player_position = i + 1
                    if player_position in player_models:
                        assigned_model = player_models[player_position]
                        logger.info(f"Session {session_number}: Bot participant {participant_code} (position {player_position}) -> {assigned_model}")

        # Get the monitor URL and open browser
        monitor_url = f"{args.otree_url}/SessionMonitor/{otree_session_id}"
        logger.info(f"Session {session_number}: Monitor URL: {monitor_url}")
        
        # Display session info
        if session['human_urls']:
            print(f"\nSession {session_number}: Human participant URLs:")
            for i, url in enumerate(session['human_urls'], 1):
                print(f"  Participant {i}: {url}")
        
        if session['bot_urls']:
            if player_models:
                print(f"\nSession {session_number}: Starting {len(session['bot_urls'])} bots with player-specific models (q-role: {args.q_role})")
            else:
                print(f"\nSession {session_number}: Starting {len(session['bot_urls'])} bots with {args.model_string} (q-role: {args.q_role})")
        
        if n_bots == 0:
            print(f"\nSession {session_number}: All {args.participants} participants are human")
        
        print(f"Monitor progress at: {monitor_url}")
        
        # Automatically open Chrome with the monitor URL
        open_chrome_browser(monitor_url)
        
        # Run bots if there are any
        if session['bot_urls']:
            # Check if we're using player-specific models
            if player_models:
                logger.info(f"Session {session_number}: Running bots with player-specific models")
                
                # Start llama.cpp server if any local models are used
                use_local_model = any(available_models[player_models[player_id]]['provider'] == 'local' 
                                      for player_id in range(1, args.participants + 1) 
                                      if player_id in player_models and not session['is_human'][player_id - 1])
                
                server_process = None
                if use_local_model:
                    logger.info(f"Session {session_number}: Starting llama.cpp server for local models")
                    server_url = args.server_url or "http://localhost:8080"
                    
                    try:
                        import requests
                        response = requests.get(f"{server_url}/health", timeout=5)
                        if response.status_code != 200:
                            raise Exception("Server not running")
                        logger.info(f"Session {session_number}: llama.cpp server already running at {server_url}")
                    except:
                        server_process = botex.start_llamacpp_server({
                            "server_path": args.server_path,
                            "local_llm_path": args.model_path,
                            "server_url": server_url,
                            "maximum_tokens_to_predict": args.max_tokens,
                            "temperature": args.temperature,
                        })
                        logger.info(f"Session {session_number}: llama.cpp server started")
                
                # Run bots individually with assigned models
                bot_threads = []
                bot_idx = 0
                
                for i, is_human in enumerate(session['is_human']):
                    if not is_human:
                        player_id = i + 1
                        url = session['bot_urls'][bot_idx]
                        bot_idx += 1
                        
                        if player_id in player_models:
                            model_name = player_models[player_id]
                            model_info = available_models[model_name]
                            
                            api_key = None
                            if model_info['api_key_env']:
                                api_key = os.environ.get(model_info['api_key_env'])
                            
                            if model_info['provider'] == 'local':
                                user_prompts = get_tinyllama_prompts(args.q_role if args.q_role != "none" else None)
                                modified_prompts, tinyllama_params = configure_tinyllama_params(args, user_prompts)
                                user_prompts = modified_prompts
                            else:
                                user_prompts = get_bot_prompts(args.q_role if args.q_role != "none" else None)
                            
                            logger.info(f"Session {session_number}: Player {player_id} using {model_name} ({model_info['provider']})")
                            
                            thread = botex.run_single_bot(
                                url=url,
                                session_id=otree_session_id,
                                participant_id=f"P{player_id}",
                                botex_db=botex_db,
                                model=model_info['full_name'],
                                api_key=api_key,
                                user_prompts=user_prompts,
                                temperature=args.temperature,
                                max_tokens=args.max_tokens,
                                throttle=not args.no_throttle,
                                wait=False
                            )
                            bot_threads.append(thread)
                            thread.start()
                
                # Wait for all bots to finish
                for thread in bot_threads:
                    thread.join()
                
                # Clean up llama.cpp server if we started it
                if server_process is not None:
                    logger.info(f"Session {session_number}: Stopping llama.cpp server")
                    botex.stop_llamacpp_server(server_process)
                
            else:
                # Use single model for all bots
                if args.model == "tinyllama":
                    server_url = args.server_url or "http://localhost:8080"
                    
                    try:
                        import requests
                        response = requests.get(f"{server_url}/health", timeout=5)
                        if response.status_code != 200:
                            raise Exception("Server not running")
                        logger.info(f"Session {session_number}: llama.cpp server already running")
                        server_process = None
                    except:
                        logger.info(f"Session {session_number}: Starting llama.cpp server...")
                        server_process = botex.start_llamacpp_server({
                            "server_path": args.server_path,
                            "local_llm_path": args.model_path,
                            "server_url": server_url,
                            "maximum_tokens_to_predict": args.max_tokens,
                            "temperature": args.temperature,
                        })
                        logger.info(f"Session {session_number}: llama.cpp server started")
                    
                    user_prompts = get_tinyllama_prompts(args.q_role if args.q_role != "none" else None)
                    modified_prompts, tinyllama_params = configure_tinyllama_params(args, user_prompts)

                    botex.run_bots_on_session(
                        session_id=otree_session_id,
                        botex_db=botex_db,
                        user_prompts=modified_prompts,
                        throttle=not args.no_throttle,
                        model="llamacpp",
                        api_base=server_url,
                        **tinyllama_params
                    )
                    
                    if server_process is not None:
                        logger.info(f"Session {session_number}: Stopping llama.cpp server")
                        botex.stop_llamacpp_server(server_process)
                else:
                    # API-based models
                    user_prompts = get_bot_prompts(args.q_role if args.q_role != "none" else None)
                    
                    botex.run_bots_on_session(
                        session_id=otree_session_id,
                        botex_db=botex_db,
                        model=args.model_string,
                        api_key=args.api_key,
                        user_prompts=user_prompts,
                        max_tokens=args.max_tokens,
                        temperature=args.temperature,
                        throttle=not args.no_throttle
                    )
            
            logger.info(f"Session {session_number}: Bots completed")
        else:
            # Human-only session - wait for completion
            logger.info(f"Session {session_number}: No bots to run - waiting for human participants to complete")
            
            print(f"\nWaiting for all {args.humans} human participants to complete the experiment...")
            print(f"You can monitor progress at: {monitor_url}")
            print(f"Press Ctrl+C to stop early and export current data.\n")
            
            try:
                import time
                import requests
                
                # Wait for human participants to complete
                while True:
                    try:
                        time.sleep(20)  # Check every 20 seconds
                        
                        # Get session status from oTree
                        session_data = botex.call_otree_api(
                            requests.get, 'sessions', otree_session_id,
                            otree_server_url=args.otree_url, 
                            otree_rest_key=args.otree_rest_key
                        )
                        
                        participants = session_data.get('participants', [])
                        total_participants = len(participants)
                        
                        # Only count participants with explicit finished=True flag
                        completed_count = 0
                        for p in participants:
                            participant_code = p.get('code', 'unknown')
                            finished_flag = p.get('finished', False)
                            current_page = p.get('_current_page_name', 'unknown')
                            current_app = p.get('_current_app_name', 'unknown')
                            
                            if finished_flag:
                                completed_count += 1
                                logger.info(f"  {participant_code}: COMPLETED")
                            else:
                                logger.info(f"  {participant_code}: IN PROGRESS ({current_app}.{current_page})")
                        
                        logger.info(f"Session {session_number}: {completed_count}/{total_participants} participants explicitly finished")
                        
                        # Only proceed when ALL participants have finished=True
                        if completed_count >= total_participants and total_participants > 0:
                            logger.info(f"Session {session_number}: All human participants completed!")
                            print(f"All participants have completed the experiment. Proceeding to data export...")
                            break
                            
                    except KeyboardInterrupt:
                        logger.info(f"Session {session_number}: Manual interruption - proceeding to data export")
                        print(f"Manual interruption. Exporting current data...")
                        break
                    except Exception as api_error:
                        logger.warning(f"Session {session_number}: Could not check session status: {str(api_error)}")
                        # Continue waiting
                        
            except Exception as e:
                logger.error(f"Session {session_number}: Error while waiting for human completion: {str(e)}")
                print(f"Error while waiting. Proceeding to data export...")
        
        # Export data using botex standard functions
        logger.info(f"Session {session_number}: Exporting data...")
        
        # Export oTree data
        otree_wide_csv = os.path.join(output_dir, f"otree_{otree_session_id}_wide{model_suffix}.csv")
        try:
            botex.export_otree_data(
                otree_wide_csv,
                server_url=args.otree_url,
                admin_name='admin',
                admin_password=os.environ.get('OTREE_ADMIN_PASSWORD')
            )
            logger.info(f"Session {session_number}: oTree data exported")
        except Exception as e:
            logger.error(f"Session {session_number}: Failed to export oTree data: {str(e)}")
        
        # Normalize oTree data
        try:
            botex.normalize_otree_data(
                otree_wide_csv, 
                store_as_csv=True,
                data_exp_path=output_dir,
                exp_prefix=f"otree_{otree_session_id}{model_suffix}"
            )
            logger.info(f"Session {session_number}: oTree data normalized")
        except Exception as e:
            logger.warning(f"Session {session_number}: Data normalization warning: {str(e)}")
        
        # Export botex data
        if n_bots > 0:
            try:
                botex.export_participant_data(
                    os.path.join(output_dir, f"botex_{otree_session_id}_participants{model_suffix}.csv"),
                    botex_db=botex_db,
                    session_id=otree_session_id
                )
                logger.info(f"Session {session_number}: Botex participant data exported")
            except Exception as e:
                logger.warning(f"Session {session_number}: Could not export botex participant data: {str(e)}")
            
            try:
                export_ordered_response_data(
                    os.path.join(output_dir, f"botex_{otree_session_id}_responses{model_suffix}.csv"),
                    botex_db=botex_db,
                    session_id=otree_session_id
                )
                logger.info(f"Session {session_number}: Botex response data exported")
            except Exception as e:
                logger.warning(f"Session {session_number}: Error exporting botex responses: {str(e)}")
        
        # Create summary file
        summary_file = os.path.join(output_dir, f"experiment_summary_{otree_session_id}{model_suffix}.txt")
        with open(summary_file, 'w') as f:
            f.write(f"Social Influence Task Experiment Summary - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*70 + "\n\n")
            f.write(f"Session ID: {otree_session_id}\n")
            f.write(f"Session Number: {session_number}\n")
            f.write(f"Participants: {args.participants} total ({args.humans} human, {n_bots} bots)\n")
            f.write(f"Questionnaire role: {args.q_role}\n\n")
            
            if session['human_urls']:
                f.write("Human participant URLs:\n")
                for i, url in enumerate(session['human_urls'], 1):
                    f.write(f"  Participant {i}: {url}\n")
            
            if player_models and n_bots > 0:
                f.write("\nBot model assignments:\n")
                bot_idx = 0
                for i, is_human in enumerate(session['is_human']):
                    if not is_human:
                        player_id = i + 1
                        if player_id in player_models:
                            model_name = player_models[player_id]
                            provider = available_models[model_name]['provider']
                            f.write(f"  Player {player_id}: {model_name} ({provider})\n")
                        bot_idx += 1
        
        logger.info(f"Session {session_number}: Session completed successfully")
        return {"success": True, "session_id": otree_session_id, "output_dir": output_dir}
    
    except Exception as e:
        logger.error(f"Session {session_number}: Error: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}

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
    
    # Load available models from environment
    available_models = get_available_models()
    logger.info(f"Available models: {list(available_models.keys())}")

    # If using player-specific models, load and validate the mapping
    player_models = None
    if os.path.exists(args.model_mapping):
        player_models, is_human_list = load_model_mapping(args.model_mapping, args.participants)
        is_valid, error_msg = validate_player_models(
            player_models, available_models, args.participants, args.humans
        )
        
        if not is_valid:
            logger.error(error_msg)
            print(f"\nERROR: {error_msg}")
            print("Please correct the model mapping file and try again.")
            sys.exit(1)
        
        # Print the models for each player
        if args.humans > 0:
            print(f"\nPlayer model assignments ({args.participants - args.humans} bots, {args.humans} humans):")
            print("Note: Model assignments for human participants will be ignored.")
        else:
            print(f"\nPlayer model assignments ({args.participants} bots):")
            
        for player_id in sorted(player_models.keys()):
            model_name = player_models[player_id]
            if model_name in available_models:
                provider = available_models[model_name]['provider']
                print(f"  Player {player_id}: {model_name} ({provider})")
    
    # Log the configuration
    if player_models:
        logger.info(f"Starting experiment with player-specific models")
    else:
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
    
    otree_process = botex.start_otree_server(project_path=".", timeout=15)
    logger.info(f"oTree server started at {args.otree_url}")
    
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
        # Stop oTree server using botex
        logger.info("Stopping oTree server...")
        botex.stop_otree_server(otree_process)
        logger.info("oTree server stopped")

if __name__ == "__main__":
    main()