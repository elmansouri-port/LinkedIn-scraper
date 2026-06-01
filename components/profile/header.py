"""
Profile Header Component — name extraction from LinkedIn profile pages.
"""
import logging
import re
from selenium.webdriver.common.by import By
from components.selectors import ProfileSelectors
from components.common.waits import find_with_fallback
from selenium.common.exceptions import NoSuchElementException

logger = logging.getLogger(__name__)


def extract_name(driver, timeout=15):
    """
    Extract first name, last name, and full name from the current page.

    Tries multiple strategies in order:
      1. ProfileSelectors.NAME_FALLBACKS (CSS/XPath)
      2. First <h1> on the page (standard profile page)
      3. First <h2> with a connection badge nearby (search card)
      4. Any element matching common LinkedIn profile name patterns

    Args:
        driver:  Selenium WebDriver
        timeout: seconds to wait

    Returns:
        dict with keys: first_name, last_name, full_name

    Raises:
        ValueError if name cannot be extracted
    """
    strategies = [
        ("fallback selectors", lambda: find_with_fallback(
            driver, ProfileSelectors.NAME_FALLBACKS, timeout=timeout
        )),
        ("any h1", lambda: driver.find_element(By.CSS_SELECTOR, "h1")),
        ("top h1 inside profile section", lambda: driver.find_element(
            By.XPATH,
            "//main//h1"
        )),
    ]

    name_text = ""
    last_error = None

    for label, fn in strategies:
        try:
            el = fn()
            text = el.text.strip()
            if text and _looks_like_name(text):
                name_text = text
                logger.info("Name found via '%s': %s", label, name_text)
                break
            elif text:
                name_text = text
                break
        except Exception as e:
            last_error = e
            continue

    if not name_text:
        # Last resort: scan all elements for anything that looks like a name
        for tag in ["h1", "h2", "h3"]:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, tag)
                for el in elements:
                    text = el.text.strip()
                    if text and _looks_like_name(text):
                        name_text = text
                        logger.info("Name found via scan of <%s>: %s", tag, name_text)
                        break
                if name_text:
                    break
            except Exception:
                continue

    if not name_text:
        raise ValueError(
            f"Could not extract profile name. Last error: {last_error}"
        )

    # Split name into first and last
    name_parts = name_text.split()

    if len(name_parts) == 0:
        raise ValueError("Empty name")
    elif len(name_parts) == 1:
        first_name = name_parts[0]
        last_name = ""
    elif len(name_parts) == 2:
        first_name = name_parts[0]
        last_name = name_parts[1]
    else:
        first_name = name_parts[0]
        last_name = " ".join(name_parts[1:])

    return {
        "first_name": first_name,
        "last_name": last_name,
        "full_name": name_text,
    }


_NON_NAME_PHRASES = {
    "notifications", "notification", "messages", "invitations", "invitation",
    "connect", "connections", "followers", "following", "profile", "settings",
    "search", "home", "network", "jobs", "messaging", "notifications,",
    "message", "inbox",
}


def _looks_like_name(text):
    """Heuristic: a real name is 2+ words, mostly letters, no URLs/emails."""
    if not text:
        return False
    if len(text) < 2:
        return False
    if re.search(r'https?://|@|#|\.com|\.org|www\.', text, re.I):
        return False
    # Reject common LinkedIn UI phrases
    lower = text.lower()
    if any(phrase in lower for phrase in _NON_NAME_PHRASES):
        return False
    # Should be mostly alphabetic
    words = text.split()
    if len(words) >= 2:
        alpha_words = sum(1 for w in words if w.isalpha())
        return alpha_words >= len(words) - 1
    return text.isalpha()
