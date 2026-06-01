"""
LinkedIn Profile Scraper for Profile Enricher
Extracts name, about, all experiences, and education from LinkedIn profiles.

Uses the components layer for element extraction.
"""
import time
import logging
from components.profile.header import extract_name
from components.profile.about import extract_about
from components.profile.experience import extract_all_experiences
from components.profile.education import extract_all_education
from components.common.navigation import navigate_to
from components.common.scrolling import scroll_to_reveal_content

logger = logging.getLogger(__name__)

# Sections we need to find via scrolling
_REQUIRED_SECTIONS = ["experience", "education"]


def scrape_profile_data(driver, profile_url):
    """
    Main function to scrape full profile data.

    Args:
        driver: Selenium WebDriver instance
        profile_url: LinkedIn profile URL

    Returns:
        Dictionary with profile data
    """
    try:
        # Navigate to profile
        navigate_to(driver, profile_url)

        # Scroll to trigger lazy-loaded sections (Experience, Education, etc.)
        logger.info("Scrolling to reveal lazy-loaded sections...")
        scroll_to_reveal_content(driver, target_sections=_REQUIRED_SECTIONS)
        logger.info("Scroll complete — starting extraction")

        # Extract name
        name_data = extract_name(driver, timeout=15)
        logger.info("Name: %s", name_data.get("full_name", "Unknown"))

        time.sleep(1)

        # Extract about section
        about_text = extract_about(driver, timeout=10)
        if about_text:
            logger.info("About extracted (%d chars)", len(about_text))

        time.sleep(1)

        # Extract all experiences
        experiences = extract_all_experiences(driver)
        if experiences:
            logger.info("Extracted %d experience(s)", len(experiences))
            for i, exp in enumerate(experiences):
                logger.info(
                    "  [%d] %s at %s (%s)",
                    i + 1,
                    exp.get("title", ""),
                    exp.get("company", ""),
                    exp.get("dates", ""),
                )

        time.sleep(1)

        # Extract all education
        education = extract_all_education(driver)
        if education:
            logger.info("Extracted %d education(s)", len(education))
            for i, edu in enumerate(education):
                logger.info(
                    "  [%d] %s — %s (%s)",
                    i + 1,
                    edu.get("school", ""),
                    edu.get("degree", ""),
                    edu.get("dates", ""),
                )

        # Get current (most recent) company and title for email generation
        current_exp = experiences[0] if experiences else {}

        # Combine data
        profile_data = {
            **name_data,
            "about": about_text,
            "experiences": experiences,
            "education": education,
            "current_company": current_exp.get("company", ""),
            "current_job_title": current_exp.get("title", ""),
            "url": profile_url,
        }

        return profile_data

    except Exception as e:
        raise Exception(f"Error scraping profile: {str(e)}")
