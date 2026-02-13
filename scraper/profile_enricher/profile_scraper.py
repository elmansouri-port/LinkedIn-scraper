"""
LinkedIn Profile Scraper for Profile Enricher
Extracts name and company information from LinkedIn profiles.

Refactored to use the components layer for element extraction.
"""
import time
import logging
from components.profile.header import extract_name
from components.profile.experience import extract_companies
from components.common.navigation import navigate_to

logger = logging.getLogger(__name__)


def extract_profile_name(driver, profile_url):
    """
    Navigate to LinkedIn profile and extract first and last name.
    Delegates element extraction to components.profile.header.

    Args:
        driver: Selenium WebDriver instance
        profile_url: LinkedIn profile URL

    Returns:
        Dictionary with first_name, last_name, and full_name
    """
    try:
        navigate_to(driver, profile_url, wait_seconds=3)
        return extract_name(driver, timeout=15)
    except Exception as e:
        raise Exception(f"Error extracting profile name: {str(e)}")


def extract_experience_companies(driver):
    """
    Extract all company names from the experience section.
    Delegates element extraction to components.profile.experience.

    Args:
        driver: Selenium WebDriver instance

    Returns:
        List of company names
    """
    return extract_companies(driver)


def scrape_profile_data(driver, profile_url):
    """
    Main function to scrape profile data (name + companies).

    Args:
        driver: Selenium WebDriver instance
        profile_url: LinkedIn profile URL

    Returns:
        Dictionary with profile data
    """
    try:
        # Extract name
        name_data = extract_profile_name(driver, profile_url)

        # Small delay between operations
        time.sleep(2)

        # Extract companies
        companies = extract_experience_companies(driver)

        # Combine data
        profile_data = {
            **name_data,
            'companies': companies,
            'url': profile_url
        }

        return profile_data

    except Exception as e:
        raise Exception(f"Error scraping profile: {str(e)}")
