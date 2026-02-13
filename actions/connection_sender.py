# actions/connection_sender.py
"""
Connection request sender.
Refactored to use the components layer for button/modal interactions.
"""
import time
import logging
from selenium.webdriver.common.by import By
from config.settings import GROUP_URL, MESSAGE, GROUP_ID

# Component imports — all Selenium element logic is now in components/
from components.connection.buttons import click_connect_button
from components.connection.modal import add_note_and_send, send_without_note
from components.common.navigation import navigate_to


def send_connection(driver, profile_url, note_message, note=True):
    """
    Send a connection request to a LinkedIn profile.
    Delegates element interactions to components.

    Args:
        driver: Selenium WebDriver instance
        profile_url: Target profile URL
        note_message: Message to include with connection request
        note: Whether to include a note (True) or send without one (False)
    """
    driver.refresh()
    time.sleep(1)
    navigate_to(driver, profile_url, wait_seconds=2)
    print("start to search")

    # Step 1: Click the connect button (handles direct and dropdown variants)
    connect_clicked = click_connect_button(driver)

    if not connect_clicked:
        print("Could not find connect button")
        return

    time.sleep(0.5)

    # Step 2: Handle modal based on note parameter
    if note:
        success = add_note_and_send(driver, note_message)
        if not success:
            print("Could not add note and send")
            return
    else:
        success = send_without_note(driver)
        if not success:
            print("Could not send without note")
            return

    time.sleep(0.3)
    print("Connection request sent")


# ---- Original code preserved as comment for reference ----
# (removed old inline CSS selector implementations)