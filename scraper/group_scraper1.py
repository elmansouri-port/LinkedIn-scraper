# scraper/group_scraper.py
import time
import logging
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from utils.group_data_saver import GroupDataSaver

def extract_group_id_from_url(group_url: str) -> str:
    """Extract group ID from LinkedIn group URL"""
    match = re.search(r'/groups/(\d+)', group_url)
    return match.group(1) if match else "unknown"

def scrape_group_members(driver, group_url: str, max_members: int = None):
    """
    Scrape LinkedIn group members with infinite scroll handling
    
    Args:
        driver: Selenium WebDriver instance
        group_url: URL of the LinkedIn group (from config.settings)
        max_members: Maximum number of members to scrape (None for unlimited)
    """
    try:
        # Ask user for max members if not provided
        if max_members is None:
            max_input = input("\n📊 Enter maximum number of members to scrape (press Enter for unlimited): ").strip()
            if max_input:
                try:
                    max_members = int(max_input)
                    print(f"📈 Will scrape maximum {max_members} members")
                except ValueError:
                    print("⚠️ Invalid number entered, will scrape unlimited members")
                    max_members = None
            else:
                print("📈 Will scrape unlimited members (until stopped or end reached)")
        
        print(f"🔍 Navigating to group: {group_url}")
        driver.get(group_url)
        
        wait = WebDriverWait(driver, 15)
        
        # Wait for the page to load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        print("✅ Group page loaded successfully!")
        
        # Extract group ID for file naming
        group_id = extract_group_id_from_url(group_url)
        print(f"📋 Group ID: {group_id}")
        
        # Initialize data saver
        data_saver = GroupDataSaver(group_id=group_id, batch_size=10)
        
        # Navigate to members section
        print("🔄 Navigating to members section...")
        try:
            # Look for members tab/link
            members_link = wait.until(EC.element_to_be_clickable((
                By.XPATH, "//a[contains(@href, '/members') or contains(text(), 'Members') or contains(text(), 'Show more results')]"
            )))
            
            members_link.click()
            time.sleep(3)
        except TimeoutException:
            print("⚠️ Could not find members link, assuming we're already on members page")
        
        # Wait for members list to load
        try:
            wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR, ".groups-members-list, .artdeco-list, .artdeco-entity-lockup"
            )))
        except TimeoutException:
            print("❌ Members list not found")
            return
        
        print("📋 Members list found, starting extraction...")
        
        scraped_members = set()  # Track scraped members to avoid duplicates
        consecutive_no_new_members = 0
        max_consecutive_attempts = 5
        
        while True:
            # Check if we've reached the max limit
            if max_members and data_saver.total_saved >= max_members:
                print(f"✅ Reached maximum members limit: {max_members}")
                break
            
            # STEP 1: Extract all currently visible members first
            print("📋 Extracting all currently visible members...")
            initial_scraped_count = len(scraped_members)
            new_members_found = extract_all_visible_members_optimized(driver, scraped_members, data_saver, max_members)
            
            print(f"📈 New members extracted in this round: {new_members_found}")
            
            # Check if we reached max limit during extraction
            if max_members and data_saver.total_saved + len(data_saver.members_buffer) >= max_members:
                print(f"✅ Reached maximum members limit during extraction: {max_members}")
                data_saver.save_remaining()
                return
            
            # If no new members found, increment counter
            if new_members_found == 0:
                consecutive_no_new_members += 1
                print(f"⚠️ No new members found (attempt {consecutive_no_new_members}/{max_consecutive_attempts})")
                
                if consecutive_no_new_members >= max_consecutive_attempts:
                    print("⚠️ No new members found in multiple attempts, reached the end")
                    break
            else:
                consecutive_no_new_members = 0
            
            # Print current stats
            stats = data_saver.get_stats()
            print(f"📊 Current stats: {stats['total_saved']} saved, {stats['buffer_size']} in buffer")
            
            # STEP 2: Try to load more members
            print("🔄 Attempting to load more members...")
            load_success = load_more_members_optimized(driver, wait)
            
            if not load_success:
                print("📄 Could not load more members, might have reached the end")
                break
            
            # STEP 3: Wait for new content to load
            print("⏳ Waiting for new members to load...")
            if not wait_for_new_members_to_load(driver, initial_scraped_count + len(scraped_members)):
                print("⚠️ No new members loaded after waiting")
                consecutive_no_new_members += 1
                if consecutive_no_new_members >= max_consecutive_attempts:
                    break
            
            # Small delay to avoid being too aggressive
            time.sleep(1)
        
        # Save any remaining members
        data_saver.save_remaining()
        
        final_stats = data_saver.get_stats()
        print(f"🎉 Scraping completed!")
        print(f"📈 Total members scraped: {final_stats['total_saved']}")
        print(f"💾 Data saved to: {data_saver.get_filepath()}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Scraping interrupted by user")
        if 'data_saver' in locals():
            data_saver.save_remaining()
            final_stats = data_saver.get_stats()
            print(f"💾 Saved {final_stats['total_saved']} members before interruption")
        
    except Exception as e:
        print(f"❌ Error scraping group: {e}")
        logging.error(f"Error details: {e}", exc_info=True)
        if 'data_saver' in locals():
            data_saver.save_remaining()

