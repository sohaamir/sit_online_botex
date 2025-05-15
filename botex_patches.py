"""
botex_patches.py - Custom patches for the botex package to handle common issues
"""
import logging
import time
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By

logger = logging.getLogger("botex_patches")

def apply_stale_element_fix(botex_module):
    """
    Apply a monkeypatch to fix stale element reference issues in botex
    
    Args:
        botex_module: The imported botex module to patch
    """
    # Store the original function
    original_click_on_element = botex_module.bot.click_on_element
    
    # Define a patched version with retry logic
    def click_on_element_with_retry(dr, element, timeout=3600, check_errors=False, max_retries=3):
        """Patched version of click_on_element with retry logic for stale elements"""
        for retry in range(max_retries):
            try:
                # Try the normal click
                return original_click_on_element(dr, element, timeout, check_errors)
            except StaleElementReferenceException:
                logger.warning(f"Stale element reference detected (attempt {retry+1}/{max_retries})")
                
                # If we've exhausted retries, give up
                if retry >= max_retries - 1:
                    logger.error("Maximum retries exceeded for stale element")
                    raise
                
                # Wait a moment before retrying
                time.sleep(2)
                
                # If it's a known element type, try to refetch it
                try:
                    # Refresh the page and wait for it to load
                    dr.refresh()
                    logger.info("Page refreshed, waiting for it to load")
                    time.sleep(3)
                    
                    # Look for the most common button types
                    next_buttons = dr.find_elements(By.CLASS_NAME, 'otree-btn-next')
                    if next_buttons:
                        logger.info("Found new next button after refresh")
                        element = next_buttons[0]
                        continue
                    
                    # Handle wait pages specially
                    if "wait" in dr.page_source.lower() or "waiting" in dr.page_source.lower():
                        logger.info("Detected wait page, will retry later")
                        time.sleep(5)  # Wait longer on wait pages
                        continue
                        
                except Exception as e:
                    logger.warning(f"Error while trying to recover from stale element: {str(e)}")
            
            except TimeoutException:
                logger.warning(f"Timeout exception when clicking element (attempt {retry+1}/{max_retries})")
                # Similar recovery logic
                if retry >= max_retries - 1:
                    raise
                time.sleep(2)
    
    # Replace the original function with our patched version
    botex_module.bot.click_on_element = click_on_element_with_retry
    logger.info("Applied stale element fix to botex.bot.click_on_element")
    
    # Also patch the scan_page function to better handle wait pages
    original_scan_page = botex_module.bot.scan_page
    
    def scan_page_with_wait_handling(dr):
        """Patched version of scan_page with better wait page handling"""
        try:
            result = original_scan_page(dr)
            
            # Extra handling for wait pages
            if result[1]:  # If wait_page is True
                logger.info("Wait page detected, applying special handling")
                # Force refresh if the page has a refresh meta tag
                meta_refresh = dr.find_elements(By.CSS_SELECTOR, "meta[http-equiv='refresh']")
                if not meta_refresh:
                    # Add our own periodic refresh if none exists
                    dr.execute_script("""
                        setTimeout(function() {
                            window.location.reload();
                        }, 5000);
                    """)
                    logger.info("Added automatic refresh script to wait page")
            
            return result
        except Exception as e:
            logger.warning(f"Error in scan_page: {str(e)}")
            # Return default values that won't break the bot
            return ("Error loading page", True, None, None)
    
    # Replace scan_page with our patched version
    botex_module.bot.scan_page = scan_page_with_wait_handling
    logger.info("Applied wait page fix to botex.bot.scan_page")

def apply_all_patches(botex_module):
    """Apply all available patches to botex"""
    apply_stale_element_fix(botex_module)
    logger.info("All botex patches applied successfully")