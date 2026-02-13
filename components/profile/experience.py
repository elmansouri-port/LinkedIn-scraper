"""
Profile Experience Component — company extraction from LinkedIn profile pages.
"""
import time
import logging
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from components.selectors import ProfileSelectors
from components.common.scrolling import scroll_to_element

logger = logging.getLogger(__name__)


def extract_companies(driver):
    """
    Extract all company names from the experience section of the current profile.

    Args:
        driver: Selenium WebDriver (already on a profile page)

    Returns:
        list[str] of unique company names
    """
    companies = []

    try:
        # Scroll to experience section
        try:
            by, value = ProfileSelectors.EXPERIENCE_SECTION
            experience_section = driver.find_element(by, value)
            scroll_to_element(driver, experience_section)
            time.sleep(2)
        except NoSuchElementException:
            logger.warning("Experience section not found")
            return companies

        time.sleep(2)

        # Find experience items using fallback selectors
        experience_items = []
        for by, value in ProfileSelectors.EXPERIENCE_ITEMS_FALLBACKS:
            try:
                experience_items = driver.find_elements(by, value)
                if experience_items:
                    break
            except NoSuchElementException:
                continue

        if not experience_items:
            logger.warning("No experience items found")
            return companies

        logger.info(f"Found {len(experience_items)} experience items")

        # Extract company names from each item
        for item in experience_items:
            for by, value in ProfileSelectors.COMPANY_NAME_FALLBACKS:
                try:
                    company_element = item.find_element(by, value)
                    company_text = company_element.text.strip()
                    if company_text and "·" in company_text:
                        company_name = company_text.split("·")[0].strip()
                        if company_name and company_name not in companies:
                            companies.append(company_name)
                        break
                except NoSuchElementException:
                    continue

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for c in companies:
            if c not in seen:
                seen.add(c)
                unique.append(c)

        return unique

    except Exception as e:
        logger.error(f"Error extracting companies: {e}")
        return companies
