#!/usr/bin/env python3
"""
Standalone debug script for experience extraction.
Run: python debug_experience.py <profile_url>
"""
import sys
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("debug_experience")

# ── Selenium + project imports ──────────────────────────────────
from selenium.webdriver.common.by import By
from core.driver_manager import DriverManager
from auth.auth_manager import AuthManager
from config.scraper_config import LINKEDIN_EMAIL, LINKEDIN_PASSWORD
from components.common.navigation import navigate_to
from components.common.scrolling import scroll_to_element

# ────────────────────────────────────────────────────────────────
# ── 1. EXTRACTION LOGIC (copied from components/profile/experience.py) ──
# ────────────────────────────────────────────────────────────────

MATCHES = ['experience', 'expérience', 'experiences', 'expériences']
SCROLL_PX = 800
SCROLL_PAUSE = 1.2
MAX_SCROLL_ATTEMPTS = 3

EXTRACT_JS = r"""
(function() {
    try {
        // 1. Find the Experience heading
        var h2s = document.querySelectorAll('h2');
        var heading = null;
        var matches = ['experience', 'expérience', 'experiences', 'expériences'];
        for (var i = 0; i < h2s.length; i++) {
            var txt = h2s[i].textContent.trim().toLowerCase();
            for (var m = 0; m < matches.length; m++) {
                if (txt.indexOf(matches[m]) !== -1) { heading = h2s[i]; break; }
            }
            if (heading) break;
        }
        if (!heading) return [];

        // 2. Find container that holds the experience items
        var container = heading.closest('section');
        if (!container || !container.querySelector('[componentkey*="entity-collection-item"]')) {
            container = heading.parentElement;
            while (container) {
                if (container.querySelector('[componentkey*="entity-collection-item"]')) break;
                container = container.parentElement;
                if (!container || container.tagName === 'BODY') { container = document; break; }
            }
        }

        // 3. Find entity-collection-item groups
        var groups = container.querySelectorAll('[componentkey*="entity-collection-item"]');
        if (groups.length === 0 && container !== document) {
            groups = document.querySelectorAll('[componentkey*="entity-collection-item"]');
        }

        var results = [];
        var TYPE_RE = /^(full|part|contract|freelance|self|permanent|cdi|cdd|apprenticeship|internship|stage|alternance)/i;

        for (var g = 0; g < groups.length; g++) {
            var group = groups[g];

            var logoImg = group.querySelector('a[href*="/company/"] figure img[alt]');
            var company = logoImg ? logoImg.getAttribute('alt').replace(/\s*logo\s*$/i, '').trim() : '';
            if (!company) {
                var links = group.querySelectorAll('a[href*="/company/"]');
                if (links.length >= 2) {
                    company = links[1].textContent.trim().split('\n')[0].trim();
                }
            }

            var lis = group.querySelectorAll('ul li');
            if (lis.length === 0) {
                var title = '', dates = '', desc = '';
                var ps = group.querySelectorAll('p');
                for (var p = 0; p < ps.length; p++) {
                    var txt = ps[p].textContent.trim();
                    if (!txt || (company && txt === company)) continue;
                    if (txt.match(/skills/i)) continue;
                    if (!title && !txt.match(/\d{4}/) && !txt.match(TYPE_RE)) { title = txt; continue; }
                    if (!dates && txt.match(/\d{4}/)) { dates = txt; continue; }
                }
                var exp = group.querySelector('[data-testid="expandable-text-box"]');
                if (exp) desc = exp.textContent.trim().replace(/\s*\.\.\.\s*more\s*$/i, '').trim();
                if (title || company) results.push({title: title, company: company, dates: dates, location: '', description: desc});
            } else {
                for (var l = 0; l < lis.length; l++) {
                    var li = lis[l];
                    var title = '', dates = '', desc = '';
                    var ps = li.querySelectorAll('p');
                    for (var p = 0; p < ps.length; p++) {
                        var txt = ps[p].textContent.trim();
                        if (!txt || (company && txt === company)) continue;
                        if (txt.match(/skills/i)) continue;
                        if (!title && !txt.match(/\d{4}/) && !txt.match(TYPE_RE)) { title = txt; continue; }
                        if (!dates && txt.match(/\d{4}/)) { dates = txt; continue; }
                    }
                    var exp = li.querySelector('[data-testid="expandable-text-box"]');
                    if (exp) desc = exp.textContent.trim().replace(/\s*\.\.\.\s*more\s*$/i, '').trim();
                    if (title || company) results.push({title: title, company: company, dates: dates, location: '', description: desc});
                }
            }
        }

        return results;
    } catch(e) {
        return [];
    }
})()
"""


