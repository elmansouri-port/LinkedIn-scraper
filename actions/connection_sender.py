import time
import logging
import pandas as pd
import os
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from config.settings import GROUP_URL, MESSAGE, GROUP_ID
from utils.send_csv import *


def find_and_click_button_by_text(driver, selector, target_texts):
    """Helper function to find and click button by span text"""
    buttons = driver.find_elements(By.CSS_SELECTOR, selector)
    for button in buttons:
        try:
            span = button.find_element(By.TAG_NAME, "span")
            if any(text in span.text for text in target_texts):
                span.click()
                return True
        except Exception:
            continue
    return False


def send_connection(driver, profile_url, note_message, note=True):
    wait = WebDriverWait(driver, 15)
    
    driver.refresh()
    time.sleep(1)
    driver.get(profile_url)
    time.sleep(2)
    print("start to search")

    # Step 1: Try to find direct connect button
    connect_found = find_and_click_button_by_text(
        driver,
        "div.pb5.ph5 button[id^='ember'][class*='ember-view']",
        ["Se connecter", "Connect"]
    )
    
    # Step 2: If not found, try the hidden connect button via plus menu
    if not connect_found:
        try:
            # Click the plus button
            plus = driver.find_element(By.CSS_SELECTOR, 
                "div.ph5.pb5 div[id^='ember'].artdeco-dropdown.artdeco-dropdown--placement-bottom button[id^='ember'][class*='artdeco-dropdown__trigger']")
            plus.click()
            time.sleep(0.2)
            
            # Find connect in dropdown
            find_and_click_button_by_text(
                driver,
                "div.ph5.pb5 div[id^='ember'].artdeco-dropdown.artdeco-dropdown--placement-bottom ul li div[id^='ember']",
                ["Se connecter", "Connect"]
            )
        except Exception as e:
            print(f"Could not find connect button: {e}")
            return
    
    time.sleep(0.5)
    
    # Step 3: Handle modal based on note parameter
    if note:
        # Add note flow
        note_added = find_and_click_button_by_text(
            driver,
            "div[id='artdeco-modal-outlet'] div[id^='ember'].artdeco-modal__actionbar button[id^='ember']",
            ["Ajouter une note", "Add a note"]
        )
        
        if note_added:
            time.sleep(0.3)
            # Enter note message
            try:
                note_field = driver.find_element(By.CSS_SELECTOR, 
                    "div[id='artdeco-modal-outlet'] div[id^='ember'].artdeco-modal__content textarea")
                note_field.send_keys(note_message)
                time.sleep(0.2)
                
                # Send with note
                find_and_click_button_by_text(
                    driver,
                    "div[id='artdeco-modal-outlet'] div[id^='ember'].artdeco-modal__actionbar button",
                    ["Envoyer", "Send"]
                )
            except Exception as e:
                print(f"Could not add note: {e}")
                return
    else:
        # Send without note
        find_and_click_button_by_text(
            driver,
            "div[id='artdeco-modal-outlet'] div[id^='ember'].artdeco-modal__actionbar button[id^='ember']",
            ["Envoyer sans note", "Send without a note"]
        )
    
    time.sleep(0.3)
    print("Connection request sent")


#original code
"""#action/connection_sender.py
import time
import logging
import pandas as pd
import os
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from config.settings import GROUP_URL, MESSAGE, GROUP_ID
from utils.send_csv import *



def send_connection(driver, profile_url, note_message, note=True):

    wait = WebDriverWait(driver, 15)

    driver.refresh()
    time.sleep(1)

    driver.get(profile_url)

    time.sleep(2)
    print("start to search")


    # connect button direct

    buttons = driver.find_elements(By.CSS_SELECTOR,"div.pb5.ph5 button[id^='ember'][class*='ember-view']")

    for button in buttons:
        try:
            # Find the <span> inside the button and get its text
            span = button.find_element(By.TAG_NAME, "span")
            if "Se connecter" in span.text or "Connect" in span.text:
                span.click()
        except Exception:
            # If no <span> is found, skip this button
            continue

    # connect button hided 

    # click the plus
    plus = driver.find_element(By.CSS_SELECTOR,"div.ph5.pb5 div[id^='ember'].artdeco-dropdown.artdeco-dropdown--placement-bottom button[id^='ember'][class*='artdeco-dropdown__trigger']") #div[id^='ember518'].artdeco-dropdown.artdeco-dropdown--placement-bottom.artdeco-dropdown--justification-left.ember-view button[id^='ember'][class*='artdeco-dropdown__trigger']
    plus.click()
    time.sleep(0.2)

    hided_connect = driver.find_elements(By.CSS_SELECTOR,"div.ph5.pb5 div[id^='ember'].artdeco-dropdown.artdeco-dropdown--placement-bottom ul li div[id^='ember']")
    for connect in hided_connect:
        try:
            # Find the <span> inside the button and get its text
            span = connect.find_element(By.TAG_NAME, "span")
            if "Se connecter" in span.text or "Connect" in span.text:
                span.click()
        except Exception:
            # If no <span> is found, skip this button
            continue
    
    #the send button without note
    modal_without_note = driver.find_elements(By.CSS_SELECTOR,"div[id='artdeco-modal-outlet'] div[id^='ember'].artdeco-modal__actionbar button[id^='ember']")

    for without_note in modal_without_note:
        try:
            # Find the <span> inside the button and get its text
            span = without_note.find_element(By.TAG_NAME, "span")
            if "Envoyer sans note" in span.text or "Send without a note" in span.text:
                span.click()
                time.sleep(0.3)
        except Exception:
            # If no <span> is found, skip this button
            continue

    # the add note button
    modal_with_note = driver.find_elements(By.CSS_SELECTOR,"div[id='artdeco-modal-outlet'] div[id^='ember'].artdeco-modal__actionbar button[id^='ember']")
    
    for with_note in modal_with_note:
        try:
            # Find the <span> inside the button and get its text
            span = with_note.find_element(By.TAG_NAME, "span")
            if "Ajouter une note" in span.text or "Add a note" in span.text:
                span.click()
                time.sleep(0.3)
        except Exception:
            # If no <span> is found, skip this button
            continue

    # find the note entry
    note = driver.find_element(By.CSS_SELECTOR,"div[id='artdeco-modal-outlet'] div[id^='ember'].artdeco-modal__content textarea")
    note.send_keys(note_message)
    time.sleep(0.2)

    #find the send button after adding the note
    send_button = driver.find_elements(By.CSS_SELECTOR,"div[id='artdeco-modal-outlet'] div[id^='ember'].artdeco-modal__actionbar button")

    for button in send_button:
        try:
            # Find the <span> inside the button and get its text
            span = button.find_element(By.TAG_NAME, "span")
            if "Envoyer" in span.text or "Send" in span.text:
                span.click()
                time.sleep(0.3)
        except Exception:
            # If no <span> is found, skip this button
            continue




    # for without_not in modal_without_not:
    #     print(without_not.get_attribute('outerHTML'))






"""