# scraper/group_scraper.py
import time
import logging
import re
import string
import os
import json
from datetime import datetime
from itertools import product
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from utils.group_data_saver import GroupDataSaver

# Component imports — all Selenium element logic is now in components/
from components.group.members import get_member_elements, extract_member_data
from components.group.search import find_search_input, enter_search_term
from components.common.scrolling import (
    scroll_to_bottom,
    has_page_scrolled as _has_page_scrolled,
    click_load_more,
)
from components.selectors import GroupSelectors


class ScrapingLogger:
    """Handles logging and session resume functionality"""
    
    def __init__(self, group_id, scraping_mode):
        self.group_id = group_id
        self.scraping_mode = scraping_mode
        self.logs_dir = "data/logs"
        self.log_file = os.path.join(self.logs_dir, f"group_steps_{group_id}.log")
        self.state_file = os.path.join(self.logs_dir, f"group_state_{group_id}.json")
        
        # Make sure logs directory exists
        os.makedirs(self.logs_dir, exist_ok=True)
        
        self.setup_logging()
        
        # Track our progress
        self.session_state = {
            'scraping_mode': scraping_mode,
            'current_combination_index': 0,
            'total_members_scraped': 0,
            'completed_combinations': [],
            'session_start_time': datetime.now().isoformat(),
            'last_update_time': datetime.now().isoformat()
        }
    
    def setup_logging(self):
        """Set up file logging"""
        self.logger = logging.getLogger(f'group_scraper_{self.group_id}')
        self.logger.setLevel(logging.INFO)
        
        # Clear any existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Add file handler
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Log session start
        self.logger.info("=== NEW SCRAPING SESSION STARTED ===")
        self.logger.info(f"Group ID: {self.group_id}")
        self.logger.info(f"Scraping Mode: {self.scraping_mode}")
    
    def log_combination_start(self, combination_index, combination, total_combinations):
        """Log when we start working on a new search combination"""
        message = f"Starting combination {combination_index}/{total_combinations}: '{combination}'"
        self.logger.info(message)
        print(f"📝 {message}")
        
        # Update our progress
        self.session_state['current_combination_index'] = combination_index
        self.session_state['last_update_time'] = datetime.now().isoformat()
        self.save_state()
    
    def log_combination_complete(self, combination, members_found, total_scraped):
        """Log when we finish a combination"""
        message = f"Completed combination '{combination}': {members_found} members processed. Total scraped: {total_scraped}"
        self.logger.info(message)
        print(f"✅ {message}")
        
        self.session_state['completed_combinations'].append({
            'combination': combination,
            'members_found': members_found,
            'timestamp': datetime.now().isoformat()
        })
        self.session_state['total_members_scraped'] = total_scraped
        self.session_state['last_update_time'] = datetime.now().isoformat()
        self.save_state()
    
    def log_session_complete(self, total_scraped, total_combinations):
        """Log when we're all done"""
        message = f"=== SCRAPING SESSION COMPLETED === Total members scraped: {total_scraped} from {total_combinations} combinations"
        self.logger.info(message)
        print(f"🎉 {message}")
        
        self.session_state['session_complete'] = True
        self.session_state['session_end_time'] = datetime.now().isoformat()
        self.session_state['total_members_scraped'] = total_scraped
        self.save_state()
    
    def log_session_interrupted(self, total_scraped, current_combination):
        """Log when something goes wrong or we stop early"""
        message = f"=== SESSION INTERRUPTED === Total scraped: {total_scraped}, Last combination: '{current_combination}'"
        self.logger.info(message)
        print(f"⚠️ {message}")
        
        self.session_state['session_interrupted'] = True
        self.session_state['total_members_scraped'] = total_scraped
        self.session_state['last_update_time'] = datetime.now().isoformat()
        self.save_state()
    
    def log_error(self, error_message):
        """Log errors"""
        self.logger.error(error_message)
        print(f"❌ ERROR: {error_message}")
    
    def log_info(self, message):
        """Log general info"""
        self.logger.info(message)
        print(f"ℹ️ {message}")
    
    def save_state(self):
        """Save our progress to a file so we can resume later"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.session_state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Error saving state: {e}")
    
    def load_previous_state(self):
        """Load previous session if it exists"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"❌ Error loading previous state: {e}")
                return None
        return None
    
    def check_for_resume(self, combinations):
        """Check if we can continue from where we left off"""
        previous_state = self.load_previous_state()
        
        if not previous_state:
            print("🆕 No previous session found. Starting fresh.")
            return 0, 0  # start_index, total_members_scraped
        
        # Make sure we're using the same scraping mode
        if previous_state.get('scraping_mode') != self.scraping_mode:
            print(f"⚠️ Previous session used different mode ({previous_state.get('scraping_mode')}). Starting fresh.")
            return 0, 0
        
        # If we finished last time, start over
        if previous_state.get('session_complete'):
            print("✅ Previous session was completed. Starting fresh.")
            return 0, 0
        
        # Show resume option
        last_combination_index = previous_state.get('current_combination_index', 0)
        total_scraped = previous_state.get('total_members_scraped', 0)
        completed_combinations = previous_state.get('completed_combinations', [])
        
        print(f"\n🔄 FOUND PREVIOUS SESSION")
        print(f"   📊 Mode: {previous_state.get('scraping_mode')}")
        print(f"   📈 Total members scraped: {total_scraped}")
        print(f"   📍 Last combination index: {last_combination_index}")
        print(f"   ✅ Completed combinations: {len(completed_combinations)}")
        
        if last_combination_index < len(combinations):
            next_combination = combinations[last_combination_index] if last_combination_index < len(combinations) else "N/A"
            print(f"   ➡️ Next combination would be: '{next_combination}' (index {last_combination_index})")
        
        # Ask user what to do
        while True:
            choice = input(f"\n🤔 Resume from where you left off? (y/n) [default: y]: ").lower().strip()
            if not choice:
                choice = 'y'
            
            if choice in ['y', 'yes']:
                print(f"🔄 Resuming from combination index {last_combination_index}")
                self.logger.info(f"=== RESUMING SESSION === Starting from combination index {last_combination_index}")
                return last_combination_index, total_scraped
            elif choice in ['n', 'no']:
                print("🆕 Starting fresh session")
                self.logger.info("=== STARTING FRESH === User chose not to resume")
                return 0, 0
            else:
                print("❌ Please enter 'y' for yes or 'n' for no")


