"""
Search Results Component — extract profiles from LinkedIn search results pages.
"""
import logging
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from components.selectors import SearchSelectors

logger = logging.getLogger(__name__)


def extract_profiles_from_page(driver, timeout=15):
    """
    Extract all profile names and links from the current search results page.

    Args:
        driver:  Selenium WebDriver (on a LinkedIn search results page)
        timeout: seconds to wait for results

    Returns:
        list[dict] with keys: name, link
    """
    profiles = []

    try:
        wait = WebDriverWait(driver, timeout)
        by, value = SearchSelectors.RESULTS_LIST
        wait.until(EC.presence_of_element_located((by, value)))

        # Find all profile links
        link_by, link_value = SearchSelectors.PROFILE_LINKS
        profile_links = driver.find_elements(link_by, link_value)
        logger.info(f"Found {len(profile_links)} profile links on current page")

        name_by, name_value = SearchSelectors.PROFILE_NAME

        for i, anchor in enumerate(profile_links, 1):
            try:
                name_element = anchor.find_element(name_by, name_value)
                name = name_element.text.strip()

                if name:
                    profiles.append({
                        "name": name,
                        "link": anchor.get_attribute("href"),
                    })
                    logger.info(f"Extracted profile {i}: {name}")
                else:
                    logger.warning(f"Empty name for profile {i}")

            except Exception as e:
                logger.warning(f"Failed to extract profile {i}: {e}")
                continue

    except TimeoutException:
        logger.error("Timeout waiting for search results to load")
    except Exception as e:
        logger.error(f"Error extracting profiles from page: {e}")

    return profiles
