"""
Popup and overlay handlers — dismisses consent popups and overlays.
"""
import time
import logging
from components.selectors import GoogleSelectors
from components.common.waits import click_with_fallback

logger = logging.getLogger(__name__)


def handle_google_consent(driver, timeout=3):
    """
    Dismiss the Google consent / cookie popup if it appears.

    Returns:
        True if a popup was dismissed, False otherwise
    """
    try:
        clicked = click_with_fallback(
            driver, GoogleSelectors.CONSENT_BUTTON_FALLBACKS, timeout=timeout
        )
        if clicked:
            logger.info("Google consent popup dismissed")
            time.sleep(1)
        return clicked
    except Exception as e:
        logger.debug(f"No Google consent popup found: {e}")
        return False


def handle_messaging_overlay(driver):
    """
    Dismiss the LinkedIn messaging overlay if it covers interactive elements.
    Placeholder for future implementation.
    """
    # LinkedIn sometimes shows a messaging pane that blocks clicks.
    # This can be extended as needed.
    pass
