"""
Messaging Compose Component — type and send messages in LinkedIn.
"""
import time
import logging
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from components.selectors import MessagingSelectors, GroupSelectors

logger = logging.getLogger(__name__)


def open_message_dialog(driver, member_element):
    """
    Click the "Message" button on a group member element to open compose.

    Args:
        driver:         Selenium WebDriver
        member_element: WebElement for the member list item

    Returns:
        True if dialog opened, False otherwise
    """
    try:
        by, value = GroupSelectors.MESSAGE_BUTTON
        msg_button = member_element.find_element(by, value)
        msg_button.click()
        time.sleep(3)
        logger.info("Message dialog opened")
        return True
    except Exception as e:
        logger.error(f"Could not open message dialog: {e}")
        return False


def type_and_send_message(driver, message, timeout=15):
    """
    Type a message and click send in the LinkedIn messaging compose box.

    Args:
        driver:  Selenium WebDriver
        message: text to send
        timeout: seconds to wait for compose box

    Returns:
        True on success, False on failure
    """
    try:
        wait = WebDriverWait(driver, timeout)

        # Focus the compose box
        by, value = MessagingSelectors.COMPOSE_BOX
        message_box = wait.until(EC.presence_of_element_located((by, value)))
        message_box.click()
        time.sleep(1)
        message_box.send_keys(message)
        time.sleep(1)

        # Click send
        send_by, send_value = MessagingSelectors.SEND_BUTTON
        send_button = wait.until(
            EC.element_to_be_clickable((send_by, send_value))
        )
        send_button.click()

        logger.info("Message sent successfully")
        return True

    except TimeoutException:
        logger.error("Timeout waiting for messaging compose box")
        return False
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False