def extract_member_data_batch(driver, member_elements: list) -> list:
    """
    Extract member data from multiple elements using batch processing with JavaScript
    This is much faster than individual DOM queries
    """
    try:
        # JavaScript code to extract all member data at once
        js_script = """
        var elements = arguments[0];
        var results = [];
        
        for (var i = 0; i < elements.length; i++) {
            var element = elements[i];
            var memberData = {};
            
            try {
                // Extract name
                var nameEl = element.querySelector('.artdeco-entity-lockup__title');
                memberData.name = nameEl ? nameEl.textContent.trim() : '';
                
                // Extract profile URL
                var linkEl = element.querySelector('a[href*="/in/"]');
                if (linkEl && linkEl.href) {
                    memberData.profile_url = linkEl.href.split('?')[0];
                } else {
                    memberData.profile_url = '';
                }
                
                // Extract title/subtitle
                var titleEl = element.querySelector('.artdeco-entity-lockup__subtitle');
                memberData.title = titleEl ? titleEl.textContent.trim() : '';
                
                // Check if verified
                var verifiedEl = element.querySelector('[data-test-icon="verified-small"]');
                memberData.verified = verifiedEl ? 'Yes' : 'No';
                
                // Extract profile image URL
                var imgEl = element.querySelector('.presence-entity__image');
                memberData.profile_image_url = imgEl ? imgEl.src : '';
                
                // Only add if we have name or profile URL
                if (memberData.name || memberData.profile_url) {
                    results.push(memberData);
                }
                
            } catch (e) {
                // Skip this element if extraction fails
                continue;
            }
        }
        
        return results;
        """
        
        # Execute JavaScript to extract all data at once
        return driver.execute_script(js_script, member_elements)
        
    except Exception as e:
        logging.error(f"Error in batch extraction: {e}")
        # Fallback to individual extraction if batch fails
        return extract_member_data_fallback(member_elements)

def extract_member_data_fallback(member_elements: list) -> list:
    """
    Fallback method for individual member data extraction
    """
    results = []
    for element in member_elements:
        try:
            member_data = extract_member_data(element)
            if member_data:
                results.append(member_data)
        except Exception as e:
            logging.warning(f"Error extracting member data: {e}")
            continue
    return results

def extract_member_data(member_element) -> dict:
    """
    Extract member data from a member element based on the actual HTML structure
    """
    try:
        member_data = {}
        
        # Extract name from the title element
        try:
            name_element = member_element.find_element(By.CSS_SELECTOR, 
                ".artdeco-entity-lockup__title")
            member_data['name'] = name_element.text.strip()
        except NoSuchElementException:
            member_data['name'] = ""
        
        # Extract profile URL from the main link
        try:
            profile_link = member_element.find_element(By.CSS_SELECTOR, 
                "a[href*='/in/']")
            href = profile_link.get_attribute('href')
            if href:
                member_data['profile_url'] = href.split('?')[0]
            else:
                member_data['profile_url'] = ""
        except NoSuchElementException:
            member_data['profile_url'] = ""
        
        # Extract title/subtitle (job title)
        try:
            title_element = member_element.find_element(By.CSS_SELECTOR, 
                ".artdeco-entity-lockup__subtitle")
            member_data['title'] = title_element.text.strip()
        except NoSuchElementException:
            member_data['title'] = ""
        
        # Check if verified (look for the verified icon)
        try:
            verified_element = member_element.find_element(By.CSS_SELECTOR, 
                "[data-test-icon='verified-small']")
            member_data['verified'] = "Yes"
        except NoSuchElementException:
            member_data['verified'] = "No"
        
        # Extract profile image URL
        try:
            img_element = member_element.find_element(By.CSS_SELECTOR, 
                ".presence-entity__image")
            member_data['profile_image_url'] = img_element.get_attribute('src')
        except NoSuchElementException:
            member_data['profile_image_url'] = ""
        
        # Only return data if we have at least a name or profile URL
        if member_data.get('name') or member_data.get('profile_url'):
            return member_data
        else:
            return None
        
    except Exception as e:
        logging.warning(f"Error extracting member data: {e}")
        return None