class CombinationGenerator:
    """Creates different sets of search terms based on how thorough you want to be"""
    
    def __init__(self):
        self.alphabet = string.ascii_lowercase
        
    def generate_single_letters(self):
        """Just a-z"""
        return list(self.alphabet)
    
    def generate_double_letters(self):
        """All two-letter combinations (aa, ab, ac, etc.)"""
        return [''.join(combo) for combo in product(self.alphabet, repeat=2)]
    
    def generate_common_name_patterns(self):
        """Common patterns you find in names"""
        # Stuff you see at the start or end of names
        prefixes = ['al', 'an', 'br', 'ch', 'cl', 'cr', 'da', 'de', 'el', 'fr', 'ja', 'jo', 'ma', 'mi', 'pa', 'ra', 're', 'sa', 'th']
        suffixes = ['an', 'ar', 'el', 'en', 'er', 'es', 'ia', 'ic', 'ie', 'in', 'le', 'ly', 'na', 'ne', 'on', 'or', 'ry', 'son', 'ton']
        
        # Vowel + consonant and consonant + vowel patterns
        vowel_consonant = [''.join(combo) for combo in product('aeiou', 'bcdfghjklmnpqrstvwxyz')]
        consonant_vowel = [''.join(combo) for combo in product('bcdfghjklmnpqrstvwxyz', 'aeiou')]
        
        # Mix them together but don't go crazy
        return list(set(prefixes + suffixes + vowel_consonant[:50] + consonant_vowel[:50]))
    
    def generate_three_letter_common(self):
        """Common three-letter combinations in names"""
        common_three = [
            'and', 'ben', 'can', 'dan', 'eva', 'ian', 'jan', 'jen', 'joe', 'jon',
            'ken', 'lea', 'len', 'max', 'sam', 'tom', 'van', 'ale', 'ali', 'ana',
            'ann', 'art', 'bob', 'cal', 'cam', 'don', 'eli', 'gab', 'guy', 'hal',
            'ida', 'ira', 'ivy', 'jay', 'jim', 'kim', 'lee', 'leo', 'liz', 'lou',
            'mae', 'mel', 'mia', 'nat', 'ned', 'pat', 'ray', 'rex', 'roy', 'sue',
            'ted', 'tim', 'vic', 'wes'
        ]
        return common_three

    def get_combinations(self, mode='medium'):
        """Get search combinations based on how thorough you want to be"""
        if mode == 'light':
            # Just single letters - quick and dirty
            combinations = self.generate_single_letters()
            print(f"Light mode: Using {len(combinations)} single letter combinations")
            
        elif mode == 'medium':
            # Single letters + all double letters - good balance
            single = self.generate_single_letters()
            double = self.generate_double_letters()
            combinations = single + double
            print(f"Medium mode: Using {len(combinations)} combinations (single + double letters)")
            
        elif mode == 'robust':
            # Everything - gonna take a while but thorough
            single = self.generate_single_letters()
            double = self.generate_double_letters()
            common_patterns = self.generate_common_name_patterns()
            three_letter = self.generate_three_letter_common()
            combinations = single + double + common_patterns + three_letter
            # Remove duplicates but keep order
            combinations = list(dict.fromkeys(combinations))
            print(f"Robust mode: Using {len(combinations)} combinations (comprehensive set)")
            
        else:
            raise ValueError("Mode must be 'light', 'medium', or 'robust'")
        
        return combinations


