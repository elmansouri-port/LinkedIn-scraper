#actions/group_outreach.py
"""
Group outreach — send messages to group members.
Refactored to use the components layer for element interactions.
"""
import time
import logging
import pandas as pd
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from config.settings import GROUP_URL, MESSAGE, GROUP_ID
from utils.send_csv import *

# Component imports — all Selenium element logic is now in components/
from components.group.search import enter_search_term
from components.group.members import get_member_elements
from components.messaging.compose import open_message_dialog, type_and_send_message
from components.selectors import GroupSelectors, MessagingSelectors


def send_message_to_person(driver, profile_name):
    """Send message to a specific person using component-based selectors"""
    wait = WebDriverWait(driver, 15)

    try:
        # Go to group page
        driver.get(GROUP_URL)
        time.sleep(2)

        # Find search input and type name using component
        enter_search_term(driver, profile_name, timeout=15)
        time.sleep(2)  # Wait for results to load

        # Locate the list of members using component
        members_list = get_member_elements(driver)

        # Iterate through the list to find the correct member
        for member in members_list:
            try:
                # Find the member's name within the current list item
                member_name_element = member.find_element(
                    By.CSS_SELECTOR, GroupSelectors.MEMBER_NAME
                )
                member_name = member_name_element.text.strip()

                # Check if the name matches the profile_name
                if member_name.lower() == profile_name.lower():
                    # Open the message dialog for this member
                    if open_message_dialog(member):
                        time.sleep(3)  # Wait for the message dialog to open
                        # Type and send the message
                        if type_and_send_message(driver, MESSAGE, timeout=15):
                            print(f"✅ Message sent to {profile_name}")
                            return True
                        else:
                            print(f"❌ Failed to send message to {profile_name}")
                            return False

            except Exception as e:
                # If there's an issue with this member, skip to the next
                continue

        # If no matching member is found
        print(f"❌ Could not find member: {profile_name}")
        return False

    except TimeoutException:
        print(f"❌ Timeout: Could not send message to {profile_name}")
        return False
    except Exception as e:
        print(f"❌ Error sending message to {profile_name}: {str(e)}")
        return False


def message_all_group_members(driver):
    """Main function to message all group members"""

    # Load CSV file
    df = load_csv_file()
    if df is None:
        return

    print(f"Found {len(df)} members in CSV file")

    # Process each member
    for index, row in df.iterrows():
        profile_name = row['Name']  # Adjust column name as needed
        current_status = row['status']

        # Skip if already sent
        if current_status == 'sent':
            print(f"⏭️  Skipping {profile_name} - already sent")
            continue

        print(f"📤 Sending message to {profile_name}...")

        # Try to send message
        success = send_message_to_person(driver, profile_name)

        if success:
            # Update status and time
            df.at[index, 'status'] = 'sent'
            df.at[index, 'sent_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            # Mark as failed
            df.at[index, 'status'] = 'failed'
            df.at[index, 'sent_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Save progress after each attempt
        save_csv_file(df)

        # Wait between messages to avoid being blocked
        time.sleep(5)

    print("✅ Finished processing all members")
