#!/usr/bin/env python3
"""
experiment.py - Social influence task experiment execution

This module contains all the logic for running individual experimental sessions,
configuring bots, managing prompts, and exporting data.
"""

from prompts import *
import datetime
import logging
import os
import platform
import subprocess
import time
import webbrowser
import csv
import requests
import botex
import litellm
import sqlite3
import json
import pandas as pd


logger = logging.getLogger("sit_botex")


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
    
    additional_params['repetition_penalty'] = 1.1
    
    return modified_prompts, additional_params


def remove_redundant_otree_builtin_fields(csv_file_path):
    """
    Remove redundant built-in oTree fields that don't change across rounds.
    Keeps payoff (which should vary) but removes redundant id_in_group and role.
    """
    try:
        # Read the wide CSV
        df = pd.read_csv(csv_file_path)
        
        # Identify built-in oTree fields that are round-invariant
        builtin_fields_to_check = ['id_in_group', 'role']  # Don't include payoff - it should vary
        
        columns_to_remove = []
        columns_to_rename = {}
        
        for field in builtin_fields_to_check:
            # Find all columns for this field across rounds
            field_columns = [col for col in df.columns if col.endswith(f'.player.{field}')]
            
            if len(field_columns) > 1:
                # Check if all columns have identical values
                first_col = field_columns[0]
                is_invariant = True
                
                for participant_row in range(len(df)):
                    first_value = df.loc[participant_row, first_col]
                    
                    for col_name in field_columns[1:]:
                        if df.loc[participant_row, col_name] != first_value:
                            # Handle NaN comparisons
                            if not (pd.isna(first_value) and pd.isna(df.loc[participant_row, col_name])):
                                is_invariant = False
                                break
                    
                    if not is_invariant:
                        break
                
                if is_invariant:
                    # Keep only the first column, rename it to remove round number
                    new_name = f"task.player.{field}"  # Remove round number
                    columns_to_rename[first_col] = new_name
                    columns_to_remove.extend(field_columns[1:])  # Remove the rest
        
        # Remove redundant columns
        if columns_to_remove:
            df_clean = df.drop(columns=columns_to_remove)
            
            # Rename the kept columns
            if columns_to_rename:
                df_clean.rename(columns=columns_to_rename, inplace=True)
            
            # Save the cleaned CSV
            df_clean.to_csv(csv_file_path, index=False)
            
            logger.info(f"Removed {len(columns_to_remove)} redundant built-in oTree columns")
            logger.debug(f"Removed columns: {columns_to_remove}")
        else:
            logger.info("No redundant built-in oTree columns found")
            
    except Exception as e:
        logger.warning(f"Error removing redundant built-in fields: {str(e)}. Keeping original CSV.")