class MemberTracker:
    """Keeps track of which members we've already processed so we don't do them twice"""
    
    def __init__(self):
        self.processed_members = set()  # Unique IDs of members we've seen
        self.last_processed_count = 0
    
    def generate_member_id(self, name, profile_link):
        """Create a unique ID for each member"""
        return f"{name.strip()}::{profile_link}"
    
    def is_processed(self, name, profile_link):
        """Check if we've already handled this member"""
        member_id = self.generate_member_id(name, profile_link)
        return member_id in self.processed_members
    
    def mark_processed(self, name, profile_link):
        """Mark this member as done"""
        member_id = self.generate_member_id(name, profile_link)
        self.processed_members.add(member_id)
    
    def get_processed_count(self):
        """How many members have we processed?"""
        return len(self.processed_members)
    
    def reset_for_new_combination(self):
        """Start fresh for a new search term"""
        self.processed_members.clear()
        self.last_processed_count = 0
        print("🔄 Reset member tracker for new combination")


def has_page_scrolled(old_height, new_height):
    """Check if the page actually scrolled — delegates to component."""
    return _has_page_scrolled(old_height, new_height)


def get_memory_usage(driver):
    """Check how much memory the browser is using"""
    try:
        metrics = driver.execute_cdp_cmd("Performance.getMetrics", {})
        metric_dict = {m['name']: m['value'] for m in metrics['metrics']}
        
        used = metric_dict.get('UsedJSHeapSize', 0)
        total = metric_dict.get('TotalJSHeapSize', 0)
        limit = metric_dict.get('JSHeapSizeLimit', 0)
        
        return used, limit, total
    except Exception as e:
        print(f"Error checking memory: {e}")
        return 0, 0, 0


def is_memory_getting_full(used, limit, threshold=0.9):
    """Is the browser running out of memory?"""
    if limit == 0:
        return False
    return (used / limit) > threshold


def process_new_members(driver, data_saver, member_tracker, combination, max_members, total_members_scraped):
    """Process members we haven't seen before on this page.
    Uses components.group.members for element extraction."""
    print(f"\n🔍 PROCESSING MEMBERS FOR '{combination}'...")
    
    # Find all the member items using the component
    member_items = get_member_elements(driver)
    
    current_page_count = len(member_items)
    already_processed_count = member_tracker.get_processed_count()
    
    print(f"📊 Found {current_page_count} members on page, already processed {already_processed_count}")
    
    # Only look at members we haven't processed yet
    new_members_processed = 0
    members_to_process = member_items[already_processed_count:]
    
    if not members_to_process:
        print("⏭️ No new members to process")
        return 0, total_members_scraped, True
    
    print(f"🔄 Processing {len(members_to_process)} new members...")
    
    for i, item in enumerate(members_to_process, start=already_processed_count + 1):
        print(f"👤 Processing member {i}/{current_page_count}...", end=' ')
        try:
            # Extract member data using the component
            member_data = extract_member_data(item)
            if member_data is None:
                print("⚠️ Could not extract data, skipping")
                continue
            
            name = member_data["name"]
            profile_link = member_data["profile_url"]
            headline = member_data["headline"]
            profile_img_link = member_data["image_url"]
            
            print(f"Name: {name}")

            # Double check we haven't seen them
            if member_tracker.is_processed(name, profile_link):
                print(f"⚠️ Member {i} already processed: {name}")
                member_tracker.mark_processed(name, profile_link)
                continue
            
            # Mark as processed before saving
            member_tracker.mark_processed(name, profile_link)
            
            # Save the member data
            saved = data_saver.save_data(name, profile_link, headline, profile_img_link)
            if saved:  # New member added to database
                print(f"✅ SAVED: {name}")
                total_members_scraped += 1
                new_members_processed += 1
            else:  # Already in database
                print(f"🔄 DUPLICATE: {name}")
                new_members_processed += 1
                        
            # Check if we hit our limit
            if max_members and total_members_scraped >= max_members:
                print(f"🎯 REACHED LIMIT! Maximum members ({max_members}) achieved. Total: {total_members_scraped}")
                return new_members_processed, total_members_scraped, False
        
        except Exception as e:
            print(f"❌ ERROR with member {i}: {e}")
            continue

    print(f"✅ Processed {new_members_processed} new members for combination '{combination}'")
    return new_members_processed, total_members_scraped, True


