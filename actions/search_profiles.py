#action/search_connections.py
"""
LinkedIn profile search — collect profiles from search pages.
Refactored to use the components layer for result extraction and pagination.
"""
import time
import logging
import pandas as pd
import os
from datetime import datetime
from config.settings import GROUP_URL, MESSAGE, GROUP_ID
from utils.send_csv import *

# Component imports — all Selenium element logic is now in components/
from components.search.results import extract_profiles_from_page as _extract_profiles
from components.search.pagination import is_next_button_disabled as _is_next_disabled


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


def url_builder(keywords, geoUrn="%5B%2210501587522%5D", page=1, origin="GLOBAL_SEARCH_HEADER"):
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
    """Extract profiles from current page — delegates to component."""
    profiles = _extract_profiles(driver, timeout=15)
    logger.info(f"Found {len(profiles)} profiles on current page")
    for i, p in enumerate(profiles, 1):
        logger.info(f"Extracted profile {i}: {p['name']}")
    return profiles


def is_next_button_disabled(driver, logger):
    """Check if the Next button is disabled — delegates to component."""
    disabled = _is_next_disabled(driver)
    if disabled:
        logger.info("Next button found and is DISABLED - no more pages available")
    else:
        logger.info("Next button found and is ENABLED - more pages available")
    return disabled


def search_connections(driver, keywords, profiles_number, start_page=1):
    """
    Enhanced search function that collects specified number of profiles.
    Business logic only — element interactions are in components/.
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

            # Extract profiles from current page (using component)
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