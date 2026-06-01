"""
Resilient element-finding helpers.

Provides fallback-based lookups that try multiple selectors in order,
handling LinkedIn's bilingual UI and class-name changes gracefully.
"""
import logging
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)

logger = logging.getLogger(__name__)


def find_with_fallback(driver, selectors, timeout=10):
    """
    Try each (By, value) selector in order; return the first element found.

    Args:
        driver:    Selenium WebDriver
        selectors: list of (By.XXX, value) tuples
        timeout:   seconds to wait per selector attempt

    Returns:
        WebElement

    Raises:
        NoSuchElementException if none matched
    """
    wait = WebDriverWait(driver, timeout)
    last_error = None

    for by, value in selectors:
        try:
            element = wait.until(EC.presence_of_element_located((by, value)))
            return element
        except (TimeoutException, NoSuchElementException) as e:
            last_error = e
            continue

    raise NoSuchElementException(
        f"Could not find element with any of {len(selectors)} fallback selectors. "
        f"Last error: {last_error}"
    )


def click_with_fallback(driver, selectors, timeout=10):
    """
    Try each selector; click the first clickable element found.

    Returns:
        True if clicked, False if none found
    """
    wait = WebDriverWait(driver, timeout)

    for by, value in selectors:
        try:
            element = wait.until(EC.element_to_be_clickable((by, value)))
            if element.is_displayed() and element.is_enabled():
                element.click()
                return True
        except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
            continue

    return False


def safe_extract_text(element, selector_tuple, default=""):
    """
    Extract text from a child element, returning a default on failure.

    Args:
        element:        parent WebElement
        selector_tuple: (By.XXX, value)
        default:        fallback string

    Returns:
        str
    """
    try:
        by, value = selector_tuple
        child = element.find_element(by, value)
        text = child.text.strip()
        return text if text else default
    except (NoSuchElementException, StaleElementReferenceException):
        return default


def safe_extract_attribute(element, selector_tuple, attribute, default=""):
    """
    Extract an attribute from a child element, returning a default on failure.

    Args:
        element:        parent WebElement
        selector_tuple: (By.XXX, value)
        attribute:      attribute name (e.g. 'href', 'src')
        default:        fallback string

    Returns:
        str
    """
    try:
        by, value = selector_tuple
        child = element.find_element(by, value)
        return child.get_attribute(attribute) or default
    except (NoSuchElementException, StaleElementReferenceException):
        return default


def element_exists(element, selector_tuple):
    """
    Check if a child element exists within a parent element.

    Returns:
        bool
    """
    try:
        by, value = selector_tuple
        element.find_element(by, value)
        return True
    except NoSuchElementException:
        return False


def find_and_click_button_by_text(driver, selector_tuple, target_texts):
    """
    Find buttons matching a selector, then click the one whose <span> text
    matches any of the target_texts.

    Args:
        driver:       Selenium WebDriver
        selector_tuple: (By.XXX, value)
        target_texts: list of strings to match against span text

    Returns:
        True if clicked, False otherwise
    """
    try:
        by, value = selector_tuple
        buttons = driver.find_elements(by, value)
        for button in buttons:
            try:
                from selenium.webdriver.common.by import By
                span = button.find_element(By.TAG_NAME, "span")
                if any(text in span.text for text in target_texts):
                    span.click()
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False
