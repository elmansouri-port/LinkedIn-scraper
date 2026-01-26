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
from urllib.parse import urljoin, urlparse
import os

class GoogleLinkedInProfileScraper:
    """
    High-Performance Google LinkedIn Profile Scraper v3.0
    
    Features:
    - BATCH extraction (all profiles from page at once)
    - Minimal delays for maximum speed
    - Smart duplicate detection (ratio-based, not count-based)
    - Verbose mode toggle for debugging
    - Intelligent page navigation
    """
    
    # Configuration constants
    DEFAULT_MAX_PAGES_PER_KEYWORD = 10
    DUPLICATE_RATIO_THRESHOLD = 0.7      # Skip keyword if >70% duplicates
    CONSECUTIVE_BAD_PAGES = 2            # Skip after N consecutive high-duplicate pages
    PAGE_LOAD_TIMEOUT = 5                # Fast timeout (was 8)
    ELEMENT_WAIT_TIMEOUT = 3             # Wait for elements (was implicit)
    
    def __init__(self, driver, max_pages_per_keyword=None, verbose=True):
        """
        Initialize scraper.
        
        Args:
            driver: Selenium WebDriver
            max_pages_per_keyword: Max pages to scrape per keyword (default: 10)
            verbose: Enable detailed logging (default: True)
        """
        self.driver = driver
        self.verbose = verbose
        self.data_dir = "data"
        self.db_dir = os.path.join(self.data_dir, "db")
        self.logs_dir = os.path.join(self.data_dir, "logs")
        
        os.makedirs(self.db_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # Profile tracking
        self.profiles_scraped = 0
        self.profiles_saved = 0
        self.scraped_urls = set()
        
        # Configuration
        self.max_pages_per_keyword = max_pages_per_keyword or self.DEFAULT_MAX_PAGES_PER_KEYWORD
        
        # Statistics
        self.stats = {
            'keywords_processed': 0,
            'keywords_skipped_due_to_duplicates': 0,
            'total_pages_scraped': 0,
            'duplicate_urls_found': 0,
            'no_more_pages_count': 0
        }
        
        self._popup_handled = False
    
    def log(self, message, force=False):
        """Print message only if verbose mode is on or force=True"""
        if self.verbose or force:
            print(message)
    
    def create_database(self, keywords, oblig_keywords=""):
        """Create SQLite database for storing LinkedIn profiles"""
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
        
        conn.commit()
        conn.close()
        
        print(f"📁 Database: {db_name}")
        return self.db_path

    def save_profiles_batch(self, profiles, search_keyword, all_keywords):
        """
        BATCH SAVE: Insert multiple profiles at once.
        Returns (saved_count, duplicate_count)
        """
        saved_count = 0
        duplicate_count = 0
        
        if not profiles:
            return 0, 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for profile_data in profiles:
            profile_url = profile_data.get('profile_url')
            
            # Skip if already in memory cache
            if profile_url in self.scraped_urls:
                duplicate_count += 1
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
                    self.log(f"      + {profile_data.get('name', 'Unknown')}")
                else:
                    duplicate_count += 1
                    
            except sqlite3.Error:
                duplicate_count += 1
        
        conn.commit()
        conn.close()
        
        self.profiles_saved += saved_count
        self.profiles_scraped += saved_count
        self.stats['duplicate_urls_found'] += duplicate_count
        
        return saved_count, duplicate_count

    def _handle_google_popup(self):
        """Handle Google consent popup - fast check"""
        try:
            selectors = [
                "button#L2AGLb",
                "button[aria-label*='Accept']",
                "button[aria-label*='Accepter']",
                "button[aria-label*='Tout accepter']"
            ]
            
            for selector in selectors:
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if btn.is_displayed():
                        btn.click()
                        self.log("✅ Popup handled")
                        time.sleep(0.5)
                        return True
                except NoSuchElementException:
                    continue
        except Exception:
            pass
        return False

    def _wait_for_results(self):
        """Wait for search results to load - optimized"""
        try:
            WebDriverWait(self.driver, self.PAGE_LOAD_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#search"))
            )
            return True
        except TimeoutException:
            return False

    def _extract_all_profiles_from_page(self):
        """
        FAST BATCH EXTRACTION: Get all LinkedIn profile data from current page.
        Returns list of profile dictionaries.
        """
        profiles = []
        
        try:
            # Find all search result containers
            containers = self.driver.find_elements(By.CSS_SELECTOR, ".MjjYud, .g")
            
            for container in containers:
                try:
                    # Find LinkedIn link
                    link = container.find_element(By.CSS_SELECTOR, "a[href*='linkedin.com/in/']")
                    url = link.get_attribute('href')
                    
                    if not url or 'linkedin.com/in/' not in url.lower():
                        continue
                    
                    # Clean URL
                    parsed = urlparse(url)
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')
                    
                    # Extract name from h3
                    name = ""
                    try:
                        h3 = container.find_element(By.CSS_SELECTOR, "h3")
                        name = h3.text.split(' - ')[0].split(' | ')[0].split(' – ')[0].strip()
                    except:
                        pass
                    
                    # Extract snippet info
                    title = ""
                    location = ""
                    company = ""
                    description = ""
                    
                    try:
                        snippet = container.find_element(By.CSS_SELECTOR, ".VwiC3b, .YrbPuc")
                        text = snippet.text.strip()
                        
                        if ' · ' in text:
                            parts = text.split(' · ')
                            if len(parts) >= 1:
                                location = parts[0].strip()
                            if len(parts) >= 2:
                                title = parts[1].strip()
                            if len(parts) >= 3:
                                company = parts[2].strip()
                        else:
                            description = text[:300]
                    except:
                        pass
                    
                    profiles.append({
                        'profile_url': clean_url,
                        'name': name,
                        'title': title,
                        'company': company,
                        'location': location,
                        'description': description
                    })
                    
                except (NoSuchElementException, StaleElementReferenceException):
                    continue
                    
        except Exception as e:
            self.log(f"   ⚠️ Extraction error: {e}")
        
        return profiles

    def _has_next_page(self):
        """Quick check if next page exists"""
        try:
            next_btn = self.driver.find_element(By.CSS_SELECTOR, "a#pnnext")
            return next_btn.is_displayed()
        except:
            return False

    def _go_to_next_page(self):
        """Navigate to next page - direct URL navigation for speed"""
        try:
            next_btn = self.driver.find_element(By.CSS_SELECTOR, "a#pnnext")
            href = next_btn.get_attribute('href')
            if href:
                self.driver.get(href)
                time.sleep(0.5)  # Minimal delay
                return True
        except:
            pass
        return False

    def scrape_single_keyword(self, keyword, oblig_keywords, max_profiles_per_keyword, total_max_profiles, all_keywords):
        """
        OPTIMIZED: Scrape profiles for a single keyword.
        Uses ratio-based duplicate detection instead of count-based.
        """
        from urllib.parse import quote_plus
        
        # Build search query
        base_query = f'site:linkedin.com/in/ {keyword.strip()}'
        
        if oblig_keywords.strip():
            oblig_words = [w.strip() for w in oblig_keywords.split() if w.strip()]
            oblig_query = ' '.join([f'+{w}' for w in oblig_words])
            search_query = f'{base_query} {oblig_query}'
        else:
            search_query = base_query
        
        print(f"\n🔍 [{keyword.strip()}] Target: {max_profiles_per_keyword} profiles")
        
        google_url = f"https://www.google.com/search?q={quote_plus(search_query)}&num=20"
        
        try:
            self.driver.get(google_url)
            
            # Handle popup only once
            if not self._popup_handled:
                time.sleep(1)
                self._handle_google_popup()
                self._popup_handled = True
            
            # Wait for page
            if not self._wait_for_results():
                print(f"   ❌ Page load failed")
                return 0
            
            page_num = 1
            profiles_found = 0
            consecutive_high_dup_pages = 0
            
            while (profiles_found < max_profiles_per_keyword and 
                   self.profiles_saved < total_max_profiles and
                   page_num <= self.max_pages_per_keyword):
                
                self.stats['total_pages_scraped'] += 1
                
                # BATCH EXTRACT
                page_profiles = self._extract_all_profiles_from_page()
                
                if not page_profiles:
                    self.log(f"   Page {page_num}: No results")
                    break
                
                # Calculate how many we need
                remaining = min(
                    max_profiles_per_keyword - profiles_found,
                    total_max_profiles - self.profiles_saved
                )
                profiles_to_save = page_profiles[:remaining]
                
                # BATCH SAVE
                saved, dupes = self.save_profiles_batch(profiles_to_save, keyword.strip(), all_keywords)
                profiles_found += saved
                
                # Calculate duplicate ratio for this page
                total_on_page = saved + dupes
                dup_ratio = dupes / total_on_page if total_on_page > 0 else 0
                
                print(f"   Page {page_num}: +{saved} new, {dupes} dupes ({dup_ratio:.0%})")
                
                # Smart duplicate detection: ratio-based
                if dup_ratio >= self.DUPLICATE_RATIO_THRESHOLD:
                    consecutive_high_dup_pages += 1
                    if consecutive_high_dup_pages >= self.CONSECUTIVE_BAD_PAGES:
                        print(f"   ⚠️ {self.CONSECUTIVE_BAD_PAGES} pages with >{self.DUPLICATE_RATIO_THRESHOLD:.0%} duplicates - moving to next keyword")
                        self.stats['keywords_skipped_due_to_duplicates'] += 1
                        break
                else:
                    consecutive_high_dup_pages = 0  # Reset if good page
                
                # Check targets
                if profiles_found >= max_profiles_per_keyword:
                    self.log(f"   ✅ Keyword target reached!")
                    break
                
                if self.profiles_saved >= total_max_profiles:
                    print(f"   ✅ Total target reached!")
                    break
                
                # Next page
                if not self._has_next_page():
                    self.log(f"   📄 No more pages")
                    self.stats['no_more_pages_count'] += 1
                    break
                
                if not self._go_to_next_page():
                    break
                
                page_num += 1
            
            print(f"   ✅ Total: {profiles_found} profiles from {page_num} page(s)")
            return profiles_found
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return profiles_found if 'profiles_found' in locals() else 0

    def scrape_google_page(self, keywords_str, oblig_keywords, max_profiles, max_profiles_per_keyword):
        """Main scraping function - iterates through keywords"""
        start_time = datetime.now()
        
        print(f"\n{'='*60}")
        print(f"🚀 GOOGLE LINKEDIN SCRAPER v3.0")
        print(f"{'='*60}")
        
        keywords_list = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
        
        print(f"Keywords: {keywords_list}")
        print(f"Obligatory: {oblig_keywords if oblig_keywords.strip() else 'None'}")
        print(f"Target: {max_profiles} total, {max_profiles_per_keyword}/keyword")
        print(f"Verbose: {'ON' if self.verbose else 'OFF'}")
        print(f"{'='*60}")
        
        for idx, keyword in enumerate(keywords_list, 1):
            if self.profiles_saved >= max_profiles:
                print(f"\n🎉 Total target ({max_profiles}) reached!")
                break
            
            print(f"\n{'─'*40}")
            print(f"📍 Keyword {idx}/{len(keywords_list)}")
            
            self.scrape_single_keyword(
                keyword, oblig_keywords,
                max_profiles_per_keyword,
                max_profiles,
                keywords_str
            )
            
            self.stats['keywords_processed'] += 1
        
        # Summary
        duration = datetime.now() - start_time
        
        print(f"\n{'='*60}")
        print(f"🎉 COMPLETED in {duration}")
        print(f"{'='*60}")
        print(f"📊 Profiles saved: {self.profiles_saved}")
        print(f"📊 Keywords: {self.stats['keywords_processed']}/{len(keywords_list)}")
        print(f"📊 Pages scraped: {self.stats['total_pages_scraped']}")
        print(f"📊 Duplicates: {self.stats['duplicate_urls_found']}")
        
        if self.profiles_saved > 0 and duration.total_seconds() > 0:
            rate = self.profiles_saved / (duration.total_seconds() / 60)
            print(f"📊 Rate: {rate:.1f} profiles/min")
        
        print(f"📁 Database: {self.db_path}")
        print(f"{'='*60}\n")

    @staticmethod
    def scrape_google_linkedin_profiles(driver, keywords, oblig_keywords, max_profiles,
                                        max_profiles_per_keyword, duplicate_threshold=3,
                                        max_pages_per_keyword=10, verbose=True):
        """
        Entry point function for scraping Google LinkedIn profiles.
        
        Args:
            driver: Selenium WebDriver
            keywords: Comma-separated keywords
            oblig_keywords: Space-separated obligatory keywords
            max_profiles: Maximum total profiles
            max_profiles_per_keyword: Maximum per keyword
            duplicate_threshold: (deprecated, uses ratio-based now)
            max_pages_per_keyword: Max pages per keyword (default: 10)
            verbose: Enable detailed logging (default: True)
        """
        try:
            scraper = GoogleLinkedInProfileScraper(
                driver,
                max_pages_per_keyword=max_pages_per_keyword,
                verbose=verbose
            )
            
            scraper.create_database(keywords, oblig_keywords)
            scraper.scrape_google_page(keywords, oblig_keywords, max_profiles, max_profiles_per_keyword)
            
            return True
            
        except Exception as e:
            print(f"❌ Scraping failed: {e}")
            import traceback
            traceback.print_exc()
            return False