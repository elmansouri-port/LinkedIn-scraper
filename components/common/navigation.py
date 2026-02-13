"""
Navigation utilities — page loading and refreshing.
"""
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)


def navigate_to(driver, url, wait_seconds=2):
    """
    Navigate to a URL and wait for the page body to load.

    Args:
        driver:       Selenium WebDriver
        url:          target URL
        wait_seconds: seconds to wait after navigation
    """
    driver.get(url)
    time.sleep(wait_seconds)
    logger.info(f"Navigated to: {url}")


def refresh_and_wait(driver, wait_seconds=2):
    """
    Refresh the current page and wait for it to reload.

    Args:
        driver:       Selenium WebDriver
        wait_seconds: seconds to wait after refresh

    Returns:
        True on success, False on error
    """
    try:
        driver.refresh()
        time.sleep(wait_seconds)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        logger.info("Page refreshed successfully")
        return True
    except Exception as e:
        logger.error(f"Error refreshing page: {e}")
        return False
