"""
Profile Experience Component — extracts all experiences from LinkedIn profile pages.

Relies on the caller (profile_scraper.py) having already scrolled to reveal
lazy-loaded sections.  If the Experience heading is absent from the DOM,
returns an empty list immediately instead of blocking on redundant scrolls.
"""
import logging
from selenium.common.exceptions import JavascriptException

logger = logging.getLogger(__name__)


def _extract_all_experiences(driver, timeout=15):
    """
    Core extractor — finds Experience section and returns all entries.
    Step-by-step: each JS call is tiny and individually logged.
    """
    logger.info("=" * 60)
    logger.info("STEP: _extract_all_experiences — start")

    # ────────────────────────────────────────────────────────────
    # STEP 1 — Find the Experience <h2> index
    # ────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 1: Find Experience <h2> index")
    MATCH_WORDS = ['experience', 'expérience', 'experiences', 'expériences']
    heading_index = -1
    heading_text = ""
    try:
        h2_data = driver.execute_script("""
            var out = [];
            document.querySelectorAll('h2').forEach(function(h) {
                out.push(h.textContent.trim());
            });
            return out;
        """) or []
        for i, t in enumerate(h2_data):
            tl = t.lower()
            for m in MATCH_WORDS:
                if m in tl:
                    heading_index = i
                    heading_text = t
                    break
            if heading_index >= 0:
                break
    except JavascriptException as e:
        logger.error("  STEP 1 JS error: %s", e)
        return []

    if heading_index < 0:
        logger.error("  STEP 1 FAIL: no Experience <h2> found among %d h2s", len(h2_data))
        for i, t in enumerate(h2_data):
            logger.info("    h2[%d] = '%s'", i, t)
        return []
    logger.info("  STEP 1 OK: h2[%d] = '%s'", heading_index, heading_text)

    # ────────────────────────────────────────────────────────────
    # STEP 2 — Walk up DOM from heading, max 15 levels
    # ────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 2: Walk up DOM from heading (max 15 levels)")
    container_found = False
    container_level = -1

    for depth in range(15):
        try:
            info = driver.execute_script("""
                var h2s = document.querySelectorAll('h2');
                var heading = h2s[arguments[0]];
                var el = heading;
                for (var d = 0; d <= arguments[1]; d++) {
                    if (!el || el.tagName === 'BODY') return {atBody: true, tag: 'BODY'};
                    if (d > 0) el = el.parentElement;
                    if (!el) return {atBody: true, tag: 'BODY'};
                }
                var count = el.querySelectorAll('[componentkey*="entity-collection-item"]').length;
                return {
                    depth: arguments[1],
                    tag: el.tagName,
                    id: el.id || '',
                    classPreview: (el.className || '').substring(0, 50),
                    entityCount: count,
                    atBody: false
                };
            """, heading_index, depth)
        except JavascriptException as e:
            logger.error("  STEP 2 depth %d JS error: %s", depth, e)
            continue

        if info.get("atBody"):
            logger.info("  STEP 2 depth=%d: reached BODY, stopping", depth)
            break

        logger.info("  STEP 2 depth=%d: tag=%s  id='%s'  class='%s'  entity-items=%d",
            info.get("depth"), info.get("tag"), info.get("id"),
            info.get("classPreview"), info.get("entityCount"))

        if info.get("entityCount", 0) > 0:
            container_found = True
            container_level = depth
            logger.info("  STEP 2 FOUND container at depth=%d (tag=%s)", depth, info.get("tag"))
            break

    if not container_found:
        logger.error("  STEP 2 FAIL: no container found after 15 levels")
        return []

    # ────────────────────────────────────────────────────────────
    # STEP 3 — Get full raw innerHTML of the container
    # ────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 3: Grab full innerHTML of container (depth=%d)", container_level)
    try:
        html = driver.execute_script("""
            var h2s = document.querySelectorAll('h2');
            var heading = h2s[arguments[0]];
            var el = heading;
            for (var d = 0; d <= arguments[1]; d++) {
                if (d > 0) el = el.parentElement;
            }
            return el.innerHTML;
        """, heading_index, container_level)
    except JavascriptException as e:
        logger.error("  STEP 3 JS error: %s", e)
        return []

    logger.info("  STEP 3 innerHTML length: %d chars", len(html or ""))
    logger.info("  STEP 3 innerHTML content:")
    logger.info("  ---BEGIN CONTAINER HTML---")
    for line in (html or "").split("\n"):
        logger.info("  %s", line)
    logger.info("  ---END CONTAINER HTML---")

    # ────────────────────────────────────────────────────────────
    # STEP 4 — Count entity-collection-items inside container
    # ────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 4: Count entity-collection-item elements in container")
    try:
        count = driver.execute_script("""
            var h2s = document.querySelectorAll('h2');
            var heading = h2s[arguments[0]];
            var el = heading;
            for (var d = 0; d <= arguments[1]; d++) {
                if (d > 0) el = el.parentElement;
            }
            return el.querySelectorAll('[componentkey*="entity-collection-item"]').length;
        """, heading_index, container_level)
    except JavascriptException as e:
        logger.error("  STEP 4 JS error: %s", e)
        return []

    item_count = count or 0
    logger.info("  STEP 4: entity-collection-item count = %d", item_count)
    if item_count == 0:
        logger.warning("  STEP 4 WARNING: zero items found in container — nothing to extract")
        return []

    # ────────────────────────────────────────────────────────────
    # STEP 5 — For each item, extract raw p tag texts
    # ────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 5: Extract raw <p> texts from each item")

    all_texts = []
    for idx in range(item_count):
        try:
            extracted_texts = driver.execute_script("""
                var h2s = document.querySelectorAll('h2');
                var heading = h2s[arguments[0]];
                var el = heading;
                for (var d = 0; d <= arguments[1]; d++) {
                    if (d > 0) el = el.parentElement;
                }
                var items = el.querySelectorAll('[componentkey*="entity-collection-item"]');
                var item = items[arguments[2]];
                var out = [];
                
                var visibleElements = item.querySelectorAll('span[aria-hidden="true"]');
                if (visibleElements.length > 0) {
                    visibleElements.forEach(function(el) {
                        var t = el.textContent.trim();
                        if (t) out.push(t);
                    });
                } else {
                    var fallbacks = item.querySelectorAll('p, h3, h4');
                    fallbacks.forEach(function(el) {
                        var t = el.textContent.trim();
                        if (t) out.push(t);
                    });
                }
                return out;
            """, heading_index, container_level, idx)
        except JavascriptException as e:
            logger.error("  STEP 5 item %d JS error: %s", idx, e)
            continue

        texts = extracted_texts or []
        all_texts.append(texts)
        logger.info("  STEP 5 item[%d] raw texts (%d): %s", idx, len(texts), texts)

    if not all_texts:
        logger.error("  STEP 5 FAIL: no item texts could be extracted")
        return []

    # ────────────────────────────────────────────────────────────
    # STEP 6 — Map texts to fields in Python (Intelligent Rule-Based)
    # ────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 6: Map raw texts -> fields dynamically")

    def has_date_range(s):
        return ' - ' in s or 'Present' in s or 'aujourd’hui' in s.lower()
        
    def is_duration_only(s):
        s_lower = s.lower()
        return (' yr' in s_lower or ' mo' in s_lower or ' an' in s_lower or ' mois' in s_lower) and not has_date_range(s)

    results = []
    for idx, texts in enumerate(all_texts):
        cleaned = [t.strip() for t in texts if t.strip()]
        if not cleaned:
            continue
            
        date_range_idx = -1
        for i, t in enumerate(cleaned):
            if has_date_range(t):
                date_range_idx = i
                break
                
        duration_only_idx = -1
        for i in range(min(3, len(cleaned))):
            if is_duration_only(cleaned[i]):
                duration_only_idx = i
                break
                
        if duration_only_idx == 1 or duration_only_idx == 2:
            # Multi-role item
            company = cleaned[0]
            if ' · ' in company:
                company = company.split(' · ')[0]
                
            role_start_idx = duration_only_idx + 1
            while role_start_idx < len(cleaned):
                role_date_idx = -1
                for j in range(role_start_idx, min(role_start_idx + 4, len(cleaned))):
                    if has_date_range(cleaned[j]):
                        role_date_idx = j
                        break
                        
                if role_date_idx != -1:
                    title = " ".join(cleaned[role_start_idx:role_date_idx])
                    if ' · ' in title:
                        title = title.split(' · ')[0]
                        
                    dates = cleaned[role_date_idx]
                    location = ""
                    
                    next_idx = role_date_idx + 1
                    if next_idx < len(cleaned) and len(cleaned[next_idx]) < 60 and not has_date_range(cleaned[next_idx]) and not is_duration_only(cleaned[next_idx]):
                        location = cleaned[next_idx]
                        role_start_idx = next_idx + 1
                    else:
                        role_start_idx = next_idx
                    
                    entry = {
                        "title": title,
                        "company": company,
                        "dates": dates,
                        "location": location,
                        "description": ""
                    }
                    results.append(entry)
                    logger.info("  STEP 6 Multi-Role: title='%s' company='%s' dates='%s' location='%s'", 
                        entry["title"], entry["company"], entry["dates"], entry["location"])
                else:
                    break
        else:
            # Single-role item
            if date_range_idx != -1:
                title = " ".join(cleaned[0:date_range_idx-1]) if date_range_idx > 0 else cleaned[0]
                company = cleaned[date_range_idx-1] if date_range_idx > 0 else ""
                
                if ' · ' in title:
                    title = title.split(' · ')[0]
                if ' · ' in company:
                    company = company.split(' · ')[0]
                    
                dates = cleaned[date_range_idx]
                location = ""
                if date_range_idx + 1 < len(cleaned):
                    location = cleaned[date_range_idx + 1]
                    
                entry = {
                    "title": title,
                    "company": company,
                    "dates": dates,
                    "location": location,
                    "description": ""
                }
            else:
                entry = {
                    "title": cleaned[0] if len(cleaned) > 0 else "",
                    "company": cleaned[1] if len(cleaned) > 1 else "",
                    "dates": cleaned[2] if len(cleaned) > 2 else "",
                    "location": cleaned[3] if len(cleaned) > 3 else "",
                    "description": ""
                }
            results.append(entry)
            logger.info("  STEP 6 Single-Role item[%d]: title='%s' company='%s' dates='%s' location='%s'",
                idx, entry["title"], entry["company"], entry["dates"], entry["location"])

    # ────────────────────────────────────────────────────────────
    # STEP 7 — Summary and return
    # ────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 7: %d entries extracted", len(results))

    return results


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
