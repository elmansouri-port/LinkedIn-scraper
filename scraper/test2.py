import time
import csv
import os
import sqlite3
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GoogleLinkedInProfileScraper:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)
        self.profiles_data = []
        self.search_keywords = ""
        self.current_page = 0
        self.profiles_scraped = 0
        self.db_path = ""
        self.state_file = ""
        
    def search_google_linkedin_profiles(self, search_keywords, max_profiles=50):
        """
        Main entry function to search Google for LinkedIn profiles
        
        Args:
            search_keywords (str): The job title or keywords to search for
            max_profiles (int): Maximum number of profiles to scrape
            
        Returns:
            list: List of scraped profile data
        """
        self.search_keywords = search_keywords
        logger.info(f"Starting Google search for LinkedIn profiles: {search_keywords}")
        
        # Initialize database and state tracking
        self._init_database()
        self._load_state()
        
        try:
            # Build Google search URL with site:linkedin.com
            search_query = f'site:linkedin.com/in/ "{search_keywords}"'
            google_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
            
            # If resuming, navigate to the correct page
            if self.current_page > 0:
                logger.info(f"Resuming from page {self.current_page + 1}")
                google_url += f"&start={self.current_page * 10}"
            
            logger.info(f"Navigating to: {google_url}")
            self.driver.get(google_url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Accept cookies if present (adjust selector as needed)
            try:
                cookie_button = self.driver.find_element(By.CSS_SELECTOR, "button[id*='accept'], button[aria-label*='Accept']")
                cookie_button.click()
                time.sleep(2)
            except NoSuchElementException:
                logger.info("No cookie banner found")
            
            max_pages = 10  # Limit to prevent infinite loop
            
            while self.profiles_scraped < max_profiles and self.current_page < max_pages:
                logger.info(f"Processing page {self.current_page + 1}")
                
                # Scroll to load all results on current page
                self._scroll_page()
                
                # Get LinkedIn profile links from Google search results
                linkedin_links = self._get_linkedin_links_from_google()
                
                if not linkedin_links:
                    logger.warning("No LinkedIn links found on current page")
                    break
                
                # Process each LinkedIn profile
                for link in linkedin_links:
                    if self.profiles_scraped >= max_profiles:
                        break
                        
                    try:
                        # Check if profile already exists in database
                        if self._profile_exists(link):
                            logger.info(f"Profile already exists, skipping: {link}")
                            continue
                            
                        profile_data = self._scrape_linkedin_profile(link)
                        if profile_data:
                            self._save_profile_to_db(profile_data)
                            self.profiles_data.append(profile_data)
                            self.profiles_scraped += 1
                            logger.info(f"Scraped profile {self.profiles_scraped}: {profile_data.get('name', 'Unknown')}")
                        
                        # Save state after each profile
                        self._save_state()
                        
                        # Small delay between profiles
                        time.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"Error scraping profile {link}: {str(e)}")
                        continue
                
                # Navigate to next page if needed
                if self.profiles_scraped < max_profiles:
                    if not self._go_to_next_google_page():
                        logger.info("No more pages available or unable to navigate")
                        break
                
                self.current_page += 1
                self._save_state()
                
        except Exception as e:
            logger.error(f"Error in main search function: {str(e)}")
        
        # Export to CSV
        self._export_db_to_csv()
        
        logger.info(f"Scraping completed. Total profiles scraped: {len(self.profiles_data)}")
        return self.profiles_data
    
    def _scroll_page(self):
        """Scroll the Google search results page to load all results"""
        try:
            # Scroll to bottom of page gradually
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            while True:
                # Scroll down
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # Calculate new scroll height
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                
        except Exception as e:
            logger.error(f"Error scrolling page: {str(e)}")
    
    def _get_linkedin_links_from_google(self):
        """Extract LinkedIn profile links from Google search results"""
        linkedin_links = []
        
        try:
            # CSS selector for Google search result links - adjust as needed
            result_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='linkedin.com/in/']")
            
            for link in result_links:
                href = link.get_attribute('href')
                if href and 'linkedin.com/in/' in href:
                    # Clean the URL (remove Google redirect parameters)
                    if '/url?q=' in href:
                        clean_url = href.split('/url?q=')[1].split('&')[0]
                    else:
                        clean_url = href
                    
                    if clean_url not in linkedin_links:
                        linkedin_links.append(clean_url)
            
            logger.info(f"Found {len(linkedin_links)} LinkedIn links on current page")
            
        except Exception as e:
            logger.error(f"Error extracting LinkedIn links: {str(e)}")
            
        return linkedin_links
    
    def _scrape_linkedin_profile(self, profile_url):
        """
        Scrape individual LinkedIn profile data
        
        Args:
            profile_url (str): LinkedIn profile URL
            
        Returns:
            dict: Profile data including name, job title, and profile link
        """
        profile_data = {
            'name': '',
            'job_title': '',
            'linkedin_url': profile_url,
            'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        try:
            logger.info(f"Scraping profile: {profile_url}")
            self.driver.get(profile_url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Scrape name - adjust CSS selector as needed
            try:
                name_element = self.driver.find_element(By.CSS_SELECTOR, "h1.text-heading-xlarge")
                profile_data['name'] = name_element.text.strip()
            except NoSuchElementException:
                logger.warning(f"Name not found for profile: {profile_url}")
                # Alternative selector
                try:
                    name_element = self.driver.find_element(By.CSS_SELECTOR, ".pv-text-details__left-panel h1")
                    profile_data['name'] = name_element.text.strip()
                except NoSuchElementException:
                    profile_data['name'] = 'Name not found'
            
            # Scrape job title - adjust CSS selector as needed
            try:
                job_element = self.driver.find_element(By.CSS_SELECTOR, ".text-body-medium.break-words")
                profile_data['job_title'] = job_element.text.strip()
            except NoSuchElementException:
                logger.warning(f"Job title not found for profile: {profile_url}")
                # Alternative selector
                try:
                    job_element = self.driver.find_element(By.CSS_SELECTOR, ".pv-text-details__left-panel .text-body-medium")
                    profile_data['job_title'] = job_element.text.strip()
                except NoSuchElementException:
                    profile_data['job_title'] = 'Job title not found'
            
            return profile_data
            
        except Exception as e:
            logger.error(f"Error scraping LinkedIn profile {profile_url}: {str(e)}")
            return None
    
    def _go_to_next_google_page(self):
        """Navigate to next page of Google search results"""
        try:
            # CSS selector for "Next" button - adjust as needed
            next_button = self.driver.find_element(By.CSS_SELECTOR, "a[aria-label='Next page'], a#pnnext")
            
            if next_button and next_button.is_enabled():
                next_button.click()
                time.sleep(3)
                return True
            else:
                return False
                
        except NoSuchElementException:
            logger.info("Next page button not found")
            return False
        except Exception as e:
            logger.error(f"Error navigating to next page: {str(e)}")
            return False
    
    def save_to_csv(self, filename=None, search_keywords=""):
        """Deprecated - now using database with CSV export"""
        logger.warning("save_to_csv is deprecated. Data is automatically saved to database and exported to CSV.")
        return self._export_db_to_csv()
    
    def _init_database(self):
        """Initialize SQLite database for storing profiles"""
        # Ensure directories exist
        os.makedirs('data/csv', exist_ok=True)
        os.makedirs('data/db', exist_ok=True)
        os.makedirs('data/logs', exist_ok=True)
        
        # Create database filename based on search keywords
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_keywords = "".join(c for c in self.search_keywords if c.isalnum() or c in (' ', '_')).replace(' ', '_')
        db_name = f"google_linkedin_profiles_{safe_keywords}_{timestamp}.db"
        self.db_path = os.path.join('data', 'db', db_name)
        
        # State file for resuming
        state_name = f"google_scraper_state_{safe_keywords}.json"
        self.state_file = os.path.join('data', 'logs', state_name)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create profiles table with linkedin_url as unique
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    job_title TEXT,
                    linkedin_url TEXT UNIQUE,
                    scraped_at TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create index on linkedin_url for faster lookups
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_linkedin_url ON profiles(linkedin_url)')
            
            conn.commit()
            conn.close()
            
            logger.info(f"Database initialized: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
    
    def _profile_exists(self, linkedin_url):
        """Check if profile already exists in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM profiles WHERE linkedin_url = ?', (linkedin_url,))
            exists = cursor.fetchone()[0] > 0
            
            conn.close()
            return exists
            
        except Exception as e:
            logger.error(f"Error checking profile existence: {str(e)}")
            return False
    
    def _save_profile_to_db(self, profile_data):
        """Save profile data to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR IGNORE INTO profiles (name, job_title, linkedin_url, scraped_at)
                VALUES (?, ?, ?, ?)
            ''', (
                profile_data['name'],
                profile_data['job_title'],
                profile_data['linkedin_url'],
                profile_data['scraped_at']
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving profile to database: {str(e)}")
    
    def _save_state(self):
        """Save current scraping state for resuming"""
        state_data = {
            'search_keywords': self.search_keywords,
            'current_page': self.current_page,
            'profiles_scraped': self.profiles_scraped,
            'db_path': self.db_path,
            'last_updated': datetime.now().isoformat()
        }
        
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {str(e)}")
    
    def _load_state(self):
        """Load previous scraping state if exists"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    state_data = json.load(f)
                
                if state_data.get('search_keywords') == self.search_keywords:
                    self.current_page = state_data.get('current_page', 0)
                    self.profiles_scraped = state_data.get('profiles_scraped', 0)
                    if state_data.get('db_path') and os.path.exists(state_data.get('db_path')):
                        self.db_path = state_data.get('db_path')
                        logger.info(f"Resuming previous session from page {self.current_page + 1}")
                    
            except Exception as e:
                logger.error(f"Error loading state: {str(e)}")
    
    def _export_db_to_csv(self):
        """Export database content to CSV file"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT name, job_title, linkedin_url, scraped_at FROM profiles ORDER BY created_at')
            profiles = cursor.fetchall()
            
            conn.close()
            
            if not profiles:
                logger.warning("No profiles to export")
                return None
            
            # Create CSV filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_keywords = "".join(c for c in self.search_keywords if c.isalnum() or c in (' ', '_')).replace(' ', '_')
            csv_filename = f"google_linkedin_profiles_{safe_keywords}_{timestamp}.csv"
            csv_path = os.path.join('data', 'csv', csv_filename)
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['name', 'job_title', 'linkedin_url', 'scraped_at']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for profile in profiles:
                    writer.writerow({
                        'name': profile[0],
                        'job_title': profile[1],
                        'linkedin_url': profile[2],
                        'scraped_at': profile[3]
                    })
            
            logger.info(f"Data exported to CSV: {csv_path}")
            return csv_path
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {str(e)}")
            return None

# Entry function to be called from main.py
def scrape_google_linkedin_profiles(driver, search_keywords, max_profiles=50):
    """
    Entry function to scrape LinkedIn profiles from Google search
    
    Args:
        driver: Selenium WebDriver instance
        search_keywords (str): Job title or keywords to search for
        max_profiles (int): Maximum number of profiles to scrape
        
    Returns:
        list: List of scraped profile data
    """
    scraper = GoogleLinkedInProfileScraper(driver)
    profiles = scraper.search_google_linkedin_profiles(search_keywords, max_profiles)
    
    logger.info(f"Scraping completed. {len(profiles)} profiles processed")
    
    return profiles
    