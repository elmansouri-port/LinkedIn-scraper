"""
Profile Experience Component — extracts all experiences from LinkedIn profile pages.

Uses semantic/structural selectors only (heading text, <ul>, <li>, <figure>,
componentkey attributes) — never hashed class names that LinkedIn changes.
"""
import time
import logging
import re
from components.common.scrolling import scroll_to_element

logger = logging.getLogger(__name__)

# JavaScript extractor — finds Experience section by heading text,
# then walks the DOM structurally to get every experience entry.
_EXPERIENCE_JS = r"""
(function() {
    // 1. Find the Experience section by <h2> text (English or French)
    var h2s = document.querySelectorAll('h2');
    var expHeading = null;
    for (var i = 0; i < h2s.length; i++) {
        var txt = h2s[i].textContent.trim().toLowerCase();
        if (txt === 'experience' || txt === 'expérience' || txt === 'experiences') {
            expHeading = h2s[i];
            break;
        }
    }
    if (!expHeading) return [];

    // 2. Get the section container (parent that holds all experience items)
    var section = expHeading.parentElement;
    // Walk up until we find the container with multiple experience items
    while (section && !section.querySelector('ul, [componentkey*="entity-collection-item"]')) {
        section = section.parentElement;
        if (!section) return [];
    }

    var results = [];

    // 3. Find all experience items — they are <li> elements inside <ul>
    //    OR divs with componentkey starting with "entity-collection-item"
    var items = [];
    var uls = section.querySelectorAll('ul');
    for (var u = 0; u < uls.length; u++) {
        var lis = uls[u].querySelectorAll('li');
        for (var l = 0; l < lis.length; l++) {
            items.push(lis[l]);
        }
    }

    // Also check for flat entries (divs with componentkey)
    var collectionItems = section.querySelectorAll('[componentkey*="entity-collection-item"]');
    for (var c = 0; c < collectionItems.length; c++) {
        var ci = collectionItems[c];
        // If this item is NOT already inside a <ul>, treat it as a flat entry
        if (!ci.closest('ul')) {
            items.push(ci);
        }
    }

    if (items.length === 0) return [];

    // 4. Extract data from each item
    for (var idx = 0; idx < items.length; idx++) {
        var item = items[idx];
        var title = '';
        var company = '';
        var dates = '';
        var location = '';
        var description = '';

        // Get all <p> elements inside this item
        var paragraphs = item.querySelectorAll('p');

        // Find company name: look for a link to /company/ or figure aria-label
        var companyLink = item.querySelector('a[href*="/company/"]');
        if (companyLink) {
            company = companyLink.textContent.trim();
        } else {
            var figure = item.querySelector('figure img[aria-label], figure img[alt]');
            if (figure) {
                var label = figure.getAttribute('aria-label') || figure.getAttribute('alt') || '';
                // Remove " logo" suffix
                company = label.replace(/\s*logo\s*$/i, '').trim();
            }
        }

        // Find company header (for grouped entries — company at top, not inside <li>)
        if (!company) {
            // For grouped entries, the company name is in a sibling <p> before the <ul>
            var parent = item.closest('ul');
            if (parent) {
                var prevSiblings = parent.previousElementSibling;
                if (prevSiblings) {
                    var companyPs = prevSiblings.querySelectorAll('p');
                    for (var cp = 0; cp < companyPs.length; cp++) {
                        var txt = companyPs[cp].textContent.trim();
                        if (txt.length > 0) {
                            // Check if this looks like a company (not a title, not dates)
                            if (!txt.match(/\d{4}/) && !txt.match(/\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)/i)) {
                                company = txt;
                                break;
                            }
                        }
                    }
                }
            }
        }

        // Parse paragraphs: first <p> is title, next contains dates, optional location
        for (var p = 0; p < paragraphs.length; p++) {
            var txt = paragraphs[p].textContent.trim();
            if (!txt) continue;

            // Skip company name if it matches what we already found
            if (company && txt === company) continue;
            // Skip if this paragraph contains "skills" or "+X skills"
            if (txt.match(/skills/i)) continue;

            if (!title) {
                // First meaningful paragraph that doesn't look like dates is the title
                if (!txt.match(/\d{4}/) && !txt.match(/^(Full|Part|Contract|Freelance|Self)/i)) {
                    title = txt;
                    continue;
                }
            }

            if (!dates && txt.match(/\d{4}/)) {
                // Paragraph with year(s) = dates
                dates = txt;
                continue;
            }

            if (!location && !dates) {
                // Could be location if it looks like a place
                if (txt.match(/,/)) {
                    location = txt;
                    continue;
                }
            }
        }

        // Find description: look for expandable text box
        var expandable = item.querySelector('[data-testid="expandable-text-box"]');
        if (expandable) {
            description = expandable.textContent.trim();
            // Remove "... more" or "...more" suffix
            description = description.replace(/\s*\.\.\.\s*more\s*$/i, '').trim();
        }

        // Find location: paragraph after dates that contains comma or city-like text
        if (!location) {
            var allTexts = item.textContent.split('\n');
            for (var t = 0; t < allTexts.length; t++) {
                var line = allTexts[t].trim();
                if (line && line.match(/[\w\s-]+,\s*[\w\s-]+/) && line.length < 80) {
                    if (!line.match(/\d{4}/) && !title && line !== company) {
                        // Skip if it looks like a date
                        if (!line.match(/\d{4}/)) {
                            location = line;
                        }
                    }
                }
            }
        }

        results.push({
            title: title || '',
            company: company || '',
            dates: dates || '',
            location: location || '',
            description: description || ''
        });
    }

    return results;
})();
"""


