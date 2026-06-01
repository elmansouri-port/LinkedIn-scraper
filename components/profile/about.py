"""
Profile About Component — about/summary extraction from LinkedIn profile pages.

Uses semantic selectors: finds <h2> with "About"/"À propos" text,
then targets <span data-testid="expandable-text-box"> for the actual summary.
No hashed class names.
"""
import logging
import time
from components.common.scrolling import scroll_to_element

logger = logging.getLogger(__name__)

_ABOUT_JS = r"""
(function() {
    // Find the About section heading
    var h2s = document.querySelectorAll('h2');
    var aboutHeading = null;
    for (var i = 0; i < h2s.length; i++) {
        var txt = h2s[i].textContent.trim().toLowerCase();
        if (txt === 'about' || txt === 'à propos' || txt === 'a propos') {
            aboutHeading = h2s[i];
            break;
        }
    }
    if (!aboutHeading) return '';

    // Find the expandable-text-box span which contains the actual about text
    // Walk up to find the section container, then search inside it
    var section = aboutHeading.parentElement;
    while (section && !section.tagName.match(/^(DIV|SECTION)$/)) {
        section = section.parentElement;
        if (!section) return '';
    }

    var expandable = section.querySelector('[data-testid="expandable-text-box"]');
    if (expandable) {
        var text = expandable.textContent.trim();
        // Remove "... more" / "...more" suffix if present
        return text.replace(/\s*\.\.\.\s*more\s*$/i, '').trim();
    }

    // Fallback: get text from first <p> directly after the heading container
    var nextEl = aboutHeading.parentElement.nextElementSibling;
    if (nextEl) {
        var p = nextEl.querySelector('p');
        if (p) {
            return p.textContent.trim();
        }
    }

    return '';
})();
"""


def extract_about(driver, timeout=10):
    """
    Extract the About/summary section text from the current profile page.

    Uses JavaScript with semantic selectors:
    1. Finds <h2> with "About" / "À propos" text
    2. Targets <span data-testid="expandable-text-box"> for actual content
    No hashed class names.

    Args:
        driver: Selenium WebDriver (already on a profile page)
        timeout: seconds to wait

    Returns:
        str: About text, or empty string if not found
    """
    try:
        # Scroll to about section using h2 heading text
        heading = None
        for text in ("About", "À propos", "A propos"):
            try:
                xpath = f"//h2[normalize-space(text())='{text}']"
                heading = driver.find_element("xpath", xpath)
                break
            except Exception:
                continue

        if heading:
            scroll_to_element(driver, heading)
            time.sleep(1)

        result = driver.execute_script(_ABOUT_JS)
        text = result.strip() if result else ""

        if text:
            logger.info("About extracted (%d chars)", len(text))
        return text

    except Exception as e:
        logger.error("Error extracting about section: %s", e)
        return ""
