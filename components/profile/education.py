"""
Profile Education Component — extracts all education entries from LinkedIn profile pages.

Uses semantic/structural selectors only (heading text, <figure> for logos,
/school/ links, componentkey attributes) — never hashed class names.
"""
import logging
from components.common.scrolling import scroll_to_element

logger = logging.getLogger(__name__)

_EDUCATION_JS = r"""
(function() {
    // 1. Find the Education section by <h2> text
    var h2s = document.querySelectorAll('h2');
    var eduHeading = null;
    for (var i = 0; i < h2s.length; i++) {
        var txt = h2s[i].textContent.trim().toLowerCase();
        if (txt === 'education' || txt === 'formation' || txt === 'éducat') {
            eduHeading = h2s[i];
            break;
        }
    }
    if (!eduHeading) return [];

    // 2. Get the section container
    var section = eduHeading.parentElement;
    while (section && !section.tagName.match(/^(DIV|SECTION)$/)) {
        section = section.parentElement;
        if (!section) return [];
    }

    // 3. Find all education entries — they are divs with componentkey
    //    inside the section (flat structure, no <ul> like Experience)
    var items = section.querySelectorAll('[componentkey]');
    if (items.length === 0) return [];

    var results = [];

    for (var idx = 0; idx < items.length; idx++) {
        var item = items[idx];
        var school = '';
        var degree = '';
        var field = '';
        var dates = '';

        // Find school: link to /school/ or figure aria-label
        var schoolLink = item.querySelector('a[href*="/school/"]');
        if (schoolLink) {
            school = schoolLink.textContent.trim();
        } else {
            var figure = item.querySelector('figure img[aria-label], figure img[alt]');
            if (figure) {
                var label = figure.getAttribute('aria-label') || figure.getAttribute('alt') || '';
                school = label.replace(/\s*logo\s*$/i, '').trim();
            }
        }

        // Get all <p> elements and parse them
        var paragraphs = item.querySelectorAll('p');
        for (var p = 0; p < paragraphs.length; p++) {
            var txt = paragraphs[p].textContent.trim();
            if (!txt) continue;

            // Skip school name if already found
            if (school && txt === school) continue;

            // Check if it looks like a date (contains year)
            if (txt.match(/\d{4}/)) {
                dates = txt;
                continue;
            }

            // First paragraph with comma is likely "Degree, Field"
            if (!degree && txt.match(/,/)) {
                var parts = txt.split(',');
                degree = parts[0].trim();
                field = parts.slice(1).join(',').trim();
                continue;
            }

            // Otherwise it could be just a degree or field
            if (!degree && txt.length > 3) {
                degree = txt;
                continue;
            }
        }

        results.push({
            school: school || '',
            degree: degree || '',
            field: field || '',
            dates: dates || ''
        });
    }

    return results;
})();
"""


def _extract_all_education(driver):
    """
    Core extractor — finds Education section and returns all entries.

    Args:
        driver: Selenium WebDriver (already on a profile page)

    Returns:
        list[dict] with keys: school, degree, field, dates
    """
    try:
        # Scroll to education section using h2 heading text
        heading = None
        for text in ("Education", "Formation", "Éducation"):
            try:
                xpath = f"//h2[normalize-space(text())='{text}']"
                heading = driver.find_element("xpath", xpath)
                break
            except Exception:
                continue

        if heading:
            scroll_to_element(driver, heading)
            import time
            time.sleep(1)

        results = driver.execute_script(_EDUCATION_JS)
        return results or []

    except Exception as e:
        logger.error("Error extracting education: %s", e)
        return []


def extract_all_education(driver):
    """
    Extract all education entries from the current profile page.

    Args:
        driver: Selenium WebDriver (already on a profile page)

    Returns:
        list[dict] with keys: school, degree, field, dates
    """
    return _extract_all_education(driver)