def _extract_all_experiences(driver, timeout=15):
    """
    Core extractor — finds Experience section and returns all entries.

    Args:
        driver: Selenium WebDriver (already on a profile page)
        timeout: seconds to wait for section to appear

    Returns:
        list[dict] with keys: title, company, dates, location, description
    """
    try:
        # Scroll to experience section using h2 heading text
        heading = None
        for text in ("Experience", "Expérience", "Experiences"):
            try:
                xpath = f"//h2[normalize-space(text())='{text}']"
                heading = driver.find_element("xpath", xpath)
                break
            except Exception:
                continue

        if heading:
            scroll_to_element(driver, heading)
            time.sleep(1.5)

        results = driver.execute_script(_EXPERIENCE_JS)
        return results or []

    except Exception as e:
        logger.error("Error extracting experiences: %s", e)
        return []


def extract_all_experiences(driver):
    """
    Extract all experiences from the current profile page.

    Args:
        driver: Selenium WebDriver (already on a profile page)

    Returns:
        list[dict] with keys: title, company, dates, location, description
    """
    return _extract_all_experiences(driver)


def extract_current_experience(driver):
    """
    Extract the most recent (first) experience entry.

    Args:
        driver: Selenium WebDriver (already on a profile page)

    Returns:
        dict with keys: company (str), job_title (str), dates (str),
              location (str), description (str)
    """
    all_exp = _extract_all_experiences(driver)
    if all_exp:
        latest = all_exp[0]
        return {
            "company": latest.get("company", ""),
            "job_title": latest.get("title", ""),
            "dates": latest.get("dates", ""),
            "location": latest.get("location", ""),
            "description": latest.get("description", ""),
        }
    return {
        "company": "", "job_title": "", "dates": "",
        "location": "", "description": "",
    }


def extract_companies(driver):
    """
    Extract all unique company names from the experience section.

    Args:
        driver: Selenium WebDriver (already on a profile page)

    Returns:
        list[str] of unique company names in order of appearance
    """
    all_exp = _extract_all_experiences(driver)
    companies = []
    seen = set()
    for exp in all_exp:
        company = exp.get("company", "")
        if company and company not in seen:
            seen.add(company)
            companies.append(company)
    return companies