def scraper(driver, url, max_members, scraping_mode='medium', group_id=None):
    """Main scraping function with logging and resume functionality"""
    
    # Get group ID from URL if not provided
    if not group_id:
        group_id = extract_group_id_from_url(url)
    
    # Generate our search combinations
    combo_generator = CombinationGenerator()
    combinations = combo_generator.get_combinations(scraping_mode)
    
    # Set up logging
    scraping_logger = ScrapingLogger(group_id, scraping_mode)
    
    # Check if we can resume from a previous session
    start_index, total_members_scraped = scraping_logger.check_for_resume(combinations)
    
    print(f"\n🚀 Starting scraper in {scraping_mode} mode with {len(combinations)} combinations")
    if start_index > 0:
        print(f"🔄 Resuming from combination {start_index + 1}/{len(combinations)}")
        remaining = combinations[start_index:]
        print("Remaining combinations:", remaining[:10] if len(remaining) > 10 else remaining)
    else:
        print("First 10 combinations:", combinations[:10])
    
    driver.get(url)
    wait = WebDriverWait(driver, 15)

    # Set up our data saver and member tracker
    data_saver = GroupDataSaver()
    member_tracker = MemberTracker()
    
    try:
        # Go through each combination starting from where we left off
        for i, combination in enumerate(combinations[start_index:], start=start_index + 1):
            print(f"\n" + "="*60)
            print(f"🔄 STARTING COMBINATION {i}/{len(combinations)}: '{combination}'")
            print(f"📊 Progress: {((i-1)/len(combinations)*100):.1f}% complete")
            print(f"👥 Total members scraped so far: {total_members_scraped}")
            print("="*60)
            
            scraping_logger.log_combination_start(i, combination, len(combinations))
            
            # Check if we've hit our limit
            if max_members and total_members_scraped >= max_members:
                print(f"🎯 REACHED MEMBER LIMIT! ({max_members})")
                scraping_logger.log_info(f"Reached maximum members limit ({max_members}). Stopping.")
                break
            
            # Reset tracker for new search
            member_tracker.reset_for_new_combination()
            
            # Refresh page to clear memory
            print(f"🔄 Refreshing page for new search...")
            driver.refresh()
            time.sleep(1)
            print(f"✅ Page refreshed!")

            try:
                # Find the search box using component (handles French/English)
                print(f"🔍 Looking for search input...")
                enter_search_term(driver, combination, timeout=15)
                print(f"✅ Search term entered: '{combination}'")
            except Exception:
                error_msg = f"Couldn't find search input for combination '{combination}'. Skipping."
                scraping_logger.log_error(error_msg)
                continue

            # Check memory usage
            used, limit, total = get_memory_usage(driver)
            scraping_logger.log_info(f"Memory - Used: {used:,}, Limit: {limit:,}, Total: {total:,}")
            
            if is_memory_getting_full(used, limit):
                scraping_logger.log_info("WARNING: Memory usage is getting high!")
            
            # Scrolling variables
            scroll_count = 0
            no_response_count = 0
            combination_members = 0
            
            print(f"🔽 Starting to scroll through members for '{combination}'...")
            
            # Scroll and process members
            while scroll_count < 211:  # Arbitrary limit to prevent infinite scrolling
                # Process members at certain intervals
                if scroll_count in {100, 110, 130, 150, 160, 170, 180, 190, 200, 210}:
                    print(f"📋 Processing members at scroll count {scroll_count}...")
                    new_processed, total_members_scraped, should_continue = process_new_members(
                        driver, data_saver, member_tracker, combination, max_members, total_members_scraped
                    )
                    combination_members += new_processed
                    print(f"✅ Processed {new_processed} members. Total so far: {total_members_scraped}")
                    
                    if not should_continue:  # Hit member limit
                        scraping_logger.log_session_complete(total_members_scraped, len(combinations))
                        return total_members_scraped

                # Try to scroll down using component
                old_height, new_height = scroll_to_bottom(driver, wait_seconds=1)

                print(f"📜 Scroll attempt {scroll_count}: height {old_height} → {new_height}")

                if has_page_scrolled(old_height, new_height):
                    scroll_count += 1
                    no_response_count = 0
                    print(f"✅ Page scrolled successfully (count: {scroll_count})")
                else:
                    print(f"⏸️ No scroll detected, trying load button...")
                    # Try clicking the "load more" button using component
                    load_selectors = [GroupSelectors.LOAD_MORE_BUTTON] + GroupSelectors.LOAD_MORE_XPATH_FALLBACKS
                    if click_load_more(driver, load_selectors, timeout=2):
                        print(f"🔘 Clicked load more button")
                        scroll_count += 1
                        no_response_count += 1
                    else:
                        print(f"❌ No load button found")
                        scroll_count += 1
                        no_response_count += 1
                        
                        # If we can't scroll or click load button multiple times, give up
                        if no_response_count > 3:
                            print("⛔ No more content available, moving to next combination")
                            scraping_logger.log_info("No more content to load")
                            break
            
            # Process any remaining members
            print(f"\n📋 Final processing of remaining members...")
            final_processed, total_members_scraped, _ = process_new_members(
                driver, data_saver, member_tracker, combination, max_members, total_members_scraped
            )
            combination_members += final_processed
            
            # Log what we accomplished
            print(f"\n🎉 COMBINATION '{combination}' COMPLETED!")
            print(f"   👥 Members processed: {combination_members}")
            print(f"   📊 Running total: {total_members_scraped}")
            scraping_logger.log_combination_complete(combination, combination_members, total_members_scraped)
            
            # Check if we hit the limit
            if max_members and total_members_scraped >= max_members:
                print(f"🏁 STOPPING: Reached member limit!")
                break
        
        # We're done!
        scraping_logger.log_session_complete(total_members_scraped, len(combinations))
        
    except KeyboardInterrupt:
        # User pressed Ctrl+C
        current_combination = combinations[min(start_index + i - 1, len(combinations) - 1)] if 'i' in locals() else "Unknown"
        scraping_logger.log_session_interrupted(total_members_scraped, current_combination)
        print(f"\n⚠️ Scraping stopped by user. Progress saved. Total scraped: {total_members_scraped}")
        return total_members_scraped
    except Exception as e:
        # Something went wrong
        scraping_logger.log_error(f"Unexpected error: {str(e)}")
        current_combination = combinations[min(start_index + i - 1, len(combinations) - 1)] if 'i' in locals() else "Unknown"
        scraping_logger.log_session_interrupted(total_members_scraped, current_combination)
        raise
    
    print(f"\n🎉 Scraping completed! Total members scraped: {total_members_scraped}")
    return total_members_scraped


