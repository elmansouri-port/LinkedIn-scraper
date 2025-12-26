# scraper/group_scraper.py
import time
import logging
import re
import string
from itertools import product
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from utils.group_data_saver import GroupDataSaver


class CombinationGenerator:
    """Generates different sets of combinations for scraping based on intensity level"""
    
    def __init__(self):
        self.alphabet = string.ascii_lowercase
        
    def generate_single_letters(self):
        """Generate single letter combinations (a-z)"""
        return list(self.alphabet)
    
    def generate_double_letters(self):
        """Generate all possible two-letter combinations (aa-zz)"""
        return [''.join(combo) for combo in product(self.alphabet, repeat=2)]
    
    def generate_common_name_patterns(self):
        """Generate common patterns found in names"""
        # Common prefixes and suffixes in names
        prefixes = ['al', 'an', 'br', 'ch', 'cl', 'cr', 'da', 'de', 'el', 'fr', 'ja', 'jo', 'ma', 'mi', 'pa', 'ra', 're', 'sa', 'th']
        suffixes = ['an', 'ar', 'el', 'en', 'er', 'es', 'ia', 'ic', 'ie', 'in', 'le', 'ly', 'na', 'ne', 'on', 'or', 'ry', 'son', 'ton']
        vowel_consonant = [''.join(combo) for combo in product('aeiou', 'bcdfghjklmnpqrstvwxyz')]
        consonant_vowel = [''.join(combo) for combo in product('bcdfghjklmnpqrstvwxyz', 'aeiou')]
        
        return list(set(prefixes + suffixes + vowel_consonant[:50] + consonant_vowel[:50]))
    
    def generate_three_letter_common(self):
        """Generate common three-letter combinations in names"""
        common_three = [
            'and', 'ben', 'can', 'dan', 'eva', 'ian', 'jan', 'jen', 'joe', 'jon',
            'ken', 'lea', 'len', 'max', 'sam', 'tom', 'van', 'ale', 'ali', 'ana',
            'ann', 'art', 'ben', 'bob', 'cal', 'cam', 'dan', 'don', 'eli', 'eva',
            'gab', 'guy', 'hal', 'ian', 'ida', 'ira', 'ivy', 'jay', 'jim', 'joe',
            'kim', 'lee', 'leo', 'liz', 'lou', 'mae', 'mel', 'mia', 'nat', 'ned',
            'pat', 'ray', 'rex', 'roy', 'sue', 'ted', 'tim', 'tom', 'vic', 'wes'
        ]
        return common_three

    def get_combinations(self, mode='light'):
        """
        Get combinations based on scraping mode
        
        Args:
            mode (str): 'light', 'medium', or 'robust'
        
        Returns:
            list: List of combinations to use for scraping
        """
        if mode == 'light':
            # Light scraping: single letters only
            combinations = self.generate_single_letters()
            print(f"Light mode: Using {len(combinations)} single letter combinations")
            
        elif mode == 'medium':
            # Medium scraping: single letters + all double letters
            single = self.generate_single_letters()
            double = self.generate_double_letters()
            combinations = single + double
            print(f"Medium mode: Using {len(combinations)} combinations (single + double letters)")
            
        elif mode == 'robust':
            # Robust scraping: everything + common three-letter patterns
            single = self.generate_single_letters()
            double = self.generate_double_letters()
            common_patterns = self.generate_common_name_patterns()
            three_letter = self.generate_three_letter_common()
            combinations = single + double + common_patterns + three_letter
            # Remove duplicates while preserving order
            combinations = list(dict.fromkeys(combinations))
            print(f"Robust mode: Using {len(combinations)} combinations (comprehensive set)")
            
        else:
            raise ValueError("Mode must be 'light', 'medium', or 'robust'")
        
        return combinations


def isscrolled(fhieght, lhieght):
    """Check if page scrolled successfully"""
    fhieght += 30
    return fhieght < lhieght


def get_memory_usage(driver):
    """Fetch current JS heap memory usage via CDP"""
    try:
        metrics = driver.execute_cdp_cmd("Performance.getMetrics", {})
        metric_dict = {m['name']: m['value'] for m in metrics['metrics']}
        
        used = metric_dict.get('UsedJSHeapSize', 0)
        total = metric_dict.get('TotalJSHeapSize', 0)
        limit = metric_dict.get('JSHeapSizeLimit', 0)
        
        return used, limit, total
    except Exception as e:
        print(f"Error fetching memory: {e}")
        return 0, 0, 0


def is_memory_critical(used, limit, threshold=0.9):
    """Check if memory usage exceeds threshold (e.g., 90%)"""
    if limit == 0:
        return False
    return (used / limit) > threshold


