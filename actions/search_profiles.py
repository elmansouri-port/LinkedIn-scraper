#action/search_connections.py
import time
import logging
import pandas as pd
import os
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from config.settings import GROUP_URL, MESSAGE, GROUP_ID
from utils.send_csv import *

def setup_logging(keywords):
    """Setup logging for the search process"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"data/logs/search_{keywords}_{timestamp}.log"
    
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_filename), exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()  # Also log to console
        ]
    )
    
    return logging.getLogger(__name__)

def url_builder(keywords, geoUrn="%5B%22105015875%22%5D", page=1, origin="GLOBAL_SEARCH_HEADER"):
    """Build LinkedIn search URL"""
    base_url = f"https://www.linkedin.com/search/results/people/?geoUrn={geoUrn}&keywords={keywords}&page={page}&origin={origin}"
    return base_url

def save_profiles_to_csv(profiles, keywords):
    """Save profiles to CSV file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"data/csv/search_{keywords}_{timestamp}.csv"
    
    # Create csv directory if it doesn't exist
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # Convert to DataFrame and save
    df = pd.DataFrame(profiles)
    df.to_csv(filename, index=False)
    
    return filename

def extract_profiles_from_page(driver, logger):
    """Extract profiles from current page"""
    profiles_on_page = []
    
    try:
        # Wait for search results to load
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul[role='list'] > li")))
        
        # Find all profile links
        profile_links = driver.find_elements(By.CSS_SELECTOR, "ul[role='list'] li a[href*='/in/']")
        logger.info(f"Found {len(profile_links)} profile links on current page")
        
        for i, a in enumerate(profile_links, 1):
            try:
                # Get only the span with aria-hidden="true"
                name_element = a.find_element(By.CSS_SELECTOR, 'span[aria-hidden="true"]')
                name = name_element.text.strip()
                
                if name:
                    profile_data = {
                        "name": name,
                        "link": a.get_attribute('href')
                    }
                    profiles_on_page.append(profile_data)
                    logger.info(f"Extracted profile {i}: {name}")
                else:
                    logger.warning(f"Empty name found for profile {i}")
                    
            except Exception as e:
                logger.warning(f"Failed to extract profile {i}: {str(e)}")
                continue
                
    except TimeoutException:
        logger.error("Timeout waiting for search results to load")
    except Exception as e:
        logger.error(f"Error extracting profiles from page: {str(e)}")
    
    return profiles_on_page

def is_next_button_disabled(driver, logger):
    """Check if the Next button is disabled (indicating no more pages)"""
    try:
        # Look for next button with various selectors
        next_button_selectors = [
            "button[aria-label='Next']",
            ".artdeco-pagination__button--next",
            "button.artdeco-pagination__button--next"
        ]
        
        for selector in next_button_selectors:
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, selector)
                
                # Check if button is disabled
                is_disabled = (
                    next_button.get_attribute('disabled') is not None or
                    'artdeco-button--disabled' in next_button.get_attribute('class') or
                    next_button.get_attribute('disabled') == 'true' or
                    next_button.get_attribute('disabled') == ''
                )
                
                if is_disabled:
                    logger.info("Next button found and is DISABLED - no more pages available")
                    return True
                else:
                    logger.info("Next button found and is ENABLED - more pages available")
                    return False
                    
            except NoSuchElementException:
                continue
        
        # If no next button found, assume no more pages
        logger.info("No next button found - assuming no more pages")
        return True
        
    except Exception as e:
        logger.error(f"Error checking next button status: {str(e)}")
        return True  # Assume no more pages on error

def search_connections(driver, keywords, profiles_number, start_page=1):
    """
    Enhanced search function that collects specified number of profiles
    """
    # Setup logging
    logger = setup_logging(keywords)
    
    profiles = []
    current_page = start_page
    max_pages = 100  # Safety limit to prevent infinite loops
    consecutive_empty_pages = 0  # Track consecutive pages with no results
    max_consecutive_empty = 3  # Max empty pages before giving up
    
    logger.info(f"Starting LinkedIn search for keyword: '{keywords}'")
    logger.info(f"Target profiles: {profiles_number}")
    logger.info(f"Starting from page: {start_page}")
    
    try:
        while len(profiles) < profiles_number and current_page <= max_pages:
            logger.info(f"\n--- Processing Page {current_page} ---")
            
            # Build URL for current page
            url = url_builder(keywords, page=current_page)
            logger.info(f"Navigating to: {url}")
            
            # Navigate to the page
            driver.get(url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Extract profiles from current page
            page_profiles = extract_profiles_from_page(driver, logger)
            
            if not page_profiles:
                consecutive_empty_pages += 1
                logger.warning(f"No profiles found on page {current_page} ({consecutive_empty_pages} consecutive empty pages)")
                
                # Check if Next button is disabled (true end of results)
                if is_next_button_disabled(driver, logger):
                    logger.info("Next button is disabled - reached end of search results")
                    break
                
                # If we've had too many consecutive empty pages, also check the button
                if consecutive_empty_pages >= max_consecutive_empty:
                    logger.warning(f"Too many consecutive empty pages ({consecutive_empty_pages})")
                    if is_next_button_disabled(driver, logger):
                        logger.info("Next button is disabled - confirmed end of results")
                        break
                    else:
                        logger.info("Next button still enabled - continuing despite empty pages")
                        
            else:
                # Reset consecutive empty pages counter
                consecutive_empty_pages = 0
                
                # Add profiles to our collection (but don't exceed the target)
                remaining_needed = profiles_number - len(profiles)
                profiles_to_add = page_profiles[:remaining_needed]
                profiles.extend(profiles_to_add)
                
                logger.info(f"Added {len(profiles_to_add)} profiles from page {current_page}")
                logger.info(f"Total profiles collected: {len(profiles)}/{profiles_number}")
            
            # Check if we have enough profiles
            if len(profiles) >= profiles_number:
                logger.info("Target number of profiles reached!")
                break
            
            # Move to next page by incrementing page number
            current_page += 1
            logger.info(f"Preparing to move to page {current_page}")
            
            # Add delay between pages to avoid being blocked
            time.sleep(2)
        
        if current_page > max_pages:
            logger.warning(f"Reached maximum page limit ({max_pages})")
        
        # Save results to CSV
        if profiles:
            csv_filename = save_profiles_to_csv(profiles, keywords)
            logger.info(f"\nScraping completed successfully!")
            logger.info(f"Total profiles collected: {len(profiles)}")
            logger.info(f"Pages processed: {start_page} to {current_page - 1}")
            logger.info(f"Data saved to: {csv_filename}")
        else:
            logger.warning("No profiles were collected")
            
    except Exception as e:
        logger.error(f"Error during search process: {str(e)}")
    
    logger.info("Search process finished")
    return profiles

def search_connections_simple(driver, keywords, profiles_number, start_page=1):
    """
    Simplified version that maintains backward compatibility
    """
    return search_connections(driver, keywords, profiles_number, start_page)