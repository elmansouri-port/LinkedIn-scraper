"""
Connection request sender.
Delegates element interactions to the components layer.
"""
import time
import logging

from components.connection.buttons import click_connect_button
from components.connection.modal import add_note_and_send, send_without_note
from components.common.navigation import navigate_to

logger = logging.getLogger(__name__)


def send_connection(driver, profile_url, note_message, note=True):
    """Send a connection request to a LinkedIn profile."""
    driver.refresh()
    time.sleep(1)
    navigate_to(driver, profile_url, wait_seconds=2)

    connect_clicked = click_connect_button(driver)
    if not connect_clicked:
        logger.warning("Could not find connect button for %s", profile_url)
        return

    time.sleep(0.5)

    if note:
        success = add_note_and_send(driver, note_message)
        if not success:
            logger.warning("Could not add note and send")
            return
    else:
        success = send_without_note(driver)
        if not success:
            logger.warning("Could not send without note")
            return

    time.sleep(0.3)
    logger.info("Connection request sent to %s", profile_url)
