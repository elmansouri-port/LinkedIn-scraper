"""
Scrolling utilities — extracted from group_scraper.py and smart_search_group.py.

Includes lazy-load-aware scrolling that reveals deferred content on
LinkedIn profile pages (Experience, Education, etc.).
"""
import time
import logging
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from components.common.waits import click_with_fallback

logger = logging.getLogger(__name__)


def scroll_to_bottom(driver, wait_seconds=1):
    """
    Scroll to the bottom of the page.

    Returns:
        tuple: (old_height, new_height)
    """
    old_height = driver.execute_script("return document.body.scrollHeight")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(wait_seconds)
    new_height = driver.execute_script("return document.body.scrollHeight")
    return old_height, new_height


def has_page_scrolled(old_height, new_height, buffer=30):
    """
    Check if the page actually scrolled (accounting for minor variations).

    Args:
        old_height:  previous scroll height
        new_height:  current scroll height
        buffer:      pixel tolerance

    Returns:
        bool
    """
    return (old_height + buffer) < new_height


def scroll_to_element(driver, element):
    """Scroll an element into the center of the viewport."""
    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center'});", element
    )


def click_load_more(driver, selectors, timeout=2):
    """
    Try to find and click a 'load more' button using fallback selectors.

    Args:
        driver:    Selenium WebDriver
        selectors: list of (By.XXX, value) tuples to try
        timeout:   wait per selector

    Returns:
        True if a button was clicked, False otherwise
    """
    return click_with_fallback(driver, selectors, timeout=timeout)


def click_load_more_js(driver, selectors, timeout=2):
    """
    Like click_load_more but uses JavaScript click to avoid interception issues.

    Returns:
        True if clicked, False otherwise
    """
    wait = WebDriverWait(driver, timeout)

    for by, value in selectors:
        try:
            button = wait.until(EC.element_to_be_clickable((by, value)))
            if button.is_displayed() and button.is_enabled():
                scroll_to_element(driver, button)
                driver.execute_script("arguments[0].click();", button)
                return True
        except (TimeoutException, Exception):
            continue

    return False


def scroll_to_reveal_content(driver, max_scrolls=12, scroll_pause=1.2,
                             target_sections=None):
    """Scroll the page incrementally to trigger lazy-loaded content.

    LinkedIn profile pages defer-render sections like Experience and
    Education until you scroll near them.  This function:

    1. Scrolls down in chunks
    2. After each chunk, checks which <h2> headings are now in the DOM
    3. Logs newly appeared headings
    4. If *target_sections* is provided (e.g. ``["Experience"]``),
       stops once all targets are found
    5. Scrolls back to the top so extraction functions see the full DOM

    Returns:
        list[str]: all ``<h2>`` heading texts found on the page.
    """
    headings = driver.execute_script("""
        return Array.from(document.querySelectorAll('h2'))
                    .map(function(h){ return h.textContent.trim(); });
    """)

    last_height = driver.execute_script("return document.body.scrollHeight")
    pause = scroll_pause
    found_targets = set()

    for i in range(max_scrolls):
        px = 600 + (i * 200)  # progressively larger scrolls (600, 800, 1000 …)
        driver.execute_script("window.scrollBy(0, arguments[0]);", px)
        time.sleep(pause)

        current = driver.execute_script("""
            return Array.from(document.querySelectorAll('h2'))
                        .map(function(h){ return h.textContent.trim(); });
        """)

        new_ones = [h for h in current if h not in headings]
        if new_ones:
            logger.info("Scroll %d/%d — new headings: %s",
                        i + 1, max_scrolls, new_ones)
            headings = current

        if target_sections:
            for t in target_sections:
                if any(t.lower() in h.lower() for h in headings):
                    found_targets.add(t)
            if len(found_targets) == len(target_sections):
                logger.info("All target sections found, stopping scroll")
                break

        # If page stopped growing and nothing new appeared, we're done
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height and not new_ones:
            logger.info("Page height stable and no new headings — done scrolling")
            break
        last_height = new_height

    # Scroll back to top so extraction starts from a clean position
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(0.4)
    return headings