def extract_group_id_from_url(url):
    """Get group ID from LinkedIn group URL"""
    # Look for pattern like: /groups/12345678/
    match = re.search(r'/groups/(\d+)/', url)
    if match:
        return match.group(1)
    
    # If we can't find it, use timestamp
    return f"group_{int(time.time())}"


def get_scraping_mode():
    """Ask user which scraping mode they want"""
    print("\n🎯 LinkedIn Group Scraper - Choose Your Mode")
    print("Available options:")
    print("1. Light - Single letters only (26 combinations) - Quick & Easy")
    print("2. Medium - Single + double letters (702 combinations) - Good Balance")
    print("3. Robust - Everything + common patterns (1000+ combinations) - Most Thorough")
    
    mode_choice = input("\n🔧 Select mode (light/medium/robust) [default: medium]: ").lower().strip()
    
    if not mode_choice:
        mode_choice = 'medium'
    
    if mode_choice not in ['light', 'medium', 'robust']:
        print("⚠️ Invalid choice. Using 'medium' as default.")
        mode_choice = 'medium'
    
    # Show what we're going to do
    combo_gen = CombinationGenerator()
    combinations = combo_gen.get_combinations(mode_choice)
    print(f"✅ Selected {mode_choice} mode with {len(combinations)} combinations")
    
    return mode_choice


def run_scraper_with_logging(driver, url, max_members=None, group_id=None):
    """Easy way to run the scraper with all the bells and whistles"""
    
    # Ask user what mode they want
    scraping_mode = get_scraping_mode()
    
    # Get group ID if not provided
    if not group_id:
        group_id = extract_group_id_from_url(url)
    
    print(f"\n📁 Your log files will be:")
    print(f"   📝 Log: data/logs/group_steps_{group_id}.log")
    print(f"   💾 State: data/logs/group_state_{group_id}.json")
    
    # Run it!
    return scraper(driver, url, max_members, scraping_mode, group_id)