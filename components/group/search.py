"""
Group Search Component — search input interactions on group member pages.
"""
import time
import logging
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys

from components.selectors import GroupSelectors
from components.common.waits import find_with_fallback

logger = logging.getLogger(__name__)


def find_search_input(driver, timeout=10):
    """
    Find the search input field on the group members page.
    Handles both French and English UI automatically.

    Args:
        driver:  Selenium WebDriver
        timeout: seconds to wait

    Returns:
        WebElement for the search input

    Raises:
        NoSuchElementException if not found
    """
    return find_with_fallback(
        driver, GroupSelectors.SEARCH_INPUT_FALLBACKS, timeout=timeout
    )


def enter_search_term(driver, term, timeout=10, submit=False):
    """
    Clear the search field and type a new search term.

    Args:
        driver:  Selenium WebDriver
        term:    search string to type
        timeout: seconds to wait for input
        submit:  if True, press Enter after typing
    """
    search_input = find_search_input(driver, timeout=timeout)
    search_input.clear()
    time.sleep(0.5)
    search_input.send_keys(term)
    if submit:
        search_input.send_keys(Keys.RETURN)
    time.sleep(1)
    logger.info(f"Search term entered: '{term}'")
