import sqlite3
import json
import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from urllib.parse import urljoin, urlparse
import os

class GoogleLinkedInProfileScraper:
    def __init__(self, driver):
        self.driver = driver
        self.data_dir = "data"
        self.db_dir = os.path.join(self.data_dir, "db")
        self.logs_dir = os.path.join(self.data_dir, "logs")
        
        # Create directories if they don't exist
        os.makedirs(self.db_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        
        self.profiles_scraped = 0
        self.profiles_saved = 0
        self.scraped_urls = set()  # Track URLs to avoid duplicates across keywords
        
    def create_database(self, keywords, oblig_keywords=""):
        """Create SQLite database for storing LinkedIn profiles"""
        import hashlib
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create a short hash of the keywords (first 8 characters)
        all_keywords = f"{keywords} {oblig_keywords}".strip()
        keywords_hash = hashlib.md5(all_keywords.encode()).hexdigest()[:8]
        
        # Format: google_li_HASH_TIMESTAMP.db (under 40 chars)
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
                followers_count TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                search_keyword TEXT,
                all_keywords TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
        print(f"📁 Database created: {db_name}")
        print(f"🔑 Keywords hash: {keywords_hash} (for reference)")
        return self.db_path

    def save_profile_to_db(self, profile_data, search_keyword, all_keywords):
        """Save profile data to SQLite database"""
        try:
            # Check if URL already scraped in this session
            if profile_data.get('profile_url') in self.scraped_urls:
                print(f"⚠️  Duplicate profile skipped (already found): {profile_data.get('name', 'Unknown')}")
                return False
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR IGNORE INTO profiles 
                (profile_url, name, title, company, location, description, followers_count, search_keyword, all_keywords)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                profile_data.get('profile_url', ''),
                profile_data.get('name', ''),
                profile_data.get('title', ''),
                profile_data.get('company', ''),
                profile_data.get('location', ''),
                profile_data.get('description', ''),
                profile_data.get('followers_count', ''),
                search_keyword,
                all_keywords
            ))
            
            if cursor.rowcount > 0:
                self.profiles_saved += 1
                self.scraped_urls.add(profile_data.get('profile_url'))
                print(f"✅ Saved: {profile_data.get('name', 'Unknown')} - {profile_data.get('title', 'No title')}")
                conn.commit()
                conn.close()
                return True
            else:
                print(f"⚠️  Duplicate profile skipped (in DB): {profile_data.get('name', 'Unknown')}")
                conn.close()
                return False
            
        except sqlite3.Error as e:
            print(f"❌ Database error: {e}")
            return False
    
    def save_state(self, keywords, oblig_keywords, current_keyword, current_page, total_profiles_found):
        """Save scraping state to resume later if needed"""
        import hashlib
        all_keywords = f"{keywords} {oblig_keywords}".strip()
        keywords_hash = hashlib.md5(all_keywords.encode()).hexdigest()[:8]
        
        state_file = os.path.join(self.logs_dir, f"google_scraper_state_{keywords_hash}.json")
        
        state = {
            'keywords': keywords,
            'oblig_keywords': oblig_keywords,
            'current_keyword': current_keyword,
            'current_page': current_page,
            'total_profiles_found': total_profiles_found,
            'profiles_scraped': self.profiles_scraped,
            'profiles_saved': self.profiles_saved,
            'last_update': datetime.now().isoformat()
        }
        
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def scrape_single_keyword(self, keyword, oblig_keywords, max_profiles_per_keyword, total_max_profiles, all_keywords):
        """Scrape profiles for a single keyword with obligatory keywords"""
        # Build search query
        if oblig_keywords.strip():
            search_query = f'site:fr.linkedin.com/in/ {keyword.strip()} "{oblig_keywords.strip()}"'
        else:
            search_query = f'site:fr.linkedin.com/in/ {keyword.strip()}'
        
        print(f"\n{'='*80}")
        print(f"🔍 Searching keyword: '{keyword.strip()}'")
        if oblig_keywords.strip():
            print(f"📌 With obligatory keywords: '{oblig_keywords.strip()}'")
        print(f"🎯 Target: {max_profiles_per_keyword} profiles for this keyword")
        print(f"{'='*80}\n")
        
        google_search_url = f"https://www.google.com/search?q={search_query}"
        
        try:
            self.driver.get(google_search_url)
            time.sleep(3)
            
            # Handle consent/popup if present
            self._handle_google_popup()
            
            page_num = 1
            profiles_found_for_keyword = 0
            
            while profiles_found_for_keyword < max_profiles_per_keyword and self.profiles_saved < total_max_profiles:
                print(f"\n📄 Page {page_num} for keyword '{keyword.strip()}'...")
                
                # Wait for search results
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.any_of(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".MjjYud")),
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".g")),
                            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-ved]"))
                        )
                    )
                except TimeoutException:
                    print("⚠️  No search results found or page didn't load")
                    break
                
                # Get search results
                search_results = self._get_search_results()
                
                if not search_results:
                    print("❌ No search results found on this page")
                    break
                
                page_profiles_found = 0
                for result in search_results:
                    if profiles_found_for_keyword >= max_profiles_per_keyword:
                        print(f"✅ Reached max profiles ({max_profiles_per_keyword}) for keyword '{keyword.strip()}'")
                        break
                    
                    if self.profiles_saved >= total_max_profiles:
                        print(f"✅ Reached total max profiles ({total_max_profiles})")
                        break
                    
                    try:
                        # Extract profile data
                        profile_data = self._extract_enhanced_profile_data(result)
                        
                        if profile_data and profile_data.get('profile_url'):
                            # Validate LinkedIn URL
                            if self._is_valid_linkedin_url(profile_data['profile_url']):
                                # Save to database
                                saved = self.save_profile_to_db(profile_data, keyword.strip(), all_keywords)
                                if saved:
                                    profiles_found_for_keyword += 1
                                    page_profiles_found += 1
                                    self.profiles_scraped += 1
                                    
                                    print(f"🔢 Keyword progress: {profiles_found_for_keyword}/{max_profiles_per_keyword}")
                                    print(f"🔢 Total progress: {self.profiles_saved}/{total_max_profiles}")
                            else:
                                print(f"⚠️  Invalid LinkedIn URL: {profile_data.get('profile_url', 'Unknown')}")
                    
                    except Exception as e:
                        print(f"⚠️  Error processing result: {e}")
                        continue
                
                print(f"✅ Found {page_profiles_found} new profiles on page {page_num}")
                
                # Save current state
                self.save_state(all_keywords, oblig_keywords, keyword.strip(), page_num, self.profiles_saved)
                
                # Check if we should continue to next page
                if profiles_found_for_keyword < max_profiles_per_keyword and self.profiles_saved < total_max_profiles:
                    if not self._go_to_next_page():
                        print(f"📄 No more pages for keyword '{keyword.strip()}'")
                        break
                    page_num += 1
                else:
                    break
            
            print(f"\n✅ Completed keyword '{keyword.strip()}': {profiles_found_for_keyword} profiles found")
            return profiles_found_for_keyword
            
        except WebDriverException as e:
            print(f"❌ Browser error for keyword '{keyword}': {e}")
            return profiles_found_for_keyword
        except Exception as e:
            print(f"❌ Unexpected error for keyword '{keyword}': {e}")
            return profiles_found_for_keyword

    def scrape_google_page(self, keywords_str, oblig_keywords, max_profiles, max_profiles_per_keyword):
        """Main scraping function that iterates through keywords"""
        print(f"\n{'='*80}")
        print(f"🚀 STARTING GOOGLE LINKEDIN SCRAPER")
        print(f"{'='*80}")
        
        # Parse keywords (split by comma)
        keywords_list = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
        
        print(f"\n📋 Configuration:")
        print(f"   Keywords: {keywords_list}")
        print(f"   Obligatory keywords: '{oblig_keywords}'" if oblig_keywords.strip() else "   No obligatory keywords")
        print(f"   Max profiles total: {max_profiles}")
        print(f"   Max profiles per keyword: {max_profiles_per_keyword}")
        print(f"   Total keywords to process: {len(keywords_list)}")
        print(f"\n{'='*80}\n")
        
        try:
            for idx, keyword in enumerate(keywords_list, 1):
                if self.profiles_saved >= max_profiles:
                    print(f"\n🎉 Reached total maximum of {max_profiles} profiles!")
                    break
                
                print(f"\n{'*'*80}")
                print(f"📍 Processing keyword {idx}/{len(keywords_list)}: '{keyword}'")
                print(f"{'*'*80}")
                
                profiles_for_keyword = self.scrape_single_keyword(
                    keyword, 
                    oblig_keywords, 
                    max_profiles_per_keyword,
                    max_profiles,
                    keywords_str
                )
                
                print(f"\n{'*'*80}")
                print(f"✅ Keyword '{keyword}' completed: {profiles_for_keyword} profiles")
                print(f"📊 Total progress: {self.profiles_saved}/{max_profiles} profiles")
                print(f"{'*'*80}\n")
                
                # Small delay between keywords
                if idx < len(keywords_list) and self.profiles_saved < max_profiles:
                    print("⏳ Waiting 2 seconds before next keyword...")
                    time.sleep(2)
            
            # Final summary
            print(f"\n{'='*80}")
            print(f"🎉 SCRAPING COMPLETED!")
            print(f"{'='*80}")
            print(f"📊 Final Statistics:")
            print(f"   Total profiles scraped: {self.profiles_scraped}")
            print(f"   Total profiles saved to database: {self.profiles_saved}")
            print(f"   Keywords processed: {min(idx, len(keywords_list))}/{len(keywords_list)}")
            print(f"   Database location: {self.db_path}")
            print(f"{'='*80}\n")
            
        except Exception as e:
            print(f"❌ Fatal error during scraping: {e}")

    def _handle_google_popup(self):
        """Handle Google consent popup if present"""
        try:
            popup_selectors = [
                "button[aria-label*='Accept']",
                "button[aria-label*='Accepter']",
                "button#L2AGLb",
                ".QS5gu button"
            ]
            
            for selector in popup_selectors:
                try:
                    popup_button = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    popup_button.click()
                    print("✅ Handled Google popup")
                    time.sleep(1)
                    return
                except (TimeoutException, NoSuchElementException):
                    continue
        except Exception as e:
            pass

    def _get_search_results(self):
        """Get search results using multiple selectors as fallback"""
        selectors = [
            ".MjjYud",
            ".g",
            "[data-ved]"
        ]
        
        for selector in selectors:
            results = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if results:
                return results
        
        return []

    def _extract_enhanced_profile_data(self, result_element):
        """Extract comprehensive profile data from search result"""
        profile_data = {}
        
        try:
            # Extract LinkedIn profile URL
            profile_link = result_element.find_element(By.CSS_SELECTOR, "a[href*='linkedin.com/in/']")
            profile_data['profile_url'] = profile_link.get_attribute('href')
            
            # Extract name from title
            try:
                title_element = result_element.find_element(By.CSS_SELECTOR, "h3")
                full_title = title_element.text.strip()
                profile_data['name'] = full_title.split(' - ')[0].strip()
            except NoSuchElementException:
                profile_data['name'] = "Name not found"
            
            # Extract job title and company
            try:
                job_selectors = [
                    ".VwiC3b",
                    ".YrbPuc",
                    ".s3v9rd",
                    ".byrV5b cite"
                ]
                
                for selector in job_selectors:
                    try:
                        job_element = result_element.find_element(By.CSS_SELECTOR, selector)
                        job_text = job_element.text.strip()
                        
                        if job_text and len(job_text) > 5:
                            if ' · ' in job_text:
                                parts = job_text.split(' · ')
                                if len(parts) >= 2:
                                    profile_data['location'] = parts[0].strip()
                                    profile_data['title'] = parts[1].strip()
                                    if len(parts) >= 3:
                                        profile_data['company'] = parts[2].strip()
                            else:
                                profile_data['description'] = job_text
                            break
                    except NoSuchElementException:
                        continue
                
            except Exception:
                pass
            
            # Extract follower count
            try:
                follower_element = result_element.find_element(By.CSS_SELECTOR, "cite")
                follower_text = follower_element.text
                if 'abonnés' in follower_text or 'followers' in follower_text:
                    profile_data['followers_count'] = follower_text.strip()
            except NoSuchElementException:
                pass
            
            profile_data['extracted_at'] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            return profile_data
            
        except NoSuchElementException:
            return None
        except Exception as e:
            return None

    def _is_valid_linkedin_url(self, url):
        """Validate if the URL is a proper LinkedIn profile URL"""
        if not url:
            return False
        
        # More flexible patterns that accept URL-encoded characters
        valid_patterns = [
            r'linkedin\.com/in/[\w\-%]+/?$',           # Standard linkedin.com
            r'fr\.linkedin\.com/in/[\w\-%]+/?$',       # French linkedin
            r'[a-z]{2}\.linkedin\.com/in/[\w\-%]+/?$', # Any country code
            r'linkedin\.com/in/[\w\-%]+/[a-z]{2}/?$'   # With language suffix
        ]
        
        for pattern in valid_patterns:
            if re.search(pattern, url.lower()):
                return True
        
        return False

    def _go_to_next_page(self):
        """Navigate to the next page of search results"""
        try:
            next_selectors = [
                "a#pnnext",
                "a[aria-label*='Next']",
                "a[aria-label*='Suivant']",
                ".d6cvqb a[href*='start=']"
            ]
            
            for selector in next_selectors:
                try:
                    next_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    
                    if next_button:
                        print("➡️  Going to next page...")
                        self.driver.execute_script("arguments[0].click();", next_button)
                        time.sleep(3)
                        return True
                except (TimeoutException, NoSuchElementException):
                    continue
            
            return False
            
        except Exception as e:
            print(f"❌ Error navigating to next page: {e}")
            return False

    @staticmethod
    def scrape_google_linkedin_profiles(driver, keywords, oblig_keywords, max_profiles, max_profiles_per_keyword):
        """Entry point function for scraping Google LinkedIn profiles"""
        try:
            scraper = GoogleLinkedInProfileScraper(driver)
            
            # Create database
            scraper.create_database(keywords, oblig_keywords)
            
            # Start scraping
            scraper.scrape_google_page(keywords, oblig_keywords, max_profiles, max_profiles_per_keyword)
            
            return True
            
        except Exception as e:
            print(f"❌ Scraping failed: {e}")
            return False