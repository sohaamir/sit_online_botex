# custom_bot_runner.py - Improved version
import logging
import threading
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
import botex

logger = logging.getLogger("custom_botex")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

def run_bots_on_session_with_wait_handling(session_id, bot_urls=None, botex_db=None, model="gpt-4o-2024-08-06", 
                                          api_key=None, **kwargs):
    """Run multiple bots concurrently with proper wait page handling"""
    
    logger.info(f"Starting custom multi-bot runner for session {session_id}")
    
    # Extract user_prompts or initialize empty dict
    user_prompts = kwargs.get('user_prompts', {})
    
    # Enhance the prompts to better handle wait pages
    wait_page_prompt = """
    This is your summary of the survey/experiment so far: \n\n {summary} \n\n 
    You have now proceeded to the next page. This is the body text of the web page:\n\n{body}\n\n
    
    I need you to update the summary. IMPORTANT: If this appears to be a wait page 
    (contains text like "waiting for other players", "please wait", etc.), just mention
    that in your summary. This is normal and expected in multiplayer experiments. The system
    will handle the waiting, and you'll be automatically moved to the next page when all
    players are ready.
    
    Provide the summary as the string variable 'summary' in a JSON string. 
    Try to be very precise and detailed. A correct answer would have the form: 
    {{"summary": "Your summary", "confused": "set to `true` if you are confused by any part of the instructions, otherwise set it to `false`"}}
    """
    
    # Update the analyze_page_no_q prompt
    user_prompts['analyze_page_no_q'] = wait_page_prompt
    
    # Also add a special prompt for when there are no questions but there is a next button
    user_prompts['analyze_page_no_q_full_hist'] = wait_page_prompt
    
    # Add enhancement to kwargs
    kwargs['user_prompts'] = user_prompts
    
    # Start monitor threads for all bot URLs
    monitor_threads = []
    for url in bot_urls:
        participant_id = url.split('/')[-1]
        thread = threading.Thread(
            target=wait_page_monitor,
            args=(url, participant_id),
            daemon=True
        )
        thread.start()
        monitor_threads.append(thread)
    
    try:
        # Run the bots using botex's function
        result = botex.run_bots_on_session(
            session_id=session_id,
            bot_urls=bot_urls,
            botex_db=botex_db,
            model=model,
            api_key=api_key,
            **kwargs
        )
        logger.info(f"All bots for session {session_id} completed successfully")
        return result
    finally:
        # Give monitor threads a chance to finish
        for thread in monitor_threads:
            thread.join(timeout=5)

def wait_page_monitor(url, participant_id):
    """Monitor wait pages and help handle them"""
    try:
        # Set up headless Chrome
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--log-level=3")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        driver = webdriver.Chrome(options=options)
        
        # Initialize tracking variables
        check_count = 0
        max_checks = 120  # Maximum number of checks (10 minutes at 5 seconds per check)
        is_on_wait_page = False
        
        logger.info(f"Starting wait page monitor for participant {participant_id}")
        
        while check_count < max_checks:
            try:
                # Navigate to the URL
                driver.get(url)
                
                # Check if the page is a wait page
                body_text = driver.find_element(By.TAG_NAME, 'body').text.lower()
                
                is_wait_page = (
                    'waiting' in body_text 
                    or 'please wait' in body_text
                    or 'otree-wait-page' in driver.page_source
                )
                
                if is_wait_page:
                    if not is_on_wait_page or check_count % 10 == 0:
                        logger.info(f"Participant {participant_id} on wait page, poll #{check_count}")
                    is_on_wait_page = True
                    
                    # Special handling for wait pages
                    try:
                        # Try clicking any 'next' buttons if they exist (sometimes hidden)
                        next_buttons = driver.find_elements(By.CLASS_NAME, 'otree-btn-next')
                        if next_buttons and len(next_buttons) > 0:
                            logger.info(f"Found next button on wait page, attempting to click")
                            try:
                                driver.execute_script("arguments[0].click();", next_buttons[0])
                                logger.info(f"Clicked next button on wait page")
                                time.sleep(2)
                                continue
                            except:
                                pass
                    except:
                        pass
                    
                    # Refresh the page to help with potential issues
                    if check_count % 4 == 0:  # Every 20 seconds
                        logger.info(f"Refreshing wait page for participant {participant_id}")
                        driver.refresh()
                    
                    time.sleep(5)
                    check_count += 1
                else:
                    # If previously on a wait page, log that we're now on a regular page
                    if is_on_wait_page:
                        logger.info(f"Participant {participant_id} moved from wait page to regular page")
                    is_on_wait_page = False
                    
                    # Not a wait page, end the monitor
                    time.sleep(20)  # Check again in 20 seconds in case we go back to a wait page
                    
            except Exception as page_e:
                logger.warning(f"Error checking page for {participant_id}: {str(page_e)}")
                time.sleep(5)
                
    except Exception as e:
        logger.error(f"Error in wait page monitor for {participant_id}: {str(e)}")
    finally:
        try:
            driver.quit()
        except:
            pass
        logger.info(f"Wait page monitor for {participant_id} ended")