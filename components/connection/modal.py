"""
Connection Modal Component — handles the connection request modal (add note / send).
"""
import time
import logging
from selenium.common.exceptions import NoSuchElementException

from components.selectors import ConnectionSelectors
from components.common.waits import find_and_click_button_by_text

logger = logging.getLogger(__name__)


def add_note_and_send(driver, message):
    """
    In the connection modal, click "Add a note", type the message, and send.

    Args:
        driver:  Selenium WebDriver
        message: note text to attach to the connection request

    Returns:
        True on success, False on failure
    """
    try:
        # Click "Add a note" button
        note_clicked = find_and_click_button_by_text(
            driver,
            ConnectionSelectors.MODAL_BUTTONS,
            ConnectionSelectors.ADD_NOTE_TEXTS,
        )

        if not note_clicked:
            logger.warning("Could not find 'Add a note' button")
            return False

        time.sleep(0.3)

        # Type the note
        by, value = ConnectionSelectors.NOTE_TEXTAREA
        note_field = driver.find_element(by, value)
        note_field.send_keys(message)
        time.sleep(0.2)

        # Click send
        find_and_click_button_by_text(
            driver,
            ConnectionSelectors.MODAL_ALL_BUTTONS,
            ConnectionSelectors.SEND_TEXTS,
        )

        logger.info("Connection note sent")
        return True

    except Exception as e:
        logger.error(f"Error adding note: {e}")
        return False


def send_without_note(driver):
    """
    In the connection modal, click "Send without a note".

    Returns:
        True on success, False on failure
    """
    result = find_and_click_button_by_text(
        driver,
        ConnectionSelectors.MODAL_BUTTONS,
        ConnectionSelectors.SEND_WITHOUT_NOTE_TEXTS,
    )

    if result:
        logger.info("Connection sent without note")
    else:
        logger.warning("Could not find 'Send without note' button")

    return result
