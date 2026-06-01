"""
Search Pagination Component — handles pagination on LinkedIn search results.
"""
import logging
from selenium.common.exceptions import NoSuchElementException

from components.selectors import SearchSelectors

logger = logging.getLogger(__name__)


def is_next_button_disabled(driver):
    """
    Check if the Next button on the search results page is disabled.

    Returns:
        True if disabled or not found (no more pages), False if enabled
    """
    for by, value in SearchSelectors.NEXT_BUTTON_FALLBACKS:
        try:
            next_button = driver.find_element(by, value)

            is_disabled = (
                next_button.get_attribute("disabled") is not None
                or "artdeco-button--disabled" in (next_button.get_attribute("class") or "")
                or next_button.get_attribute("disabled") == "true"
                or next_button.get_attribute("disabled") == ""
            )

            if is_disabled:
                logger.info("Next button found and is DISABLED — no more pages")
                return True
            else:
                logger.info("Next button found and is ENABLED — more pages available")
                return False

        except NoSuchElementException:
            continue

    logger.info("No next button found — assuming no more pages")
    return True