def extract_all_visible_members_optimized(driver, scraped_members: set, data_saver, max_members: int = None) -> int:
    """
    OPTIMIZED version: Extract all currently visible members using batch processing
    
    Args:
        driver: Selenium WebDriver instance
        scraped_members: Set of already scraped member profile URLs
        data_saver: GroupDataSaver instance
        max_members: Maximum number of members to scrape
    
    Returns:
        int: Number of new members found and extracted
    """
    try:
        # Find all member elements using the correct selector from the HTML
        member_elements = driver.find_elements(By.CSS_SELECTOR, 
            "li.groups-members-list__typeahead-result")
        
        print(f"📊 Found {len(member_elements)} member elements on current page")
        
        if not member_elements:
            return 0
        
        # OPTIMIZATION: Use batch processing with JavaScript
        print("⚡ Processing members with batch extraction...")
        start_time = time.time()
        
        # Extract all member data at once using JavaScript
        members_data = extract_member_data_batch(driver, member_elements)
        
        extraction_time = time.time() - start_time
        print(f"⚡ Batch extraction completed in {extraction_time:.2f} seconds")
        
        new_members_count = 0
        
        # Process the extracted data
        for member_data in members_data:
            try:
                # Check if we've reached the max limit
                if max_members and data_saver.total_saved + len(data_saver.members_buffer) >= max_members:
                    print(f"✅ Reached maximum members limit during extraction: {max_members}")
                    break
                
                if member_data and member_data.get('profile_url') and member_data['profile_url'] not in scraped_members:
                    scraped_members.add(member_data['profile_url'])
                    data_saver.add_member(member_data)
                    new_members_count += 1
                    
                    # Print every 10th member to avoid spam
                    if new_members_count % 10 == 0 or new_members_count <= 5:
                        name = member_data.get('name', 'Unknown')
                        title = member_data.get('title', '')[:50]
                        print(f"✅ Extracted: {name} - {title}...")
                    
            except Exception as e:
                logging.warning(f"⚠️ Error processing member data: {e}")
                continue
        
        processing_time = time.time() - start_time
        print(f"⚡ Total processing completed in {processing_time:.2f} seconds")
        print(f"📈 Processed {len(members_data)} members, found {new_members_count} new ones")
        
        return new_members_count
        
    except Exception as e:
        logging.error(f"Error in extract_all_visible_members_optimized: {e}")
        # Fallback to original method
        print("⚠️ Falling back to individual extraction...")
        return extract_all_visible_members_fallback(driver, scraped_members, data_saver, max_members)

def extract_all_visible_members_fallback(driver, scraped_members: set, data_saver, max_members: int = None) -> int:
    """
    Fallback to original individual extraction method
    """
    try:
        member_elements = driver.find_elements(By.CSS_SELECTOR, 
            "li.groups-members-list__typeahead-result")
        
        print(f"📊 Found {len(member_elements)} member elements on current page (fallback mode)")
        
        new_members_count = 0
        
        for i, member_element in enumerate(member_elements):
            try:
                # Check if we've reached the max limit
                if max_members and data_saver.total_saved + len(data_saver.members_buffer) >= max_members:
                    print(f"✅ Reached maximum members limit during extraction: {max_members}")
                    break
                
                # Extract member data
                member_data = extract_member_data(member_element)
                
                if member_data and member_data['profile_url'] not in scraped_members:
                    scraped_members.add(member_data['profile_url'])
                    data_saver.add_member(member_data)
                    new_members_count += 1
                    
                    # Print every 10th member to avoid spam
                    if new_members_count % 10 == 0 or new_members_count <= 5:
                        print(f"✅ Extracted: {member_data['name']} - {member_data['title'][:50]}...")
                    
            except Exception as e:
                logging.warning(f"⚠️ Error extracting member data: {e}")
                continue
        
        return new_members_count
        
    except Exception as e:
        logging.error(f"Error in extract_all_visible_members_fallback: {e}")
        return 0