def scraper(driver, url, max_members, scraping_mode='medium'):
    """
    Main scraper function with configurable combination generation
    
    Args:
        driver: Selenium WebDriver instance
        url (str): URL to scrape
        max_members (int): Maximum number of members to scrape
        scraping_mode (str): 'light', 'medium', or 'robust'
    """
    
    # Generate combinations based on selected mode
    combo_generator = CombinationGenerator()
    combinations = combo_generator.get_combinations(scraping_mode)
    
    print(f"\nStarting scraper in {scraping_mode} mode with {len(combinations)} combinations")
    print("First 10 combinations:", combinations[:10])
    
    driver.get(url)
    wait = WebDriverWait(driver, 15)

    # Initialize the data saver
    data_saver = GroupDataSaver()
    
    total_members_scraped = 0

    for i, combination in enumerate(combinations, 1):
        print(f"\n--- Processing combination {i}/{len(combinations)}: '{combination}' ---")
        
        # Check if we've reached the maximum members limit
        if max_members and total_members_scraped >= max_members:
            print(f"Reached maximum members limit ({max_members}). Stopping.")
            break
        
        # Refresh the page to clear memory
        driver.refresh()
        time.sleep(1)

        try:
            search_input = wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[@aria-label="Chercher des membres"]'))
            )
        except TimeoutException:
            print(f"Could not find search input for combination '{combination}'. Skipping.")
            continue

        search_input.clear()
        time.sleep(0.5)
        search_input.send_keys(combination)
        time.sleep(1)

        # Monitor memory usage
        used, limit, total = get_memory_usage(driver)
        print(f"Memory usage - Used: {used:,}, Limit: {limit:,}, Total: {total:,}")
        
        if is_memory_critical(used, limit):
            print("WARNING: Memory usage is critical!")
        
        count = 0
        no_resp = 0
        combination_members = 0
        
        while count < 210:
            # Save data at specific intervals
            if count in {100, 110, 130, 150, 160, 170, 180, 190, 200, 210}:
                # Locate all member list items
                member_items = driver.find_elements(
                    By.CSS_SELECTOR, 
                    "ul.artdeco-list.groups-members-list__results-list li.artdeco-list__item"
                )
                print(f"Found {len(member_items)} members for combination '{combination}'")

                for item in member_items:
                    try:
                        # Check member limit
                        if max_members and total_members_scraped >= max_members:
                            print(f"Reached maximum members limit during processing.")
                            return total_members_scraped

                        # Get name
                        name_elem = item.find_element(By.CSS_SELECTOR, 
                            ".artdeco-entity-lockup__title a, .artdeco-entity-lockup__title")
                        name = name_elem.text.strip()

                        # Get profile link
                        try:
                            profile_anchor = item.find_element(By.CSS_SELECTOR, 
                                "a.ui-entity-action-row__link")
                            profile_link = profile_anchor.get_attribute("href")
                        except:
                            profile_link = "No profile link"

                        # Get headline
                        try:
                            headline = item.find_element(By.CSS_SELECTOR, 
                                ".artdeco-entity-lockup__subtitle").text.strip()
                        except:
                            headline = "No headline"

                        # Get profile image link
                        try:
                            profile_img_link = item.find_element(By.CSS_SELECTOR, 
                                "img.presence-entity__image").get_attribute("src")
                        except:
                            profile_img_link = "No image"

                        # Save data
                        data_saver.save_data(name, profile_link, headline, profile_img_link)
                        print(f"Saved: {name}")
                        
                        combination_members += 1
                        total_members_scraped += 1
                    
                    except Exception as e:
                        print(f"Error extracting member data: {e}")
                        continue

            # Scroll logic
            fhieght = driver.execute_script("return document.body.scrollHeight")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            lhieght = driver.execute_script("return document.body.scrollHeight")

            print(f"Scroll heights - Before: {fhieght}, After: {lhieght}")

            if isscrolled(fhieght, lhieght):
                count += 1
                no_resp = 0
                print(f"Scrolled successfully, count: {count}")
            else:
                try:
                    load_button = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 
                            "button.scaffold-finite-scroll__load-button"))
                    )
                    load_button.click()
                    count += 1
                    no_resp += 1
                    print(f"Clicked load button, count: {count}")
                except:
                    print(f"No load button found, count: {count}")
                    count += 1  # Increment to avoid infinite loop
                    
                    # If we can't scroll or click load button multiple times, break
                    if no_resp > 3:
                        print("Breaking due to no response")
                        break
        
        print(f"Completed combination '{combination}': {combination_members} members found")
    
    print(f"\nScraping completed! Total members scraped: {total_members_scraped}")
    return total_members_scraped


def get_scraping_mode():
    """Get user input for scraping mode selection"""
    print("\n🎯 LinkedIn Group Scraper - Mode Selection")
    print("Available scraping modes:")
    print(" Light - Single letters only (26 combinations) - Fast & Light")
    print(" Medium - Single + double letters (702 combinations) - Balanced")
    print(" Robust - Comprehensive set with common patterns (1000+ combinations) - Maximum Coverage")
    print("\nType Light or Medium or Robust !!!")
    
    mode_choice = input("\n🔧 Select scraping mode (light/medium/robust) [default: medium]: ").lower().strip()
    
    if not mode_choice:
        mode_choice = 'medium'
    
    if mode_choice not in ['light', 'medium', 'robust']:
        print("⚠️ Invalid mode. Using 'medium' as default.")
        mode_choice = 'medium'
    
    # Show what will be used
    combo_gen = CombinationGenerator()
    combinations = combo_gen.get_combinations(mode_choice)
    print(f"✅ Selected {mode_choice} mode with {len(combinations)} combinations")
    
    return mode_choice