def export_response_data(csv_file, botex_db, session_id):
    """Export botex response data with proper round tracking"""
    try:
        # Connect to botex database
        conn = sqlite3.connect(botex_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get conversations for this session
        cursor.execute("SELECT * FROM conversations")
        conversations = [dict(row) for row in cursor.fetchall()]
        
        # Filter by session_id if provided
        if session_id:
            conversations = [
                c for c in conversations 
                if json.loads(c['bot_parms'])['session_id'] == session_id
            ]
        
        enhanced_responses = []
        
        for conversation in conversations:
            try:
                bot_parms = json.loads(conversation['bot_parms'])
                participant_id = conversation['id']
                
                # Parse the conversation messages
                messages = json.loads(conversation['conversation'])
                
                # Track the current round based on the conversation flow
                current_round = 1
                questions_in_current_round = 0
                
                for i, message in enumerate(messages):
                    if message.get('role') == 'user':
                        # This is a prompt to the bot - check if it mentions a round
                        prompt_content = message.get('content', '')
                        
                        # Look for round indicators in the prompt
                        import re
                        round_match = re.search(r'Round (\d+)', prompt_content)
                        if round_match:
                            detected_round = int(round_match.group(1))
                            current_round = detected_round
                    
                    elif message.get('role') == 'assistant':
                        # This is a bot response
                        try:
                            response_data = json.loads(message.get('content', '{}'))
                            
                            # Extract summary and answers
                            summary = response_data.get('summary', '')
                            answers = response_data.get('answers', {})
                            
                            # Get the corresponding user prompt
                            prompt_content = ""
                            if i > 0 and messages[i-1].get('role') == 'user':
                                prompt_content = messages[i-1].get('content', '')
                            
                            for question_id, answer_data in answers.items():
                                if question_id == 'round':
                                    continue
                                
                                enhanced_responses.append({
                                    'session_id': bot_parms.get('session_id', ''),
                                    'participant_id': participant_id,
                                    'round': current_round,
                                    'question_id': question_id,
                                    'answer': answer_data.get('answer', ''),
                                    'reason': answer_data.get('reason', ''),
                                    'summary': summary,
                                    'prompt': prompt_content
                                })
                                
                                questions_in_current_round += 1
                            
                            # If we've answered questions in this exchange, 
                            # check if we should increment the round for next time
                            if len(answers) > 0:
                                # Heuristic: if we see 4+ questions answered, we might be moving to next round
                                # This is approximate - the round detection from prompts is more reliable
                                pass
                        
                        except json.JSONDecodeError:
                            continue
                            
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Error processing conversation {conversation.get('id', 'unknown')}: {str(e)}")
                continue
        
        # Sort responses by round, participant, and question
        enhanced_responses.sort(key=lambda x: (int(x['round']), x['participant_id'], x['question_id']))
        
        # Write to CSV
        fieldnames = ['session_id', 'participant_id', 'round', 'question_id', 'answer', 'reason', 'summary', 'prompt']
        
        if enhanced_responses:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(enhanced_responses)
            logger.info(f"Successfully wrote {len(enhanced_responses)} enhanced responses to {csv_file}")
        else:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
            logger.warning(f"No enhanced responses found for session {session_id}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error in export_response_data: {str(e)}")
        
        # Fallback to standard botex export
        try:
            botex.export_response_data(csv_file, botex_db=botex_db, session_id=session_id)
            logger.info(f"Used standard botex export as fallback")
        except Exception as e2:
            logger.warning(f"Both custom and standard export failed: {str(e2)}")
            # Create empty file with headers
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()


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


def log_actual_model_used():
    """
    Simple wrapper to log what model is actually being used in API calls.
    Also logs when models fail or are unavailable.
    """
    import litellm
    
    # Store original completion function
    original_completion = litellm.completion
    
    def logged_completion(*args, **kwargs):
        model_requested = kwargs.get('model', 'unknown')
        
        try:
            # Make the API call
            response = original_completion(*args, **kwargs)
            
            # Log what model was actually used (success case)
            actual_model = getattr(response, 'model', model_requested)
            logger.info(f"🤖 ACTUAL MODEL USED: {actual_model} (requested: {model_requested})")
            
            return response
            
        except Exception as e:
            # Log when model fails or is unavailable
            logger.error(f"❌ MODEL NOT AVAILABLE: {model_requested} - Error: {str(e)}")
            
            # Re-raise the exception so normal error handling continues
            raise e
    
    # Replace the completion function
    litellm.completion = logged_completion


def run_session(args, session_number, player_models, player_q_roles, player_t_roles, is_human_list, available_models):
    """Run a single experimental session using standard botex workflow"""
    try:

        # Enable simple model logging
        log_actual_model_used()

        # Create timestamp for this session
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = f"session_{session_number}_{timestamp}"
        
        # Calculate derived values
        n_humans_actual = sum(1 for is_human in is_human_list if is_human)
        n_bots = args.participants - n_humans_actual
        
        # Create simplified model suffix (without roles)
        if player_models and n_bots > 0:
            model_suffix = f"_mixed_nhumans{n_humans_actual}_nbots{n_bots}"
        elif n_bots > 0:
            model_suffix = f"_bots_nhumans{n_humans_actual}_nbots{n_bots}"
        else:
            model_suffix = f"_humans_only_nhumans{n_humans_actual}"
        
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
                
                # Add q_role if assigned
                if player_id in player_q_roles:
                    initial_session_config_fields[f'player_{player_id}_q_role'] = player_q_roles[player_id]
                
                # Add t_role if assigned
                if player_id in player_t_roles:
                    initial_session_config_fields[f'player_{player_id}_t_role'] = player_t_roles[player_id]
                
                # If this player is explicitly a bot, store the bot assignment
                if is_human_list and player_id <= len(is_human_list) and not is_human_list[player_id - 1]:
                    initial_session_config_fields[f'bot_position_{player_id}_model'] = model_name

        # Initialize session with explicit assignment
        session = botex.init_otree_session(
            config_name=args.session_config,
            npart=args.participants,
            is_human=is_human_list,  # Use explicit assignment
            botex_db=botex_db,
            otree_server_url=args.otree_url,
            otree_rest_key=getattr(args, 'otree_rest_key', None),
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

        # Get the monitor URL and open browser
        monitor_url = f"{args.otree_url}/SessionMonitor/{otree_session_id}"
        logger.info(f"Session {session_number}: Monitor URL: {monitor_url}")
        
        # Display session info
        if session['human_urls']:
            print(f"\nSession {session_number}: Human participant URLs:")
            for i, url in enumerate(session['human_urls'], 1):
                print(f"  Participant {i}: {url}")
        
        if session['bot_urls']:
            # Create role summary
            role_summary = []
            if player_q_roles:
                q_roles_used = set(player_q_roles.values())
                role_summary.append(f"q-roles: {', '.join(sorted(q_roles_used))}")
            if player_t_roles:
                t_roles_used = set(player_t_roles.values())
                role_summary.append(f"t-roles: {', '.join(sorted(t_roles_used))}")
            
            role_text = f" ({'; '.join(role_summary)})" if role_summary else ""
            
            if player_models:
                print(f"\nSession {session_number}: Starting {len(session['bot_urls'])} bots with player-specific models{role_text}")
            else:
                print(f"\nSession {session_number}: Starting {len(session['bot_urls'])} bots{role_text}")
        
        if n_bots == 0:
            print(f"\nSession {session_number}: All {args.participants} participants are human")
        
        print(f"Monitor progress at: {monitor_url}")
        
        # Automatically open Chrome with the monitor URL (unless disabled)
        if not getattr(args, 'no_browser', False):
            open_chrome_browser(monitor_url)
        
        # Run bots if there are any
        if session['bot_urls']:
            logger.info(f"Session {session_number}: Running bots with player-specific models")
            
            # Start llama.cpp server if any local models are used
            use_local_model = any(available_models[player_models[player_id]]['provider'] == 'local' 
                                  for player_id in range(1, args.participants + 1) 
                                  if player_id in player_models and not session['is_human'][player_id - 1])
            
            server_process = None
            if use_local_model:
                logger.info(f"Session {session_number}: Starting llama.cpp server for local models")
                server_url = getattr(args, 'server_url', None) or "http://localhost:8080"
                
                try:
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
                    
                    # Check if the player has a model assigned
                    if player_id in player_models:
                        model_name = player_models[player_id]
                        model_info = available_models[model_name]
                        
                        # Get role assignments for this player
                        q_role = player_q_roles.get(player_id, None)
                        t_role = player_t_roles.get(player_id, None)
                        
                        # Log bot assignment attempt
                        logger.info(f"🔄 ATTEMPTING TO ASSIGN: Player {player_id} → {model_name} (q_role: {q_role}, t_role: {t_role})")
                        
                        try:
                            api_key = None
                            if model_info['api_key_env']:
                                api_key = os.environ.get(model_info['api_key_env'])
                            
                            if model_info['provider'] == 'local':
                                user_prompts = get_tinyllama_prompts(q_role, t_role)
                                modified_prompts, tinyllama_params = configure_tinyllama_params(args, user_prompts)
                                user_prompts = modified_prompts
                            else:
                                user_prompts = get_bot_prompts(q_role, t_role)
                            
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
                            
                            logger.info(f"✅ BOT STARTED: Player {player_id} with {model_name}")
                            
                        except Exception as e:
                            logger.error(f"❌ BOT ASSIGNMENT FAILED: Player {player_id} → {model_name} - Error: {str(e)}")
                            # Continue with other bots even if this one fails
            
            # Wait for all bots to finish
            for thread in bot_threads:
                thread.join()
            
            # Clean up llama.cpp server if we started it
            if server_process is not None:
                logger.info(f"Session {session_number}: Stopping llama.cpp server")
                botex.stop_llamacpp_server(server_process)
            
            logger.info(f"Session {session_number}: Bots completed")
        
        # Wait for human participants if there are any
        if session['human_urls']:
            logger.info(f"Session {session_number}: Waiting for {len(session['human_urls'])} human participants to complete")
            
            print(f"\nWaiting for {len(session['human_urls'])} human participants to complete the experiment...")
            print(f"You can monitor progress at: {monitor_url}")
            print(f"Press Ctrl+C to stop early and export current data.\n")
            
            try:
                # Wait for human participants to complete
                while True:
                    try:
                        time.sleep(20)  # Check every 20 seconds
                        
                        # Get session status from oTree
                        session_data = botex.call_otree_api(
                            requests.get, 'sessions', otree_session_id,
                            otree_server_url=args.otree_url, 
                            otree_rest_key=getattr(args, 'otree_rest_key', None)
                        )
                        
                        participants = session_data.get('participants', [])
                        
                        # Count completed participants (both human and bot)
                        completed_count = 0
                        human_completed = 0
                        bot_completed = 0
                        
                        for i, p in enumerate(participants):
                            participant_code = p.get('code', 'unknown')
                            finished_flag = p.get('finished', False)
                            current_page = p.get('_current_page_name', 'unknown')
                            current_app = p.get('_current_app_name', 'unknown')
                            
                            # Determine if this participant is human or bot
                            is_human_participant = session['is_human'][i] if i < len(session['is_human']) else True
                            
                            if finished_flag:
                                completed_count += 1
                                if is_human_participant:
                                    human_completed += 1
                                    logger.info(f"  {participant_code} (HUMAN): COMPLETED")
                                else:
                                    bot_completed += 1
                                    logger.info(f"  {participant_code} (BOT): COMPLETED")
                            else:
                                if is_human_participant:
                                    logger.info(f"  {participant_code} (HUMAN): IN PROGRESS ({current_app}.{current_page})")
                                else:
                                    logger.info(f"  {participant_code} (BOT): IN PROGRESS ({current_app}.{current_page})")
                        
                        logger.info(f"Session {session_number}: {completed_count}/{len(participants)} participants completed "
                                   f"({human_completed} humans, {bot_completed} bots)")
                        
                        # Only proceed when ALL participants have finished
                        if completed_count >= len(participants) and len(participants) > 0:
                            logger.info(f"Session {session_number}: All participants completed!")
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
                logger.error(f"Session {session_number}: Error while waiting for completion: {str(e)}")
                print(f"Error while waiting. Proceeding to data export...")
        else:
            # All participants were bots and have already completed
            logger.info(f"Session {session_number}: All bot participants have completed")
        
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

        # Normalize oTree data first
        try:
            botex.normalize_otree_data(
                otree_wide_csv,
                store_as_csv=True,
                data_exp_path=output_dir,
                exp_prefix=f"otree_{otree_session_id}{model_suffix}"
            )
            logger.info(f"Session {session_number}: oTree data normalized")
            
            # Then clean up the wide CSV
            remove_redundant_otree_builtin_fields(otree_wide_csv)  # ✅ AFTER NORMALIZATION
            logger.info(f"Session {session_number}: Redundant columns removed from wide CSV")
            
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
                export_response_data(
                    os.path.join(output_dir, f"botex_{otree_session_id}_responses{model_suffix}.csv"),
                    botex_db=botex_db,
                    session_id=otree_session_id
                )
                logger.info(f"Session {session_number}: Enhanced botex response data exported")
            except Exception as e:
                logger.warning(f"Session {session_number}: Error exporting enhanced botex responses: {str(e)}")
        
        # Create summary file
        summary_file = os.path.join(output_dir, f"experiment_summary_{otree_session_id}{model_suffix}.txt")
        with open(summary_file, 'w') as f:
            f.write(f"Social Influence Task Experiment Summary - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*70 + "\n\n")
            f.write(f"Session ID: {otree_session_id}\n")
            f.write(f"Session Number: {session_number}\n")
            f.write(f"Participants: {args.participants} total ({n_humans_actual} human, {n_bots} bots)\n")

            # Write role summary if any roles are assigned
            if player_q_roles or player_t_roles:
                f.write("Role assignments:\n")
                if player_q_roles:
                    f.write(f"  Questionnaire roles: {dict(player_q_roles)}\n")
                if player_t_roles:
                    f.write(f"  Task roles: {dict(player_t_roles)}\n")
            f.write("\n")
            
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