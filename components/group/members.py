"""
Group Members Component — extracts member data from LinkedIn group pages.

This is the single place for group member element extraction logic.
"""
import logging
from components.selectors import GroupSelectors
from components.common.waits import (
    safe_extract_text,
    safe_extract_attribute,
    element_exists,
)

logger = logging.getLogger(__name__)


def get_member_elements(driver):
    """
    Find all member list items on the current group members page.

    Returns:
        list[WebElement]
    """
    by, value = GroupSelectors.MEMBER_LIST_ITEMS
    return driver.find_elements(by, value)


def get_member_action_rows(driver):
    """
    Find all member action-row elements (used by smart search scraper).

    Returns:
        list[WebElement]
    """
    by, value = GroupSelectors.MEMBER_ACTION_ROW
    return driver.find_elements(by, value)


def extract_member_data(member_element):
    """
    Extract structured data from a single member list-item element.

    Args:
        member_element: WebElement for one member <li>

    Returns:
        dict with keys: name, profile_url, headline, image_url, verified
        Returns None on failure.
    """
    try:
        # Name
        name = safe_extract_text(
            member_element, GroupSelectors.MEMBER_NAME, default=""
        )
        if not name:
            return None

        # Profile URL
        profile_url = safe_extract_attribute(
            member_element, GroupSelectors.MEMBER_PROFILE_LINK, "href",
            default="No profile link"
        )

        # Headline / job title
        headline = safe_extract_text(
            member_element, GroupSelectors.MEMBER_HEADLINE, default="No headline"
        )

        # Profile image
        image_url = safe_extract_attribute(
            member_element, GroupSelectors.MEMBER_IMAGE, "src",
            default="No image"
        )

        # Verified badge
        verified = "Yes" if element_exists(
            member_element, GroupSelectors.MEMBER_BADGE
        ) else "No"

        return {
            "name": name,
            "profile_url": profile_url,
            "headline": headline,
            "image_url": image_url,
            "verified": verified,
        }

    except Exception as e:
        logger.error(f"Error extracting member data: {e}")
        return None