def scroll_to_load(driver):
    """Scroll down incrementally to trigger lazy-loading, check for heading."""
    logger.info("=" * 60)
    logger.info("STEP: Scroll to load experience section")
    for attempt in range(1, MAX_SCROLL_ATTEMPTS + 1):
        found = driver.execute_script(f"""
            var h2s = document.querySelectorAll('h2');
            var matches = {MATCHES};
            for (var i = 0; i < h2s.length; i++) {{
                var txt = h2s[i].textContent.trim().toLowerCase();
                for (var m = 0; m < matches.length; m++) {{
                    if (txt.indexOf(matches[m]) !== -1) return true;
                }}
            }}
            return false;
        """)
        if found:
            logger.info("  -> Found experience heading (attempt %d/%d)", attempt, MAX_SCROLL_ATTEMPTS)
            return True
        px = SCROLL_PX * attempt
        logger.info("  -> Scroll %d/%d: %dpx", attempt, MAX_SCROLL_ATTEMPTS, px)
        driver.execute_script(f"window.scrollBy(0, {px});")
        time.sleep(SCROLL_PAUSE)

    # Final check
    found = driver.execute_script(f"""
        var h2s = document.querySelectorAll('h2');
        var matches = {MATCHES};
        for (var i = 0; i < h2s.length; i++) {{
            var txt = h2s[i].textContent.trim().toLowerCase();
            for (var m = 0; m < matches.length; m++) {{
                if (txt.indexOf(matches[m]) !== -1) return true;
            }}
        }}
        return false;
    """)
    logger.info("  -> Final check: heading found = %s", found)
    return found


def extract_experiences(driver):
    """Full extraction pipeline with debug output at every step."""
    logger.info("=" * 60)
    logger.info("STEP: Extract experiences")

    # ─── 1. Scroll ───
    scroll_to_load(driver)

    # ─── 2. Log all h2 texts ───
    logger.info("=" * 60)
    logger.info("STEP: H2 texts on page")
    h2s = driver.execute_script("""
        var h2s = document.querySelectorAll('h2');
        var out = [];
        for (var i = 0; i < h2s.length && i < 20; i++) {
            out.push(h2s[i].textContent.trim());
        }
        return out;
    """)
    for i, t in enumerate(h2s):
        logger.info("  [%d] '%s'", i, t)

    # ─── 3. Heading check ───
    logger.info("=" * 60)
    logger.info("STEP: Check heading and company links")

    heading_info = driver.execute_script("""
        var h2s = document.querySelectorAll('h2');
        var matches = ['experience', 'expérience', 'experiences', 'expériences'];
        for (var i = 0; i < h2s.length; i++) {
            var txt = h2s[i].textContent.trim().toLowerCase();
            for (var m = 0; m < matches.length; m++) {
                if (txt.indexOf(matches[m]) !== -1) {
                    return {found: true, text: txt, tag: h2s[i].tagName, class: (h2s[i].className || '').substring(0, 60)};
                }
            }
        }
        return {found: false};
    """)
    logger.info("  Heading: %s", heading_info)

    # ─── 4. Entity-collection-item count ───
    all_entities = driver.execute_script("""
        return document.querySelectorAll('[componentkey*="entity-collection-item"]').length;
    """)
    logger.info("  Total entity-collection-item on page: %d", all_entities)

    # ─── 5. Container walking debug ───
    logger.info("=" * 60)
    logger.info("STEP: Container walk-up debug")
    container_debug = driver.execute_script("""
        var h2s = document.querySelectorAll('h2');
        var heading = null;
        var matches = ['experience', 'expérience', 'experiences', 'expériences'];
        for (var i = 0; i < h2s.length; i++) {
            var txt = h2s[i].textContent.trim().toLowerCase();
            for (var m = 0; m < matches.length; m++) {
                if (txt.indexOf(matches[m]) !== -1) { heading = h2s[i]; break; }
            }
            if (heading) break;
        }
        if (!heading) return {error: 'no_heading'};

        // Try closest section
        var section = heading.closest('section');
        var debug = {
            headingTag: heading.tagName,
            headingParentTag: heading.parentElement ? heading.parentElement.tagName : 'none',
        };
        if (section) {
            debug.closestSectionTag = section.tagName;
            debug.closestSectionClass = (section.className || '').substring(0, 80);
            debug.sectionEntityCount = section.querySelectorAll('[componentkey*="entity-collection-item"]').length;
            debug.sectionCompanyLinks = section.querySelectorAll('a[href*="/company/"]').length;
        } else {
            debug.closestSectionTag = null;
        }

        // Walk up from parent
        var walk = [];
        var el = heading.parentElement;
        var depth = 0;
        while (el && el.tagName !== 'BODY' && depth < 10) {
            walk.push({
                tag: el.tagName,
                id: el.id || '',
                classPreview: (el.className || '').substring(0, 50),
                hasEntityItems: el.querySelectorAll('[componentkey*="entity-collection-item"]').length,
                hasCompanyLinks: el.querySelectorAll('a[href*="/company/"]').length,
                children: el.children.length
            });
            el = el.parentElement;
            depth++;
        }
        debug.walkPath = walk;

        // Also check each entity-collection-item to see which section it's in
        var entities = document.querySelectorAll('[componentkey*="entity-collection-item"]');
        debug.totalEntities = entities.length;
        debug.entitySections = [];
        for (var e = 0; e < entities.length && e < 10; e++) {
            var ent = entities[e];
            var parentSection = ent.closest('section');
            var parentHeading = ent.closest('h2');
            debug.entitySections.push({
                index: e,
                sectionTag: parentSection ? parentSection.tagName : 'none',
                sectionClass: parentSection ? (parentSection.className || '').substring(0, 40) : 'none',
                hasCompanyLink: ent.querySelector('a[href*="/company/"]') !== null,
                // First p text for identification
                firstP: (ent.querySelector('p') || {}).textContent || ''
            });
        }

        return debug;
    """)
    for k, v in sorted(container_debug.items()):
        logger.info("  %s: %s", k, v)

    # ─── 6. Company links ───
    logger.info("=" * 60)
    logger.info("STEP: Company links on page")
    company_debug = driver.execute_script("""
        var links = document.querySelectorAll('a[href*="/company/"]');
        var out = [];
        for (var i = 0; i < links.length && i < 10; i++) {
            out.push({
                href: links[i].getAttribute('href'),
                text: links[i].textContent.trim().substring(0, 80),
                imgAlt: (links[i].querySelector('figure img[alt]') || {}).alt || ''
            });
        }
        return out;
    """)
    for c in company_debug:
        logger.info("  href=%s", c.get("href", ""))
        logger.info("    text='%s'", c.get("text", ""))
        logger.info("    imgAlt='%s'", c.get("imgAlt", ""))

    # ─── 7. Run the extraction JS ───
    logger.info("=" * 60)
    logger.info("STEP: Run EXTRACT_JS")
    results = driver.execute_script(EXTRACT_JS)
    results = results or []

    logger.info("  Results count: %d", len(results))
    for i, r in enumerate(results):
        logger.info("  [%d] title='%s' company='%s' dates='%s' desc_len=%d",
            i, r.get("title", ""), r.get("company", ""), r.get("dates", ""), len(r.get("description", "")))

    return results


