# scraper/smart_search_group_scraper.py
import time
import logging
import sqlite3
import os
import json
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from utils.group_data_saver import GroupDataSaver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraping.log'),
        logging.StreamHandler()
    ]
)

class SmartSearchScraper:
    def __init__(self, driver, group_id, max_members=None):
        self.driver = driver
        self.group_id = group_id
        self.max_members = max_members
        self.wait = WebDriverWait(driver, 15)
        
        # Initialize database for duplicate detection
        self.db_path = f"data/scraping_progress_{group_id}.db"
        self.ensure_data_directory()
        self.init_database()
        
        # Initialize data saver
        self.data_saver = GroupDataSaver(group_id, batch_size=20)
        
        # Search prefixes for comprehensive coverage
        self.search_prefixes = [
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
            'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
            'ab', 'ac', 'ad', 'al', 'an', 'ar', 'ba', 'be', 'br', 'ca', 'ch', 'cl', 'co', 'cr',
            'da', 'de', 'di', 'do', 'el', 'em', 'en', 'er', 'es', 'fr', 'ga', 'ge', 'ha', 'he',
            'in', 'ja', 'je', 'jo', 'ka', 'ke', 'la', 'le', 'li', 'ma', 'me', 'mi', 'mo', 'na',
            'ne', 'ni', 'ol', 'pa', 'pe', 'ph', 'ra', 're', 'ri', 'ro', 'sa', 'se', 'sh', 'st',
            'ta', 'te', 'th', 'to', 'va', 'vi', 'wa', 'wi', 'ya', 'yo', 'za'
        ]
        
        # Load progress
        self.completed_prefixes = self.load_progress()
        
        logging.info(f"SmartSearchScraper initialized for group {group_id}")
        if self.completed_prefixes:
            logging.info(f"Resuming from previous session. Completed prefixes: {len(self.completed_prefixes)}")

    def ensure_data_directory(self):
        """Ensure data directory exists"""
        os.makedirs('data', exist_ok=True)

    def init_database(self):
        """Initialize SQLite database for duplicate detection and progress tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create members table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS members (
                profile_url TEXT PRIMARY KEY,
                name TEXT,
                title TEXT,
                profile_image_url TEXT,
                verified TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                search_prefix TEXT
            )
        ''')
        
        # Create progress table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS progress (
                prefix TEXT PRIMARY KEY,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                members_found INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
        logging.info("Database initialized successfully")

    def load_progress(self):
        """Load completed prefixes from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT prefix FROM progress')
        completed = [row[0] for row in cursor.fetchall()]
        conn.close()
        return set(completed)

    def save_progress(self, prefix, members_found):
        """Save progress for a completed prefix"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO progress (prefix, completed_at, members_found)
            VALUES (?, CURRENT_TIMESTAMP, ?)
        ''', (prefix, members_found))
        conn.commit()
        conn.close()
        logging.info(f"Progress saved for prefix '{prefix}': {members_found} members found")

    def is_member_duplicate(self, profile_url):
        """Check if member already exists in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM members WHERE profile_url = ?', (profile_url,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def save_member_to_db(self, member_data, search_prefix):
        """Save member to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO members 
                (profile_url, name, title, profile_image_url, verified, search_prefix)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                member_data['profile_url'],
                member_data['name'],
                member_data['title'],
                member_data['profile_image_url'],
                member_data['verified'],
                search_prefix
            ))
            conn.commit()
            return cursor.rowcount > 0  # Returns True if a new row was inserted
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            conn.close()

    def get_total_unique_members(self):
        """Get total number of unique members scraped"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM members')
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def find_search_input(selfdriver):
        """Find the search input field (handles both French and English placeholders)"""
        search_selectors = [
            'input[placeholder="Chercher des membres"]',
            'input[placeholder="Search members"]',
            'input[aria-label="Chercher des membres"]',
            'input[aria-label="Search members"]'
        ]
        
        for selector in search_selectors:
            try:
                search_input = driver.find_element(By.CSS_SELECTOR, selector)
                
                return search_input
            except NoSuchElementException:
                continue
        
        raise NoSuchElementException("Could not find search input field")

    def extract_member_data(self, member_element):
        """Extract member data from a member element"""
        try:
            member_data = {}
            
            # Extract profile URL
            link_element = member_element.find_element(By.CSS_SELECTOR, "a.ui-entity-action-row__link")
            member_data['profile_url'] = link_element.get_attribute('href')
            
            # Check for duplicates early
            if self.is_member_duplicate(member_data['profile_url']):
                return None
            
            # Extract name
            name_element = member_element.find_element(By.CSS_SELECTOR, ".artdeco-entity-lockup__title")
            member_data['name'] = name_element.text.strip()
            
            # Extract title/position
            try:
                title_element = member_element.find_element(By.CSS_SELECTOR, ".artdeco-entity-lockup__subtitle")
                member_data['title'] = title_element.text.strip()
            except NoSuchElementException:
                member_data['title'] = ""
            
            # Extract profile image URL
            try:
                img_element = member_element.find_element(By.CSS_SELECTOR, ".presence-entity__image")
                member_data['profile_image_url'] = img_element.get_attribute('src')
            except NoSuchElementException:
                member_data['profile_image_url'] = ""
            
            # Check if verified
            try:
                member_element.find_element(By.CSS_SELECTOR, ".artdeco-entity-lockup__badge")
                member_data['verified'] = "Yes"
            except NoSuchElementException:
                member_data['verified'] = "No"
            
            return member_data
        
        except Exception as e:
            logging.error(f"Error extracting member data: {e}")
            return None

    def search_members_by_prefix(self, prefix):
        """Search for members using a specific prefix with enhanced scroll and load more strategy"""
        try:
            # Find and clear search input
            search_input = self.find_search_input()
            search_input.clear()
            time.sleep(0.5)
            
            # Enter search prefix
            search_input.send_keys(prefix)
            search_input.send_keys(Keys.RETURN)
            time.sleep(2)
            
            # Wait for results to load
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(1)
            
            members_found = 0
            processed_urls = set()
            no_new_members_count = 0
            max_no_new_attempts = 4  # Changed to 4 as requested
            previous_member_count = 0
            
            logging.info(f"Starting comprehensive search for prefix '{prefix}'")
            
            while True:
                try:
                    # Step 1: Scroll to the bottom of the page
                    logging.info("📜 Scrolling to the bottom of the page...")
                    last_height = self.driver.execute_script("return document.body.scrollHeight")
                    
                    # Scroll to bottom
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)  # Wait for potential auto-loading
                    
                    # Wait for any auto-loading to complete
                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    if new_height > last_height:
                        logging.info("🔄 Page height increased - auto-loading detected, waiting...")
                    
                    # Step 2: Search for a clickable "load more" button
                    load_more_found = False
                    load_more_selectors = [
                        "//button[.//span[contains(text(), 'Afficher plus de résultats')]]",
                        "//button[.//span[text()='Afficher plus de résultats']]",
                        "//button[contains(text(), 'Show more results')]",
                        "//button[contains(text(), 'Load more')]",
                        "//button[.//span[contains(text(), 'Show more')]]",
                        "//button[.//span[contains(text(), 'Load more')]]",
                        "//button[@aria-label='Show more results']",
                        "//button[@aria-label='Load more results']"
                    ]
                    
                    logging.info("🔍 Searching for clickable 'Load more' button...")
                    
                    for selector in load_more_selectors:
                        try:
                            load_button = WebDriverWait(self.driver, 2).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                            
                            # Check if button is visible and enabled
                            if load_button.is_displayed() and load_button.is_enabled():
                                # Step 3: Button found - scroll to it and click
                                logging.info("✅ Found clickable 'Load more' button!")
                                
                                # Scroll to button to ensure it's in view
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", load_button)
                                
                                # Click the button using JavaScript to avoid interception issues
                                self.driver.execute_script("arguments[0].click();", load_button)
                                logging.info("🔄 Clicked 'Load more' button successfully")
                                load_more_found = True
                                time.sleep(2)  # Wait for new content to load
                                
                                # Step 4: Scroll to the end of the page after clicking
                                logging.info("📜 Scrolling to end of page after button click...")
                                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                                time.sleep(2)  # Wait for content to fully load
                                
                                break  # Exit selector loop since we found and clicked a button
                                
                        except TimeoutException:
                            continue
                        except Exception as e:
                            logging.debug(f"Error with selector {selector}: {e}")
                            continue
                    
                    # Step 3 (alternative): If no button found, assume auto-loading is complete
                    if not load_more_found:
                        logging.info("⏱️ No 'Load more' button found - assuming all results are loaded automatically")
                    
                    # Get current member elements after loading/scrolling
                    member_elements = self.driver.find_elements(
                        By.CSS_SELECTOR, 
                        "div.ui-entity-action-row"
                    )
                    
                    current_total_elements = len(member_elements)
                    logging.info(f"📊 Total member elements found: {current_total_elements}")
                    
                    if not member_elements:
                        logging.info(f"No members found for prefix '{prefix}'")
                        break
                    
                    # Process current batch of members
                    new_members_in_batch = 0
                    current_batch_processed = 0
                    
                    for element in member_elements:
                        try:
                            member_data = self.extract_member_data(element)
                            
                            if member_data and member_data['profile_url'] not in processed_urls:
                                processed_urls.add(member_data['profile_url'])
                                
                                # Save to database (duplicate check happens inside)
                                if self.save_member_to_db(member_data, prefix):
                                    # Also save to CSV via data saver
                                    self.data_saver.add_member(member_data)
                                    members_found += 1
                                    new_members_in_batch += 1
                                    
                                    logging.info(f"✅ New member: {member_data['name']} (prefix: {prefix}, total: {members_found})")
                                    
                                    # Check if we've reached max members
                                    if self.max_members and self.get_total_unique_members() >= self.max_members:
                                        logging.info(f"🎯 Reached maximum of {self.max_members} members")
                                        return members_found
                                else:
                                    logging.debug(f"Duplicate member skipped: {member_data['name']}")
                            
                            current_batch_processed += 1
                            
                        except Exception as e:
                            logging.error(f"Error processing member element: {e}")
                            continue
                    
                    # Enhanced stopping logic
                    logging.info(f"📈 Batch results: {new_members_in_batch} new members, {current_batch_processed} total processed")
                    
                    # Check if we found new members in this batch
                    if new_members_in_batch == 0:
                        no_new_members_count += 1
                        logging.info(f"⚠️  No new members found in this batch (attempt {no_new_members_count}/{max_no_new_attempts})")
                    else:
                        no_new_members_count = 0  # Reset counter when we find new members
                        logging.info(f"✅ Found {new_members_in_batch} new members in this batch")
                    
                    # Enhanced stopping conditions
                    should_stop = False
                    
                    # Condition 1: No new members for max attempts
                    if no_new_members_count >= max_no_new_attempts:
                        logging.info(f"🛑 No new members found for {max_no_new_attempts} consecutive attempts. Stopping.")
                        should_stop = True
                    
                    # Condition 2: No load more button and no new members
                    elif not load_more_found and new_members_in_batch == 0:
                        logging.info(f"🛑 No 'Load more' button and no new members found. All results loaded.")
                        should_stop = True
                    
                    # Condition 3: Total elements haven't increased (stagnation detection)
                    elif current_total_elements == previous_member_count and not load_more_found:
                        logging.info(f"🛑 Page content hasn't changed and no load button available. Stopping.")
                        should_stop = True
                    
                    if should_stop:
                        break
                    
                    # Update previous count for next iteration
                    previous_member_count = current_total_elements
                    
                    # Brief pause before next iteration
                    time.sleep(1)
                    
                except Exception as e:
                    logging.error(f"Error in search loop for prefix '{prefix}': {e}")
                    break
            
            logging.info(f"🏁 Completed search for prefix '{prefix}': {members_found} new members found")
            return members_found
            
        except Exception as e:
            logging.error(f"Error searching with prefix '{prefix}': {e}")
            return 0

    def refresh_page_and_navigate_back(self):
        """Refresh the page to clear memory and navigate back to group"""
        try:
            current_url = self.driver.current_url
            logging.info("Refreshing page to clear memory...")
            
            # Refresh the page
            self.driver.refresh()
            time.sleep(3)
            
            # Wait for page to load
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(2)
            
            logging.info("Page refreshed successfully")
            return True
            
        except Exception as e:
            logging.error(f"Error refreshing page: {e}")
            return False

    def run_smart_search(self):
        """Run the smart search scraping process with refresh between prefixes"""
        logging.info("Starting smart search scraping...")
        
        total_new_members = 0
        remaining_prefixes = [p for p in self.search_prefixes if p not in self.completed_prefixes]
        
        logging.info(f"Total prefixes to process: {len(remaining_prefixes)}")
        logging.info(f"Already completed: {len(self.completed_prefixes)}")
        
        for i, prefix in enumerate(remaining_prefixes, 1):
            try:
                logging.info(f"[{i}/{len(remaining_prefixes)}] Starting comprehensive search for prefix: '{prefix}'")
                
                # Search with current prefix (includes scroll and load more)
                members_found = self.search_members_by_prefix(prefix)
                total_new_members += members_found
                
                # Save progress
                self.save_progress(prefix, members_found)
                self.completed_prefixes.add(prefix)
                
                # Get current stats
                total_unique = self.get_total_unique_members()
                logging.info(f"✅ Prefix '{prefix}' completed: {members_found} new members found. Total unique: {total_unique}")
                
                # Check if we've reached max members
                if self.max_members and total_unique >= self.max_members:
                    logging.info(f"🎯 Reached maximum of {self.max_members} members. Stopping...")
                    break
                
                # Refresh page before next prefix to prevent memory issues
                if i < len(remaining_prefixes):  # Don't refresh after the last prefix
                    logging.info("🔄 Refreshing page to clear memory before next prefix...")
                    self.refresh_page_and_navigate_back()
                    
                    # Brief pause between prefixes
                    time.sleep(2)
                
            except KeyboardInterrupt:
                logging.info("Search interrupted by user. Progress has been saved.")
                break
            except Exception as e:
                logging.error(f"Error processing prefix '{prefix}': {e}")
                # Try to refresh page and continue with next prefix
                try:
                    self.refresh_page_and_navigate_back()
                except:
                    logging.error("Failed to refresh page after error")
                continue
        
        # Save any remaining data
        self.data_saver.save_remaining()
        
        # Final statistics
        total_unique = self.get_total_unique_members()
        stats = self.data_saver.get_stats()
        
        logging.info("=" * 50)
        logging.info("SCRAPING COMPLETED!")
        logging.info(f"Total unique members found: {total_unique}")
        logging.info(f"Total members saved to CSV: {stats['total_saved']}")
        logging.info(f"Prefixes completed: {len(self.completed_prefixes)}/{len(self.search_prefixes)}")
        logging.info(f"CSV file: {self.data_saver.get_filepath()}")
        logging.info(f"Database: {self.db_path}")
        logging.info("=" * 50)
        
        return total_unique

def scrape_group_members_smart_search(driver, group_url, max_members=None):
    """Main function to scrape group members using smart search"""
    logging.info(f"Starting smart search scraping for: {group_url}")
    
    # Navigate to group
    driver.get(group_url)
    time.sleep(3)
    
    # Extract group ID from URL
    import re
    group_id = re.search(r'/groups/(\d+)/', group_url)
    group_id = group_id.group(1) if group_id else "unknown"
    
    # Wait for page to load
    wait = WebDriverWait(driver, 15)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    
    # Initialize and run scraper
    scraper = SmartSearchScraper(driver, group_id, max_members)
    total_members = scraper.run_smart_search()
    
    return total_members