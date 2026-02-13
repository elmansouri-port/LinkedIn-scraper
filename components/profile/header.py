"""
Profile Header Component — name extraction from LinkedIn profile pages.
"""
import logging
from components.selectors import ProfileSelectors
from components.common.waits import find_with_fallback

logger = logging.getLogger(__name__)


def extract_name(driver, timeout=15):
    """
    Extract first name, last name, and full name from the current profile page.
    Tries multiple selectors to handle LinkedIn layout variations.

    Args:
        driver:  Selenium WebDriver (already on a profile page)
        timeout: seconds to wait

    Returns:
        dict with keys: first_name, last_name, full_name

    Raises:
        ValueError if name cannot be extracted
    """
    try:
        name_element = find_with_fallback(
            driver, ProfileSelectors.NAME_FALLBACKS, timeout=timeout
        )
        full_name = name_element.text.strip()

        if not full_name:
            raise ValueError("Empty name extracted")

        # Split name into first and last
        name_parts = full_name.split()

        if len(name_parts) == 0:
            raise ValueError("Empty name")
        elif len(name_parts) == 1:
            first_name = name_parts[0]
            last_name = ""
        elif len(name_parts) == 2:
            first_name = name_parts[0]
            last_name = name_parts[1]
        else:
            # For names with more than 2 parts, take first as first_name
            # and rest as last_name (e.g., "Youssef El Mansouri" -> "Youssef", "El Mansouri")
            first_name = name_parts[0]
            last_name = " ".join(name_parts[1:])

        return {
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
        }

    except Exception as e:
        raise ValueError(f"Could not extract profile name: {e}")
