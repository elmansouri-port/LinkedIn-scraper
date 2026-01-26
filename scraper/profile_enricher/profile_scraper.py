"""
LinkedIn Profile Scraper for Profile Enricher
Extracts name and company information from LinkedIn profiles
"""
import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def extract_profile_name(driver, profile_url):
    """
    Navigate to LinkedIn profile and extract first and last name
    
    Args:
        driver: Selenium WebDriver instance
        profile_url: LinkedIn profile URL
        
    Returns:
        Dictionary with first_name, last_name, and full_name
    """
    try:
        # Navigate to profile
        driver.get(profile_url)
        time.sleep(3)  # Wait for page load
        
        # Wait for profile to load
        wait = WebDriverWait(driver, 15)
        
        # Try multiple selectors for the name
        name_selectors = [
            "h1.text-heading-xlarge",
            "h1.inline.t-24.v-align-middle.break-words",
            "div.ph5 h1",
            "div.pv-text-details__left-panel h1"
        ]
        
        full_name = None
        for selector in name_selectors:
            try:
                name_element = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                full_name = name_element.text.strip()
                if full_name:
                    break
            except TimeoutException:
                continue
        
        if not full_name:
            raise ValueError("Could not extract profile name")
        
        # Split name into first and last
        name_parts = full_name.split()
        
        if len(name_parts) == 0:
            raise ValueError("Empty name")
        elif len(name_parts) == 1:
            first_name = name_parts[0]
            last_name = ""
        elif len(name_parts) == 2:
            first_name = name_parts[0]
            last_name = name_parts[1]
        else:
            # For names with more than 2 parts, take first as first_name
            # and rest as last_name (e.g., "Youssef El Mansouri" -> "Youssef", "El Mansouri")
            first_name = name_parts[0]
            last_name = ' '.join(name_parts[1:])
        
        return {
            'first_name': first_name,
            'last_name': last_name,
            'full_name': full_name
        }
        
    except Exception as e:
        raise Exception(f"Error extracting profile name: {str(e)}")


def extract_experience_companies(driver):
    """
    Extract all company names from the experience section
    
    Args:
        driver: Selenium WebDriver instance
        
    Returns:
        List of company names
    """
    companies = []
    
    try:
        # Scroll to experience section
        try:
            experience_section = driver.find_element(By.ID, "experience")
            driver.execute_script("arguments[0].scrollIntoView(true);", experience_section)
            time.sleep(2)
        except NoSuchElementException:
            print("⚠️ Experience section not found")
            return companies
        
        # Wait for experience items to load
        time.sleep(2)
        
        # Find all experience list items
        # Based on the HTML structure provided, look for list items in the experience section
        experience_selectors = [
            "section#experience ul.pvs-list li.artdeco-list__item",
            "section[data-view-name='profile-card'] ul li.artdeco-list__item",
            "div#experience ~ div ul li"
        ]
        
        experience_items = []
        for selector in experience_selectors:
            try:
                experience_items = driver.find_elements(By.CSS_SELECTOR, selector)
                if experience_items:
                    break
            except NoSuchElementException:
                continue
        
        if not experience_items:
            print("⚠️ No experience items found")
            return companies
        
        print(f"📋 Found {len(experience_items)} experience items")
        
        # Extract company names from each experience item
        for item in experience_items:
            try:
                # Look for company name in the t-14 t-normal span
                # Pattern: "Company Name · Employment Type"
                company_selectors = [
                    "span.t-14.t-normal span[aria-hidden='true']",
                    "span.t-14.t-normal",
                ]
                
                company_text = None
                for selector in company_selectors:
                    try:
                        company_element = item.find_element(By.CSS_SELECTOR, selector)
                        company_text = company_element.text.strip()
                        if company_text and '·' in company_text:
                            # Split by · and take the first part (company name)
                            company_name = company_text.split('·')[0].strip()
                            if company_name and company_name not in companies:
                                companies.append(company_name)
                                print(f"  ✓ Found company: {company_name}")
                            break
                    except NoSuchElementException:
                        continue
                        
            except Exception as e:
                # Skip this item if there's an error
                continue
        
        # Remove duplicates while preserving order
        seen = set()
        unique_companies = []
        for company in companies:
            if company not in seen:
                seen.add(company)
                unique_companies.append(company)
        
        return unique_companies
        
    except Exception as e:
        print(f"⚠️ Error extracting companies: {str(e)}")
        return companies


def scrape_profile_data(driver, profile_url):
    """
    Main function to scrape profile data (name + companies)
    
    Args:
        driver: Selenium WebDriver instance
        profile_url: LinkedIn profile URL
        
    Returns:
        Dictionary with profile data
    """
    try:
        # Extract name
        name_data = extract_profile_name(driver, profile_url)
        
        # Small delay between operations
        time.sleep(2)
        
        # Extract companies
        companies = extract_experience_companies(driver)
        
        # Combine data
        profile_data = {
            **name_data,
            'companies': companies,
            'url': profile_url
        }
        
        return profile_data
        
    except Exception as e:
        raise Exception(f"Error scraping profile: {str(e)}")
