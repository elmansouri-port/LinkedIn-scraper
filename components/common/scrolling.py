"""
Scrolling utilities — extracted from group_scraper.py and smart_search_group.py.
"""
import time
import logging
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from components.common.waits import click_with_fallback

logger = logging.getLogger(__name__)


def scroll_to_bottom(driver, wait_seconds=1):
    """
    Scroll to the bottom of the page.

    Returns:
        tuple: (old_height, new_height)
    """
    old_height = driver.execute_script("return document.body.scrollHeight")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(wait_seconds)
    new_height = driver.execute_script("return document.body.scrollHeight")
    return old_height, new_height


def has_page_scrolled(old_height, new_height, buffer=30):
    """
    Check if the page actually scrolled (accounting for minor variations).

    Args:
        old_height:  previous scroll height
        new_height:  current scroll height
        buffer:      pixel tolerance

    Returns:
        bool
    """
    return (old_height + buffer) < new_height


def scroll_to_element(driver, element):
    """Scroll an element into the center of the viewport."""
    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center'});", element
    )


def click_load_more(driver, selectors, timeout=2):
    """
    Try to find and click a 'load more' button using fallback selectors.

    Args:
        driver:    Selenium WebDriver
        selectors: list of (By.XXX, value) tuples to try
        timeout:   wait per selector

    Returns:
        True if a button was clicked, False otherwise
    """
    return click_with_fallback(driver, selectors, timeout=timeout)


def click_load_more_js(driver, selectors, timeout=2):
    """
    Like click_load_more but uses JavaScript click to avoid interception issues.

    Returns:
        True if clicked, False otherwise
    """
    wait = WebDriverWait(driver, timeout)

    for by, value in selectors:
        try:
            button = wait.until(EC.element_to_be_clickable((by, value)))
            if button.is_displayed() and button.is_enabled():
                scroll_to_element(driver, button)
                driver.execute_script("arguments[0].click();", button)
                return True
        except (TimeoutException, Exception):
            continue

    return False