def load_more_members_optimized(driver, wait) -> bool:
    """
    Optimized function to load more members by first trying the "Show more results" button,
    then falling back to scrolling if needed. Handles stale element references.
    
    Args:
        driver: Selenium WebDriver instance
        wait: Selenium WebDriverWait instance
    
    Returns:
        bool: True if loading was attempted, False if no loading method available
    """
    try:
        print("🔄 Looking for 'Show more results' button...")
        
        # Strategy 1: Try to find and click the "Show more results" button with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Re-find the button each time to avoid stale element references
                show_more_button = driver.find_element(By.CSS_SELECTOR, 
                    "button.scaffold-finite-scroll__load-button")
                
                if show_more_button.is_displayed() and show_more_button.is_enabled():
                    print(f"🔘 Found 'Show more results' button (attempt {attempt + 1})")
                    
                    # Scroll the button into view
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                                        show_more_button)
                    time.sleep(1)
                    
                    # Try to click the button
                    try:
                        show_more_button.click()
                        print("✅ Successfully clicked 'Show more results' button")
                        time.sleep(2)  # Wait for the click to register
                        return True
                    except ElementClickInterceptedException:
                        # Try JavaScript click as fallback
                        driver.execute_script("arguments[0].click();", show_more_button)
                        print("✅ Successfully clicked 'Show more results' button (via JavaScript)")
                        time.sleep(2)  # Wait for the click to register
                        return True
                        
            except NoSuchElementException:
                print(f"⚠️ 'Show more results' button not found (attempt {attempt + 1})")
                break  # Button doesn't exist, no point retrying
            except Exception as e:
                if "stale element reference" in str(e).lower():
                    print(f"⚠️ Stale element reference (attempt {attempt + 1}), retrying...")
                    time.sleep(1)
                    continue  # Retry finding the element
                else:
                    logging.warning(f"Error clicking button (attempt {attempt + 1}): {e}")
                    if attempt == max_retries - 1:
                        break  # Last attempt failed, move to fallback
                    continue
        
        # Strategy 2: Fallback to infinite scroll approach
        print("🔄 Falling back to infinite scroll...")
        
        try:
            # Get current scroll position and page height
            current_scroll = driver.execute_script("return window.pageYOffset;")
            page_height = driver.execute_script("return document.body.scrollHeight;")
            
            # Scroll to bottom gradually
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(1)
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            # Check if we've reached the actual bottom or if new content loaded
            new_page_height = driver.execute_script("return document.body.scrollHeight;")
            new_scroll = driver.execute_script("return window.pageYOffset;")
            
            if new_page_height > page_height:
                print("✅ Page height increased - new content likely loaded via infinite scroll")
                return True
            elif new_scroll > current_scroll:
                print("✅ Scrolled to new position - waiting for potential content load")
                return True
            else:
                print("⚠️ No scroll change detected - might have reached the end")
                return False
                
        except Exception as e:
            logging.warning(f"Error during infinite scroll: {e}")
            return False
            
    except Exception as e:
        logging.warning(f"Error in load_more_members_optimized: {e}")
        return False

def wait_for_new_members_to_load(driver, initial_member_count: int, timeout: int = 15) -> bool:
    """
    Wait for new members to load by monitoring the number of member elements
    
    Args:
        driver: Selenium WebDriver instance
        initial_member_count: Initial count of members before loading
        timeout: Maximum time to wait in seconds
    
    Returns:
        bool: True if new members loaded, False if timeout or no new members
    """
    try:
        print(f"⏳ Waiting for new members to load (initial count: {initial_member_count})...")
        start_time = time.time()
        
        # First, wait a moment for the loading to potentially start
        time.sleep(2)
        
        while time.time() - start_time < timeout:
            # Check for loading indicators
            loading_indicators = driver.find_elements(By.CSS_SELECTOR, 
                ".scaffold-finite-scroll__loading, .loading, .spinner, [class*='loading']")
            
            if loading_indicators and any(el.is_displayed() for el in loading_indicators):
                print("🔄 Loading indicator visible, waiting...")
                time.sleep(2)
                continue
            
            # Count current members
            current_member_elements = driver.find_elements(By.CSS_SELECTOR, 
                "li.groups-members-list__typeahead-result")
            current_count = len(current_member_elements)
            
            if current_count > initial_member_count:
                print(f"✅ New members loaded! Count increased from {initial_member_count} to {current_count}")
                return True
            
            # Wait a bit more
            time.sleep(2)
        
        print(f"⏰ Timeout waiting for new members (final count: {len(driver.find_elements(By.CSS_SELECTOR, 'li.groups-members-list__typeahead-result'))})")
        return False
        
    except Exception as e:
        logging.warning(f"Error waiting for new members: {e}")
        return False

def scroll_and_wait(driver, max_scrolls: int = 5) -> bool:
    """
    Fallback method: Scroll down multiple times and wait for content
    
    Args:
        driver: Selenium WebDriver instance
        max_scrolls: Maximum number of scroll attempts
    
    Returns:
        bool: True if scrolling was performed, False otherwise
    """
    try:
        print("🔄 Fallback: Performing scroll and wait...")
        
        initial_height = driver.execute_script("return document.body.scrollHeight")
        
        for i in range(max_scrolls):
            # Scroll down
            driver.execute_script(f"window.scrollBy(0, {800 * (i + 1)});")
            time.sleep(2)
            
            # Check if height changed
            current_height = driver.execute_script("return document.body.scrollHeight")
            if current_height > initial_height:
                print(f"✅ Page height increased after scroll {i + 1}")
                time.sleep(3)  # Wait for content to settle
                return True
        
        print("⚠️ No height change detected after scrolling")
        return False
        
    except Exception as e:
        logging.warning(f"Error in scroll_and_wait: {e}")
        return False