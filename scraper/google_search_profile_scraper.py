"""
Google LinkedIn Profile Scraper v3.4
High-performance scraper using standard logging.

Features:
- BATCH extraction (all profiles from page at once)
- Per-action logging to both console and files
- Resume functionality (ask to resume or start over)
- Performance timing for debugging
- Source location tracking in logs
"""
import logging
import sqlite3
import json
import time
import re
import random
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, StaleElementReferenceException
from urllib.parse import urlparse
import os
import sys
from typing import Optional, Dict, List, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config.scraper_config import GoogleScraperConfig, DATA_DIR, DB_DIR, LOGS_DIR
    CONFIG_LOADED = True
except ImportError:
    CONFIG_LOADED = False

try:
    from utils.logger import SessionState, get_logger
    LOGGER_LOADED = True
except ImportError:
    LOGGER_LOADED = False

# Custom SUCCESS level (registered once in utils/logger.py, but safe to re-register)
SUCCESS_LEVEL = 25


class GoogleLinkedInProfileScraper:
    """Google LinkedIn Profile Scraper."""

    ACTION_NAME = "google_scraper"

    def __init__(self, driver, max_pages_per_keyword: int = None, verbose: bool = True,
                 progress_callback=None, log_callback=None):
        """Initialize scraper.

        Args:
            driver: Selenium WebDriver
            max_pages_per_keyword: Max pages per keyword (default: 10)
            verbose: Enable detailed logging
            progress_callback: optional callable(pct: int) for live progress reporting
            log_callback: optional callable(level: str, message: str) for live log streaming
        """
        self.driver = driver
        self.verbose = verbose

        # Directories
        if CONFIG_LOADED:
            self.config = GoogleScraperConfig
            self.data_dir = str(DATA_DIR)
            self.db_dir = str(DB_DIR)
            self.logs_dir = str(LOGS_DIR)
        else:
            self.config = None
            self.data_dir = "data"
            self.db_dir = os.path.join(self.data_dir, "db")
            self.logs_dir = os.path.join(self.data_dir, "logs")

        os.makedirs(self.db_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs("data/sessions", exist_ok=True)

        # Standard logger (uses centralized logging if available)
        if LOGGER_LOADED:
            self.logger = get_logger(f"scraper.{self.ACTION_NAME}")
        else:
            self.logger = logging.getLogger(f"scraper.{self.ACTION_NAME}")

        # Session state for resume
        self.session = SessionState(self.ACTION_NAME) if LOGGER_LOADED else None

        # Configuration
        if self.config:
            self.page_timeout = self.config.PAGE_LOAD_TIMEOUT
            self.element_timeout = self.config.ELEMENT_WAIT_TIMEOUT
            self.min_delay = self.config.MIN_DELAY
            self.max_delay = self.config.MAX_DELAY
            self.page_delay = self.config.PAGE_DELAY
            self.max_pages_per_keyword = max_pages_per_keyword or self.config.DEFAULT_MAX_PAGES_PER_KEYWORD
            self.dup_ratio_threshold = self.config.DUPLICATE_RATIO_THRESHOLD
            self.consecutive_bad_pages = self.config.CONSECUTIVE_BAD_PAGES
            self.results_per_page = self.config.RESULTS_PER_PAGE
            self.linkedin_domain = self.config.LINKEDIN_DOMAIN
        else:
            self.page_timeout = 5
            self.element_timeout = 3
            self.min_delay = 0.3
            self.max_delay = 1.0
            self.page_delay = 0.5
            self.max_pages_per_keyword = max_pages_per_keyword or 10
            self.dup_ratio_threshold = 0.7
            self.consecutive_bad_pages = 2
            self.results_per_page = 20
            self.linkedin_domain = "linkedin.com"

        # Profile tracking
        self.profiles_scraped = 0
        self.profiles_saved = 0
        self.scraped_urls = set()

        # Statistics
        self.stats = {
            "keywords_processed": 0,
            "keywords_skipped_duplicates": 0,
            "total_pages_scraped": 0,
            "duplicate_urls_found": 0,
            "no_more_pages_count": 0,
            "errors": 0,
        }

        self._popup_handled = False
        self.db_path = None
        self._timers: Dict[str, float] = {}
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self._last_reported_pct = -1

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------

    def log(self, message: str, *args, level: str = "info"):
        """Log message via standard logging.

        Supports both old style and new printf-style:
            log("text", "debug")        # old: level as 2nd positional arg
            log("text %s", val)         # new: printf formatting
            log("text %s", val, level="debug")  # new: explicit kwarg
        """
        # Handle old calling convention: log(message, level_str)
        if len(args) == 1 and isinstance(args[0], str) and args[0] in (
            "debug", "info", "warning", "error", "success",
        ):
            level = args[0]
            args = ()

        # Strip leading/trailing whitespace for clean log output
        message = message.strip()

        if args:
            message = message % args

        if level == "success":
            self.logger.log(SUCCESS_LEVEL, message)
        elif level == "debug":
            self.logger.debug(message)
        elif level == "warning":
            self.logger.warning(message)
        elif level == "error":
            self.logger.error(message)
        else:
            self.logger.info(message)

        if self.log_callback and level != "debug":
            try:
                self.log_callback(level, message)
            except Exception:
                pass

    def start_timer(self, name: str):
        """Start a performance timer."""
        self._timers[name] = time.time()

    def stop_timer(self, name: str) -> float:
        """Stop a performance timer and return duration in seconds."""
        if name in self._timers:
            duration = time.time() - self._timers[name]
            self.logger.debug("Timer %s: %.2fs", name, duration)
            return duration
        return 0.0

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def check_resume(self, keywords: str, oblig_keywords: str) -> Optional[Dict]:
        """Check if there's a session to resume.

        Returns:
            Resume state or None to start fresh.
        """
        if not self.session or not self.session.exists():
            return None

        state = self.session.load()
        if not state:
            return None

        # If the keywords changed, clear the old session and start fresh.
        # This is the API-safe path — no input() needed.
        current_kws = sorted(kw.strip() for kw in keywords.split(",") if kw.strip())
        saved_kws = sorted(state.get("keywords_list", []))
        if current_kws != saved_kws or state.get("oblig_keywords", "").strip() != oblig_keywords.strip():
            self.log("Keywords changed — clearing old session and starting fresh")
            self.session.clear()
            return None

        if self.session.ask_resume():
            if "scraped_urls" in state:
                self.scraped_urls = set(state["scraped_urls"])
                self.log("Loaded %d previously scraped URLs", len(self.scraped_urls))
            self.profiles_saved = state.get("profiles_saved", 0)
            self.stats = state.get("stats", self.stats)
            return state

        return None

    def save_session(self, current_keyword: str, current_keyword_idx: int,
                     keywords_list: List[str], oblig_keywords: str):
        """Save current session state for resume."""
        if not self.session:
            return

        self.session.save(
            current_keyword=current_keyword,
            current_keyword_idx=current_keyword_idx,
            keywords_list=keywords_list,
            oblig_keywords=oblig_keywords,
            profiles_saved=self.profiles_saved,
            scraped_urls=list(self.scraped_urls)[-1000:],
            stats=self.stats,
            db_path=self.db_path,
        )

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------

    def create_database(self, keywords: str, oblig_keywords: str = "", db_path: str = None) -> str:
        """Use unified database (defaults to shared linkedin_scraper.db)."""
        from core.database import DB_PATH, init_db

        if db_path and os.path.exists(db_path):
            self.db_path = db_path
            self.log("Reusing database: %s", os.path.basename(db_path))
        else:
            init_db()
            self.db_path = DB_PATH
            self.log("Using unified database: %s", os.path.basename(DB_PATH))

        return self.db_path

    def save_profiles_batch(self, profiles: List[Dict], search_keyword: str,
                            all_keywords: str) -> tuple:
        """Save multiple profiles to unified database. Returns (saved, duplicates)."""
        from core.database import save_search_profiles_batch

        if not profiles:
            return 0, 0

        db_profiles = []
        already_scraped = 0

        for profile_data in profiles:
            profile_url = profile_data.get("profile_url")
            if profile_url in self.scraped_urls:
                already_scraped += 1
                self.log(f"  ~ Dup: {profile_data.get('name', 'Unknown')}", "debug")
                continue

            db_profiles.append({
                "profile_url": profile_url,
                "name": profile_data.get("name", ""),
                "title": profile_data.get("title", ""),
                "company": profile_data.get("company", ""),
                "location": profile_data.get("location", ""),
                "description": profile_data.get("description", ""),
                "search_keyword": search_keyword,
                "all_keywords": all_keywords,
            })

        saved_count, duplicate_count = save_search_profiles_batch(db_profiles, db_path=self.db_path)

        # Track scraped URLs
        for p in db_profiles:
            self.scraped_urls.add(p["profile_url"])

        self.profiles_saved += saved_count
        self.profiles_scraped += saved_count
        self.stats["duplicate_urls_found"] += duplicate_count + already_scraped

        return saved_count, duplicate_count + already_scraped

    # ------------------------------------------------------------------
    # Page interaction
    # ------------------------------------------------------------------

    def _handle_consent_popup(self):
        """Handle Google consent popup."""
        from components.search.google_utils import handle_consent_popup
        handled = handle_consent_popup(self.driver)
        if handled:
            self.log("Consent popup handled", "debug")
        return handled

    def _check_and_handle_captcha(self) -> bool:
        """Check for CAPTCHA/sorry page and wait for manual solve.

        Returns:
            True if page is accessible (no CAPTCHA or solved), False if timeout.
        """
        from components.search.google_utils import (
            is_captcha_page,
            is_consent_popup,
            wait_for_captcha_manual_solve,
            handle_consent_popup,
        )

        # Try consent popup first
        if is_consent_popup(self.driver):
            self.log("Consent popup detected, attempting auto-dismiss", "warning")
            if not handle_consent_popup(self.driver):
                self.log("Please click 'Accept' on the consent popup", "warning")
                time.sleep(30)

        # Check for CAPTCHA
        if is_captcha_page(self.driver):
            self.log("CAPTCHA detected on Google search", "warning")
            solved = wait_for_captcha_manual_solve(self.driver, timeout=300)
            if not solved:
                self.log("CAPTCHA solve timeout - cannot continue", "error")
                return False

        return True

    def _has_next_page(self) -> bool:
        """Check if there is a next page available."""
        from components.search.google_utils import has_next_page
        return has_next_page(self.driver)

    def _go_to_next_page(self) -> bool:
        """Navigate to the next page."""
        from components.search.google_utils import go_to_next_page
        return go_to_next_page(self.driver)

    def _extract_all_profiles_from_page(self) -> List[Dict]:
        """Extract all LinkedIn profiles from current Google search page."""
        profiles = []
        self.start_timer("page_extraction")

        try:
            js_code = """
            var seen = {};
            var profiles = [];
            var results = document.querySelectorAll('.MjjYud, .g');

            results.forEach(function(result) {
                var link = result.querySelector('a[href*="linkedin.com/in/"]');
                if (!link) return;

                var url = link.href;
                if (!url || url.indexOf('/in/') === -1) return;

                url = url.split('?')[0].replace(/\\/+$/, '');
                if (seen[url]) return;
                seen[url] = true;

                var h3 = result.querySelector('h3');
                var rawName = h3 ? h3.textContent.trim() : '';
                rawName = rawName
                    .replace(/\\s*[\\|\\-–—]\\s*LinkedIn.*$/i, '')
                    .replace(/\\s*LinkedIn\\s*$/i, '')
                    .trim();

                var name = rawName.split(/\\s*[\\|–—]\\s*/)[0].split(/\\s*-\\s*/)[0].trim();

                var snippet = result.querySelector('.VwiC3b, .YrbPuc, [data-sncf]');
                var text = snippet ? snippet.textContent.trim() : '';

                var title = '', location = '', company = '', description = '';

                if (text.indexOf(' \\u00B7 ') > -1) {
                    var parts = text.split(' \\u00B7 ');
                    if (parts.length >= 3) {
                        location = parts[0] || '';
                        var titleCompany = parts.slice(1).join(' \\u00B7 ');
                        var atMatch = titleCompany.match(/^(.+?)\\s+(?:at|chez|bei|bij|en|\\u00E0)\\s+(.+)$/i);
                        if (atMatch) {
                            title = atMatch[1].trim();
                            company = atMatch[2].trim();
                        } else {
                            title = parts[1] || '';
                            company = parts[2] || '';
                        }
                    } else if (parts.length === 2) {
                        var atMatch2 = parts[1].match(/^(.+?)\\s+(?:at|chez|bei|bij|en|\\u00E0)\\s+(.+)$/i);
                        if (atMatch2) {
                            location = parts[0] || '';
                            title = atMatch2[1].trim();
                            company = atMatch2[2].trim();
                        } else {
                            title = parts[0] || '';
                            company = parts[1] || '';
                        }
                    }
                    description = text.substring(0, 500);
                } else {
                    description = text.substring(0, 500);
                }

                profiles.push({
                    url: url,
                    name: name,
                    title: title.substring(0, 200),
                    company: company.substring(0, 200),
                    location: location.substring(0, 200),
                    description: description
                });
            });

            return profiles;
            """

            results = self.driver.execute_script(js_code)

            for item in results:
                url = item.get("url", "").rstrip("/")
                name = item.get("name", "").strip()

                if not url or "/in/" not in url:
                    continue
                if not name or len(name) < 2:
                    continue

                profiles.append({
                    "profile_url": url,
                    "name": name,
                    "title": item.get("title", "").strip(),
                    "company": item.get("company", "").strip(),
                    "location": item.get("location", "").strip(),
                    "description": item.get("description", "").strip(),
                })

        except Exception as e:
            self.log(f"Extraction error: {e}", "warning")
            self.stats["errors"] += 1

        self.stop_timer("page_extraction")
        return profiles

    def _has_next_page(self) -> bool:
        """Check if next page exists."""
        try:
            next_btn = self.driver.find_element(By.CSS_SELECTOR, "a#pnnext")
            return next_btn.is_displayed()
        except Exception:
            return False

    def _go_to_next_page(self) -> bool:
        """Navigate to next page."""
        try:
            next_btn = self.driver.find_element(By.CSS_SELECTOR, "a#pnnext")
            href = next_btn.get_attribute("href")
            if href:
                self.driver.get(href)
                time.sleep(self.page_delay)
                return True
        except Exception:
            pass
        return False

    # ------------------------------------------------------------------
    # Scraping logic
    # ------------------------------------------------------------------

    def scrape_single_keyword(self, keyword: str, oblig_keywords: str,
                              max_profiles_per_keyword: int, total_max_profiles: int,
                              all_keywords: str) -> int:
        """Scrape profiles for a single keyword."""
        from urllib.parse import quote_plus

        self.start_timer(f"keyword_{keyword}")

        base_query = f"site:{self.linkedin_domain}/in {keyword.strip()}"

        if oblig_keywords.strip():
            oblig_phrase = f'"{oblig_keywords.strip()}"'
            search_query = f"{base_query} {oblig_phrase}"
        else:
            search_query = base_query

        self.log("Keyword: '%s' | Query: %s", keyword.strip(), search_query)

        google_url = f"https://www.google.com/search?q={quote_plus(search_query)}&num={self.results_per_page}"

        profiles_found = 0

        try:
            self.start_timer("page_load")
            self.driver.get(google_url)
            self.stop_timer("page_load")

            # Handle CAPTCHA / consent popup
            if not self._check_and_handle_captcha():
                self.log("CAPTCHA not solved - cannot continue", "error")
                self.stats["errors"] += 1
                return 0

            # Also try consent popup if not already handled
            if not self._popup_handled:
                self._handle_consent_popup()
                self._popup_handled = True

            # Wait for search results to load
            try:
                WebDriverWait(self.driver, self.page_timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#search"))
                )
            except TimeoutException:
                self.log("Search results did not load", "error")
                self.stats["errors"] += 1
                return 0

            page_num = 1
            consecutive_high_dup_pages = 0

            while (profiles_found < max_profiles_per_keyword and
                   self.profiles_saved < total_max_profiles and
                   page_num <= self.max_pages_per_keyword):

                self.stats["total_pages_scraped"] += 1

                page_profiles = self._extract_all_profiles_from_page()

                if not page_profiles:
                    self.log(f"  Page {page_num}: No results", "warning")
                    break

                remaining = min(
                    max_profiles_per_keyword - profiles_found,
                    total_max_profiles - self.profiles_saved,
                )
                profiles_to_save = page_profiles[:remaining]

                saved, dupes = self.save_profiles_batch(profiles_to_save, keyword.strip(), all_keywords)
                profiles_found += saved

                total_on_page = saved + dupes
                dup_ratio = dupes / total_on_page if total_on_page > 0 else 0

                self.log("  Page %d: +%d new, %d dupes (%.0f%%)", page_num, saved, dupes, dup_ratio * 100)

                if self.progress_callback and total_max_profiles > 0:
                    pct = min(95, int(self.profiles_saved / total_max_profiles * 100))
                    if pct != self._last_reported_pct:
                        self._last_reported_pct = pct
                        try:
                            self.progress_callback(pct)
                        except Exception:
                            pass

                if dup_ratio >= self.dup_ratio_threshold:
                    consecutive_high_dup_pages += 1
                    if consecutive_high_dup_pages >= self.consecutive_bad_pages:
                        self.log("  High duplicate ratio - skipping to next keyword", "warning")
                        self.stats["keywords_skipped_duplicates"] += 1
                        break
                else:
                    consecutive_high_dup_pages = 0

                if profiles_found >= max_profiles_per_keyword:
                    self.log("  Target reached!", "success")
                    break

                if self.profiles_saved >= total_max_profiles:
                    self.log("  Total target reached!", "success")
                    break

                if not self._has_next_page():
                    self.stats["no_more_pages_count"] += 1
                    break

                if not self._go_to_next_page():
                    break

                # Re-check for CAPTCHA after each page navigation
                if not self._check_and_handle_captcha():
                    self.log("CAPTCHA not solved on page %d - stopping", page_num + 1, level="error")
                    self.stats["errors"] += 1
                    break

                page_num += 1

            self.log("  %d profiles from %d page%s", profiles_found, page_num, "" if page_num == 1 else "s")

        except Exception as e:
            self.log(f"Error: {e}", "error")
            self.stats["errors"] += 1

        self.stop_timer(f"keyword_{keyword}")
        return profiles_found

    def scrape_google_page(self, keywords_str: str, oblig_keywords: str,
                           max_profiles: int, max_profiles_per_keyword: int) -> Dict:
        """Main scraping function. Returns a results dict."""
        start_time = datetime.now()

        self.log("=" * 50)
        self.log("GOOGLE LINKEDIN SCRAPER v3.4")
        self.log("=" * 50)

        keywords_list = [kw.strip() for kw in keywords_str.split(",") if kw.strip()]

        start_idx = 0
        resume_state = self.check_resume(keywords_str, oblig_keywords)

        if resume_state:
            start_idx = resume_state.get("current_keyword_idx", 0)
            if resume_state.get("db_path"):
                self.db_path = resume_state["db_path"]
            self.log(f"Resuming from keyword {start_idx + 1}")

        self.log("Keywords: %s", keywords_list)
        self.log("Obligatory: %s", oblig_keywords if oblig_keywords.strip() else "None")
        self.log("Target: %d total, %d/keyword", max_profiles, max_profiles_per_keyword)
        self.log("-" * 50)

        for idx, keyword in enumerate(keywords_list[start_idx:], start_idx + 1):
            if self.profiles_saved >= max_profiles:
                self.log(f"Total target ({max_profiles}) reached!", "success")
                break

            self.log("\n[%d/%d] Processing keyword...", idx, len(keywords_list))

            self.scrape_single_keyword(
                keyword, oblig_keywords,
                max_profiles_per_keyword,
                max_profiles,
                keywords_str,
            )

            self.stats["keywords_processed"] += 1

            self.save_session(keyword, idx, keywords_list, oblig_keywords)

        # Summary
        duration = datetime.now() - start_time
        duration_str = str(duration).split(".")[0]
        rate = f"{self.profiles_saved / (duration.total_seconds() / 60):.1f}/min" if duration.total_seconds() > 0 else "N/A"

        self.log("=" * 50)
        self.log(f"COMPLETED in {duration_str}", "success")
        self.log("=" * 50)

        self.log("Statistics:")
        self.log("  Profiles saved: %d", self.profiles_saved)
        self.log("  Keywords processed: %d/%d", self.stats["keywords_processed"], len(keywords_list))
        self.log("  Pages scraped: %d", self.stats["total_pages_scraped"])
        self.log("  Duplicates: %d", self.stats["duplicate_urls_found"])
        self.log("  Errors: %d", self.stats["errors"])
        self.log("  Rate: %s", rate)

        self.log("Database: %s", self.db_path)

        # Clear session on success
        if self.session and self.profiles_saved >= max_profiles:
            self.session.clear()

        # Read profiles from unified database
        all_profiles = []
        if self.db_path and os.path.exists(self.db_path):
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT profile_url, name, title, company, location, description, search_keyword, scraped_at "
                    "FROM search_profiles ORDER BY id"
                )
                for row in cursor.fetchall():
                    all_profiles.append({
                        "profile_url": row[0],
                        "name": row[1] or "",
                        "title": row[2] or "",
                        "company": row[3] or "",
                        "location": row[4] or "",
                        "description": row[5] or "",
                        "search_keyword": row[6] or "",
                        "scraped_at": row[7] or "",
                    })
                conn.close()
            except Exception as e:
                self.log(f"Error reading profiles from DB: {e}", "warning")

        return {
            "profiles": all_profiles,
            "profiles_saved": self.profiles_saved,
            "stats": {
                **self.stats,
                "duration": duration_str,
                "rate": rate,
            },
            "db_path": self.db_path,
        }

    @staticmethod
    def scrape_google_linkedin_profiles(driver, keywords: str, oblig_keywords: str,
                                        max_profiles: int, max_profiles_per_keyword: int,
                                        duplicate_threshold: int = 3,
                                        max_pages_per_keyword: int = 10,
                                        verbose: bool = True,
                                        db_path: str = None,
                                        progress_callback=None,
                                        log_callback=None) -> Dict:
        """Entry point for scraping.

        Args:
            db_path: optional path to a shared database; when provided the same DB
            is reused across multiple calls (single session).
            progress_callback: optional callable(pct: int) for live progress updates.
            log_callback: optional callable(level: str, message: str) for live log streaming.

        Returns:
            dict with keys: success, profiles, profiles_saved, stats, db_path, error
        """
        try:
            scraper = GoogleLinkedInProfileScraper(
                driver,
                max_pages_per_keyword=max_pages_per_keyword,
                verbose=verbose,
                progress_callback=progress_callback,
                log_callback=log_callback,
            )

            scraper.create_database(keywords, oblig_keywords, db_path=db_path)
            result = scraper.scrape_google_page(keywords, oblig_keywords, max_profiles, max_profiles_per_keyword)

            return {"success": True, **result}

        except Exception as e:
            import traceback
            logging.getLogger(__name__).error("Scrape failed: %s", e, exc_info=True)
            return {
                "success": False,
                "profiles": [],
                "profiles_saved": 0,
                "stats": {},
                "db_path": None,
                "error": str(e),
            }
