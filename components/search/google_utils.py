"""
Google page utilities - CAPTCHA handling and pagination.

Centralized functions for:
- Detecting and handling Google CAPTCHA / sorry pages
- Navigating Google pagination
"""
import logging
import time
from typing import Optional, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from components.search.google_selectors import GoogleSelectors

logger = logging.getLogger(__name__)


def is_captcha_page(driver: webdriver.Chrome) -> bool:
    """Check if the current page is a Google CAPTCHA or sorry page."""
    # Check for reCAPTCHA elements
    for selector in GoogleSelectors.CAPTCHA_INDICATORS:
        if driver.find_elements(By.CSS_SELECTOR, selector):
            return True

    # Check for sorry page indicators
    for selector in GoogleSelectors.SORRY_PAGE_INDICATORS:
        if driver.find_elements(By.CSS_SELECTOR, selector):
            return True

    # Check if URL contains "sorry"
    if "/sorry/" in driver.current_url:
        return True

    # Check if no search results were found but page loaded
    title = driver.title.lower()
    if "sorry" in title or "captcha" in title or "automated" in title:
        return True

    return False


def is_consent_popup(driver: webdriver.Chrome) -> bool:
    """Check if a consent popup is blocking the page."""
    for selector in GoogleSelectors.CONSENT_POPUP_BUTTONS:
        if driver.find_elements(By.CSS_SELECTOR, selector):
            return True
    return False


def handle_consent_popup(driver: webdriver.Chrome) -> bool:
    """Attempt to handle Google consent popup automatically."""
    for selector in GoogleSelectors.CONSENT_POPUP_BUTTONS:
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, selector)
            if buttons:
                buttons[0].click()
                logger.info("Consent popup handled via selector: %s", selector)
                time.sleep(1)
                return True
        except Exception:
            continue
    return False


def wait_for_captcha_manual_solve(driver: webdriver.Chrome, timeout: int = 300) -> bool:
    """Pause and wait for user to manually solve CAPTCHA.

    Args:
        driver: Selenium WebDriver
        timeout: Maximum seconds to wait (default: 5 minutes)

    Returns:
        True if CAPTCHA was solved, False if timeout or user cancelled
    """
    logger.warning("=" * 60)
    logger.warning("CAPTCHA / SORRY PAGE DETECTED")
    logger.warning("Please solve the CAPTCHA in the browser window.")
    logger.warning("Waiting up to %d seconds...", timeout)
    logger.warning("=" * 60)

    start = time.time()
    check_interval = 3

    while time.time() - start < timeout:
        time.sleep(check_interval)

        if is_captcha_page(driver):
            elapsed = int(time.time() - start)
            if elapsed % 15 == 0:
                logger.info("Still waiting... %d seconds elapsed", elapsed)
        else:
            logger.success("CAPTCHA solved! Continuing...")
            return True

    logger.error("CAPTCHA solve timeout (%d seconds)", timeout)
    return False


def has_next_page(driver: webdriver.Chrome) -> bool:
    """Check if there is a next page available in Google search results.

    Uses multiple fallback selectors in case Google changes HTML.

    Returns:
        True if next page link exists
    """
    # Primary selector
    if driver.find_elements(By.CSS_SELECTOR, GoogleSelectors.NEXT_BUTTON):
        return True

    # Fallback selectors
    for selector in GoogleSelectors.NEXT_BUTTON_FALLBACKS:
        if driver.find_elements(By.CSS_SELECTOR, selector):
            return True

    # JavaScript check for any link with "Next" or "Suivant" text
    has_next = driver.execute_script("""
        var all = document.querySelectorAll('a');
        for (var i = 0; i < all.length; i++) {
            var text = all[i].textContent.trim();
            if (text === 'Next' || text === 'Suivant' || text === 'Next page') {
                return true;
            }
        }
        return false;
    """)
    return bool(has_next)


def go_to_next_page(driver: webdriver.Chrome, current_url: str = "") -> bool:
    """Navigate to the next Google search results page.

    Tries multiple strategies:
    1. Click the #pnnext button
    2. Find the next page link by aria-label or text
    3. Extract URL from pagination table and navigate

    Returns:
        True if navigation succeeded
    """
    # Strategy 1: Click primary next button
    try:
        next_btn = driver.find_element(By.CSS_SELECTOR, GoogleSelectors.NEXT_BUTTON)
        if next_btn.is_displayed():
            href = next_btn.get_attribute("href")
            if href:
                driver.get(href)
                time.sleep(2)
                logger.debug("Next page via #pnnext click")
                return True
    except Exception:
        pass

    # Strategy 2: Try fallback selectors
    for selector in GoogleSelectors.NEXT_BUTTON_FALLBACKS:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                href = el.get_attribute("href")
                if href:
                    driver.get(href)
                    time.sleep(2)
                    logger.debug("Next page via selector: %s", selector)
                    return True
        except Exception:
            continue

    # Strategy 3: JavaScript - find next page link by text
    next_href = driver.execute_script("""
        var all = document.querySelectorAll('a');
        for (var i = 0; i < all.length; i++) {
            var text = all[i].textContent.trim();
            var href = all[i].getAttribute('href');
            if ((text === 'Next' || text === 'Suivant' || text === 'Next page') && href) {
                return href;
            }
        }
        return null;
    """)

    if next_href:
        driver.get(next_href)
        time.sleep(2)
        logger.debug("Next page via JavaScript text search")
        return True

    logger.warning("Could not find next page link")
    return False
