"""
Connection Buttons Component — handles finding and clicking connect buttons.
"""
import time
import logging
from selenium.common.exceptions import NoSuchElementException

from components.selectors import ConnectionSelectors
from components.common.waits import find_and_click_button_by_text

logger = logging.getLogger(__name__)


def click_connect_button(driver):
    """
    Try to click the "Connect" button on a profile page.
    Handles both the direct button and the hidden dropdown variant.

    Returns:
        True if connected, False if connect button not found
    """
    # Step 1: Try direct connect button
    found = find_and_click_button_by_text(
        driver,
        ConnectionSelectors.CONNECT_BUTTONS,
        ConnectionSelectors.CONNECT_TEXTS,
    )

    if found:
        logger.info("Clicked direct connect button")
        return True

    # Step 2: Try the hidden connect button via dropdown
    try:
        by, value = ConnectionSelectors.DROPDOWN_TRIGGER
        plus_button = driver.find_element(by, value)
        plus_button.click()
        time.sleep(0.2)

        found = find_and_click_button_by_text(
            driver,
            ConnectionSelectors.DROPDOWN_ITEMS,
            ConnectionSelectors.CONNECT_TEXTS,
        )

        if found:
            logger.info("Clicked connect from dropdown menu")
            return True

    except (NoSuchElementException, Exception) as e:
        logger.warning(f"Could not find connect button: {e}")

    return False
