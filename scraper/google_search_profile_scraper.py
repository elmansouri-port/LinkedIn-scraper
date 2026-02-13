"""
Google LinkedIn Profile Scraper v3.2
High-performance scraper with proper logging and resume functionality.

Features:
- BATCH extraction (all profiles from page at once)
- Proper per-action logging (google_scraper_TIMESTAMP.log)
- Resume functionality (ask to resume or start over)
- Performance timing for debugging
- Source location tracking in logs
"""
import sqlite3
import json
import time
import re
import random
from datetime import datetime
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
    from utils.logger import DevLogger, SessionState
    LOGGER_LOADED = True
except ImportError:
    LOGGER_LOADED = False


class GoogleLinkedInProfileScraper:
    """
    Google LinkedIn Profile Scraper v3.2
    
    Features:
    - Batch extraction for speed
    - Resume functionality
    - Performance timing
    - Proper action-based logging
    """
    
    ACTION_NAME = "google_scraper"
    
    def __init__(self, driver, max_pages_per_keyword: int = None, verbose: bool = True):
        """
        Initialize scraper.
        
        Args:
            driver: Selenium WebDriver
            max_pages_per_keyword: Max pages per keyword (default: 10)
            verbose: Enable detailed logging
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
        
        # Initialize logger with correct action name
        self.logger = None
        if LOGGER_LOADED:
            try:
                self.logger = DevLogger(
                    action_name=self.ACTION_NAME,
                    log_dir=self.logs_dir,
                    console_output=True,
                    file_output=True,
                    verbose=verbose,
                    include_source=True  # For debugging
                )
            except Exception as e:
                print(f"⚠️ Logger init failed: {e}")
        
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
            'keywords_processed': 0,
            'keywords_skipped_duplicates': 0,
            'total_pages_scraped': 0,
            'duplicate_urls_found': 0,
            'no_more_pages_count': 0,
            'errors': 0
        }
        
        self._popup_handled = False
        self.db_path = None
    
    def log(self, message: str, level: str = "info"):
        """Log message with proper level"""
        if self.logger:
            getattr(self.logger, level)(message)
        elif self.verbose or level in ["error", "warning", "success"]:
            emoji = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌", "debug": "🔍"}
            print(f"{emoji.get(level, '')} {message}")
    
    def start_timer(self, name: str):
        """Start a performance timer"""
        if self.logger:
            self.logger.start_timer(name)
    
    def stop_timer(self, name: str):
        """Stop a performance timer"""
        if self.logger:
            self.logger.stop_timer(name)
    
    def check_resume(self, keywords: str, oblig_keywords: str) -> Optional[Dict]:
        """
        Check if there's a session to resume.
        
        Returns:
            Resume state or None to start fresh
        """
        if not self.session or not self.session.exists():
            return None
        
        # Ask user
        if self.session.ask_resume():
            state = self.session.load()
            if state:
                # Load previously scraped URLs to avoid duplicates
                if 'scraped_urls' in state:
                    self.scraped_urls = set(state['scraped_urls'])
                    self.log(f"Loaded {len(self.scraped_urls)} previously scraped URLs", "info")
                
                self.profiles_saved = state.get('profiles_saved', 0)
                self.stats = state.get('stats', self.stats)
                
                return state
        
        return None
    
    def save_session(self, current_keyword: str, current_keyword_idx: int,
                     keywords_list: List[str], oblig_keywords: str):
        """Save current session state for resume"""
        if not self.session:
            return
        
        self.session.save(
            current_keyword=current_keyword,
            current_keyword_idx=current_keyword_idx,
            keywords_list=keywords_list,
            oblig_keywords=oblig_keywords,
            profiles_saved=self.profiles_saved,
            scraped_urls=list(self.scraped_urls)[-1000:],  # Keep last 1000
            stats=self.stats,
            db_path=self.db_path
        )
    
    def create_database(self, keywords: str, oblig_keywords: str = "") -> str:
        """Create SQLite database for storing profiles"""
        import hashlib
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        all_keywords = f"{keywords} {oblig_keywords}".strip()
        keywords_hash = hashlib.md5(all_keywords.encode()).hexdigest()[:8]
        db_name = f"google_li_{keywords_hash}_{timestamp}.db"
        
        self.db_path = os.path.join(self.db_dir, db_name)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_url TEXT UNIQUE NOT NULL,
                name TEXT,
                title TEXT,
                company TEXT,
                location TEXT,
                description TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                search_keyword TEXT,
                all_keywords TEXT
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_profile_url ON profiles(profile_url)')
        conn.commit()
        conn.close()
        
        self.log(f"Database: {db_name}", "info")
        return self.db_path

    def save_profiles_batch(self, profiles: List[Dict], search_keyword: str, 
                            all_keywords: str) -> tuple:
        """Save multiple profiles at once. Returns (saved, duplicates)."""
        saved_count = 0
        duplicate_count = 0
        
        if not profiles:
            return 0, 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for profile_data in profiles:
            profile_url = profile_data.get('profile_url')
            
            if profile_url in self.scraped_urls:
                duplicate_count += 1
                self.log(f"  ~ Dup: {profile_data.get('name', 'Unknown')}", "debug")
                continue
            
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO profiles 
                    (profile_url, name, title, company, location, description, search_keyword, all_keywords)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    profile_url,
                    profile_data.get('name', ''),
                    profile_data.get('title', ''),
                    profile_data.get('company', ''),
                    profile_data.get('location', ''),
                    profile_data.get('description', ''),
                    search_keyword,
                    all_keywords
                ))
                
                if cursor.rowcount > 0:
                    saved_count += 1
                    self.scraped_urls.add(profile_url)
                    self.log(f"  + {profile_data.get('name', 'Unknown')}", "debug")
                else:
                    duplicate_count += 1
                    
            except sqlite3.Error:
                duplicate_count += 1
                self.stats['errors'] += 1
        
        conn.commit()
        conn.close()
        
        self.profiles_saved += saved_count
        self.profiles_scraped += saved_count
        self.stats['duplicate_urls_found'] += duplicate_count
        
        return saved_count, duplicate_count

    def _handle_google_popup(self):
        """Handle Google consent popup — delegates to component."""
        from components.common.popups import handle_google_consent
        handled = handle_google_consent(self.driver)
        if handled:
            self.log("Popup handled", "debug")
        return handled

    def _wait_for_results(self) -> bool:
        """Wait for search results"""
        try:
            WebDriverWait(self.driver, self.page_timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#search"))
            )
            return True
        except TimeoutException:
            return False

    def _extract_all_profiles_from_page(self) -> List[Dict]:
        """
        Extract all LinkedIn profiles from current Google search page.

        Enhanced extraction with:
        - Better name cleaning (strips "LinkedIn", "| LinkedIn", separators)
        - Smarter snippet parsing (handles varying Google snippet formats)
        - In-page URL deduplication
        - Minimum-data validation (skips entries without a URL or name)
        """
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

                // Clean URL — strip query params and trailing slash
                url = url.split('?')[0].replace(/\\/+$/, '');

                // Deduplicate within the same page
                if (seen[url]) return;
                seen[url] = true;

                // ---- Name parsing ----
                var h3 = result.querySelector('h3');
                var rawName = h3 ? h3.textContent.trim() : '';

                // Remove common LinkedIn suffixes from Google titles
                // e.g. "John Doe - Senior Dev | LinkedIn"
                rawName = rawName
                    .replace(/\\s*[\\|\\-–—]\\s*LinkedIn.*$/i, '')   // strip "| LinkedIn" or "- LinkedIn"
                    .replace(/\\s*LinkedIn\\s*$/i, '')                // strip trailing "LinkedIn"
                    .trim();

                // Take the first segment before any remaining separator
                var name = rawName.split(/\\s*[\\|–—]\\s*/)[0].split(/\\s*-\\s*/)[0].trim();

                // ---- Snippet parsing ----
                var snippet = result.querySelector('.VwiC3b, .YrbPuc, [data-sncf]');
                var text = snippet ? snippet.textContent.trim() : '';

                var title = '', location = '', company = '', description = '';

                if (text.indexOf(' · ') > -1) {
                    var parts = text.split(' · ');
                    // Google snippet format varies:
                    //   "Location · Title at Company"
                    //   "Title · Company · Location"
                    //   "Location · 500+ connections · Title"
                    // Strategy: look for " at " keyword to split title/company
                    if (parts.length >= 3) {
                        location = parts[0] || '';
                        // Check if a part contains " at " or " chez "
                        var titleCompany = parts.slice(1).join(' · ');
                        var atMatch = titleCompany.match(/^(.+?)\\s+(?:at|chez|bei|bij|en|à)\\s+(.+)$/i);
                        if (atMatch) {
                            title = atMatch[1].trim();
                            company = atMatch[2].trim();
                        } else {
                            title = parts[1] || '';
                            company = parts[2] || '';
                        }
                    } else if (parts.length === 2) {
                        // Could be "Title - Company" or "Location · Title"
                        var atMatch2 = parts[1].match(/^(.+?)\\s+(?:at|chez|bei|bij|en|à)\\s+(.+)$/i);
                        if (atMatch2) {
                            location = parts[0] || '';
                            title = atMatch2[1].trim();
                            company = atMatch2[2].trim();
                        } else {
                            title = parts[0] || '';
                            company = parts[1] || '';
                        }
                    }
                    // Also capture the full text as description fallback
                    description = text.substring(0, 500);
                } else {
                    description = text.substring(0, 500);
                }

                // Remove "connections" noise from parsed fields
                [title, company, location].forEach(function(val, idx) {
                    if (/^\\d+\\+?\\s+(connections|contacts|abonnés)/i.test(val)) {
                        if (idx === 0) title = '';
                        if (idx === 1) company = '';
                        if (idx === 2) location = '';
                    }
                });

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
                url = item.get('url', '').rstrip('/')
                name = item.get('name', '').strip()

                # Validation: skip entries without a URL or name
                if not url or '/in/' not in url:
                    continue
                if not name or len(name) < 2:
                    continue

                profiles.append({
                    'profile_url': url,
                    'name': name,
                    'title': item.get('title', '').strip(),
                    'company': item.get('company', '').strip(),
                    'location': item.get('location', '').strip(),
                    'description': item.get('description', '').strip(),
                })

        except Exception as e:
            self.log(f"Extraction error: {e}", "warning")
            self.stats['errors'] += 1

        self.stop_timer("page_extraction")
        return profiles

    def _has_next_page(self) -> bool:
        """Check if next page exists"""
        try:
            next_btn = self.driver.find_element(By.CSS_SELECTOR, "a#pnnext")
            return next_btn.is_displayed()
        except:
            return False

    def _go_to_next_page(self) -> bool:
        """Navigate to next page"""
        try:
            next_btn = self.driver.find_element(By.CSS_SELECTOR, "a#pnnext")
            href = next_btn.get_attribute('href')
            if href:
                self.driver.get(href)
                time.sleep(self.page_delay)
                return True
        except:
            pass
        return False

    def scrape_single_keyword(self, keyword: str, oblig_keywords: str, 
                               max_profiles_per_keyword: int, total_max_profiles: int,
                               all_keywords: str) -> int:
        """Scrape profiles for a single keyword"""
        from urllib.parse import quote_plus
        
        self.start_timer(f"keyword_{keyword}")
        
        # Build search query
        # Format: site:linkedin.com/in keyword "obligatory phrase"
        base_query = f'site:{self.linkedin_domain}/in {keyword.strip()}'
        
        if oblig_keywords.strip():
            # Wrap obligatory keywords in quotes as a phrase
            oblig_phrase = f'"{oblig_keywords.strip()}"'
            search_query = f'{base_query} {oblig_phrase}'
        else:
            search_query = base_query
        
        self.log(f"Keyword: '{keyword.strip()}' | Query: {search_query}", "info")
        
        google_url = f"https://www.google.com/search?q={quote_plus(search_query)}&num={self.results_per_page}"
        
        profiles_found = 0
        
        try:
            self.start_timer("page_load")
            self.driver.get(google_url)
            self.stop_timer("page_load")
            
            if not self._popup_handled:
                time.sleep(0.8)
                self._handle_google_popup()
                self._popup_handled = True
            
            if not self._wait_for_results():
                self.log("Page load failed", "error")
                self.stats['errors'] += 1
                return 0
            
            page_num = 1
            consecutive_high_dup_pages = 0
            
            while (profiles_found < max_profiles_per_keyword and 
                   self.profiles_saved < total_max_profiles and
                   page_num <= self.max_pages_per_keyword):
                
                self.stats['total_pages_scraped'] += 1
                
                # Extract profiles
                page_profiles = self._extract_all_profiles_from_page()
                
                if not page_profiles:
                    self.log(f"  Page {page_num}: No results", "warning")
                    break
                
                # Calculate remaining
                remaining = min(
                    max_profiles_per_keyword - profiles_found,
                    total_max_profiles - self.profiles_saved
                )
                profiles_to_save = page_profiles[:remaining]
                
                # Save
                saved, dupes = self.save_profiles_batch(profiles_to_save, keyword.strip(), all_keywords)
                profiles_found += saved
                
                # Duplicate ratio
                total_on_page = saved + dupes
                dup_ratio = dupes / total_on_page if total_on_page > 0 else 0
                
                self.log(f"  Page {page_num}: +{saved} new, {dupes} dupes ({dup_ratio:.0%})", "info")
                
                # Check duplicate threshold
                if dup_ratio >= self.dup_ratio_threshold:
                    consecutive_high_dup_pages += 1
                    if consecutive_high_dup_pages >= self.consecutive_bad_pages:
                        self.log(f"  High duplicate ratio - next keyword", "warning")
                        self.stats['keywords_skipped_duplicates'] += 1
                        break
                else:
                    consecutive_high_dup_pages = 0
                
                if profiles_found >= max_profiles_per_keyword:
                    self.log(f"  Target reached!", "success")
                    break
                
                if self.profiles_saved >= total_max_profiles:
                    self.log(f"  Total target reached!", "success")
                    break
                
                if not self._has_next_page():
                    self.stats['no_more_pages_count'] += 1
                    break
                
                if not self._go_to_next_page():
                    break
                
                page_num += 1
            
            self.log(f"  ✓ {profiles_found} profiles from {page_num} pages", "success")
            
        except Exception as e:
            self.log(f"Error: {e}", "error")
            self.stats['errors'] += 1
        
        self.stop_timer(f"keyword_{keyword}")
        return profiles_found

    def scrape_google_page(self, keywords_str: str, oblig_keywords: str, 
                           max_profiles: int, max_profiles_per_keyword: int) -> Dict:
        """Main scraping function. Returns a results dict."""
        start_time = datetime.now()
        
        self.log("=" * 50, "info")
        self.log("GOOGLE LINKEDIN SCRAPER v3.3", "info")
        self.log("=" * 50, "info")
        
        keywords_list = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
        
        # Check for resume
        start_idx = 0
        resume_state = self.check_resume(keywords_str, oblig_keywords)
        
        if resume_state:
            start_idx = resume_state.get('current_keyword_idx', 0)
            if resume_state.get('db_path'):
                self.db_path = resume_state['db_path']
            self.log(f"Resuming from keyword {start_idx + 1}", "info")
        
        self.log(f"Keywords: {keywords_list}", "info")
        self.log(f"Obligatory: {oblig_keywords if oblig_keywords.strip() else 'None'}", "info")
        self.log(f"Target: {max_profiles} total, {max_profiles_per_keyword}/keyword", "info")
        self.log("-" * 50, "info")
        
        for idx, keyword in enumerate(keywords_list[start_idx:], start_idx + 1):
            if self.profiles_saved >= max_profiles:
                self.log(f"Total target ({max_profiles}) reached!", "success")
                break
            
            self.log(f"\n[{idx}/{len(keywords_list)}] Processing keyword...", "info")
            
            self.scrape_single_keyword(
                keyword, oblig_keywords,
                max_profiles_per_keyword,
                max_profiles,
                keywords_str
            )
            
            self.stats['keywords_processed'] += 1
            
            # Save session for resume
            self.save_session(keyword, idx, keywords_list, oblig_keywords)
        
        # Summary
        duration = datetime.now() - start_time
        duration_str = str(duration).split('.')[0]  # HH:MM:SS
        rate = f"{self.profiles_saved / (duration.total_seconds() / 60):.1f}/min" if duration.total_seconds() > 0 else "N/A"
        
        self.log("=" * 50, "info")
        self.log(f"COMPLETED in {duration_str}", "success")
        self.log("=" * 50, "info")
        
        if self.logger:
            self.logger.log_stats({
                'Profiles saved': self.profiles_saved,
                'Keywords': f"{self.stats['keywords_processed']}/{len(keywords_list)}",
                'Pages scraped': self.stats['total_pages_scraped'],
                'Duplicates': self.stats['duplicate_urls_found'],
                'Errors': self.stats['errors'],
                'Rate': rate
            })
            self.logger.close()
        
        self.log(f"Database: {self.db_path}", "info")
        
        # Clear session on success
        if self.session and self.profiles_saved >= max_profiles:
            self.session.clear()

        # ---- Read profiles from database and return ----
        all_profiles = []
        if self.db_path and os.path.exists(self.db_path):
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT profile_url, name, title, company, location, description, search_keyword, scraped_at FROM profiles ORDER BY id')
                for row in cursor.fetchall():
                    all_profiles.append({
                        'profile_url': row[0],
                        'name': row[1] or '',
                        'title': row[2] or '',
                        'company': row[3] or '',
                        'location': row[4] or '',
                        'description': row[5] or '',
                        'search_keyword': row[6] or '',
                        'scraped_at': row[7] or '',
                    })
                conn.close()
            except Exception as e:
                self.log(f"Error reading profiles from DB: {e}", "warning")

        return {
            'profiles': all_profiles,
            'profiles_saved': self.profiles_saved,
            'stats': {
                **self.stats,
                'duration': duration_str,
                'rate': rate,
            },
            'db_path': self.db_path,
        }

    @staticmethod
    def scrape_google_linkedin_profiles(driver, keywords: str, oblig_keywords: str, 
                                        max_profiles: int, max_profiles_per_keyword: int,
                                        duplicate_threshold: int = 3, 
                                        max_pages_per_keyword: int = 10,
                                        verbose: bool = True) -> Dict:
        """
        Entry point for scraping.

        Returns:
            dict with keys: success, profiles, profiles_saved, stats, db_path, error
        """
        try:
            scraper = GoogleLinkedInProfileScraper(
                driver,
                max_pages_per_keyword=max_pages_per_keyword,
                verbose=verbose
            )
            
            scraper.create_database(keywords, oblig_keywords)
            result = scraper.scrape_google_page(keywords, oblig_keywords, max_profiles, max_profiles_per_keyword)
            
            return {
                'success': True,
                **result,
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'profiles': [],
                'profiles_saved': 0,
                'stats': {},
                'db_path': None,
                'error': str(e),
            }