# ────────────────────────────────────────────────────────────────
# ── 2. MAIN — driver setup, login, navigate, extract ──────────
# ────────────────────────────────────────────────────────────────

LOGIN_CHECK_SELECTORS = [
    "[data-test-id='nav-user-profile']",
    ".global-nav__primary-link-me-menu-trigger",
    "a.nav__profile__member-photo",
    "img.global-nav__me-photo",
]


def _is_logged_in(driver):
    """Check if already logged into LinkedIn."""
    try:
        driver.get("https://www.linkedin.com")
        time.sleep(2)
        for sel in LOGIN_CHECK_SELECTORS:
            elements = driver.find_elements(By.CSS_SELECTOR, sel)
            if elements:
                logger.info("Already logged in (detected via '%s')", sel)
                return True
        # Also check URL
        if "/feed/" in driver.current_url or "linkedin.com/in/" in driver.current_url:
            logger.info("Already logged in (detected via URL: %s)", driver.current_url)
            return True
        return False
    except Exception as e:
        logger.warning("Login check failed: %s", e)
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_experience.py <profile_url>")
        sys.exit(1)

    profile_url = sys.argv[1]
    logger.info("=" * 60)
    logger.info("DEBUG EXPERIENCE EXTRACTION")
    logger.info("Profile URL: %s", profile_url)
    logger.info("=" * 60)

    # ─── Driver setup ───
    logger.info("Setting up Chrome driver...")
    driver, profile_dir = DriverManager.setup_chrome_driver()
    logger.info("Driver ready (profile: %s)", profile_dir)

    # ─── Login check — only login if needed ───
    if not _is_logged_in(driver):
        logger.info("Not logged in, attempting login...")
        auth_manager = AuthManager(email=LINKEDIN_EMAIL, password=LINKEDIN_PASSWORD)
        if not auth_manager.login(driver):
            logger.error("Login failed!")
            driver.quit()
            sys.exit(1)
        logger.info("Login OK")
    else:
        logger.info("Skipping login — already authenticated")

    # ─── Navigate ───
    logger.info("Navigating to profile...")
    navigate_to(driver, profile_url, wait_seconds=3)
    time.sleep(2)

    # ─── Extract ───
    results = extract_experiences(driver)

    # ─── Print summary ───
    logger.info("=" * 60)
    logger.info("SUMMARY: %d experience entries found", len(results))
    for i, r in enumerate(results):
        logger.info("  [%d] %s @ %s (%s)", i, r.get("title"), r.get("company"), r.get("dates"))

    # ─── Cleanup ───
    DriverManager.cleanup_driver(driver, profile_dir)
    logger.info("Done.")


if __name__ == "__main__":
    main()
