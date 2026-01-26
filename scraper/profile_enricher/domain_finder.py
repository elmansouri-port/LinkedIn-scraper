"""
Domain Finder for Profile Enricher
Searches Google to find company website domains
"""
import time
import re
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


# Cache to avoid redundant Google searches
domain_cache = {}


def _handle_google_popup(driver):
    """
    Handle Google consent popup if present
    Reused from google_search_profile_scraper.py pattern
    """
    try:
        # Look for "Accept all" or "Reject all" buttons
        popup_selectors = [
            "button#L2AGLb",  # Accept all
            "div[jsname='V67aGc'] button",
            "button[aria-label*='Accept']",
            "button[aria-label*='Tout accepter']",
        ]
        
        for selector in popup_selectors:
            try:
                button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                button.click()
                print("✓ Handled Google popup")
                time.sleep(1)
                return
            except TimeoutException:
                continue
                
    except Exception:
        pass  # No popup found or already handled


def extract_domain_from_url(url):
    """
    Extract clean domain from URL
    
    Args:
        url: Full URL
        
    Returns:
        Domain name (e.g., "al-enterprise.com")
        
    Examples:
        "https://www.al-enterprise.com/en/" -> "al-enterprise.com"
        "https://orange.fr/portail" -> "orange.fr"
    """
    if not url:
        return None
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        
        # Remove www. prefix
        domain = re.sub(r'^www\.', '', domain, flags=re.IGNORECASE)
        
        # Remove trailing slashes and paths
        domain = domain.split('/')[0]
        
        return domain if domain else None
        
    except Exception:
        return None


def search_company_domain(driver, company_name, use_cache=True):
    """
    Search Google for company domain using "site:" search
    
    Args:
        driver: Selenium WebDriver instance
        company_name: Company name to search
        use_cache: Whether to use cached results
        
    Returns:
        Domain name string or None
        
    Examples:
        "Alcatel Lucent Enterprise" -> "al-enterprise.com"
        "Orange France" -> "orange.fr"
    """
    # Check cache first
    if use_cache and company_name in domain_cache:
        cached_domain = domain_cache[company_name]
        print(f"  💾 Using cached domain for '{company_name}': {cached_domain}")
        return cached_domain
    
    try:
        # Clean company name for search
        search_query = company_name.strip()
        
        # Search for the company on Google
        google_url = f"https://www.google.com/search?q={search_query}"
        
        print(f"  🔍 Searching Google for: {company_name}")
        driver.get(google_url)
        time.sleep(2)
        
        # Handle popup if present
        _handle_google_popup(driver)
        
        # Wait for search results
        time.sleep(2)
        
        # Try to find the first search result link
        result_selectors = [
            "div#search div.g a[href]",
            "div.g a[jsname='UWckNb']",
            "a[jsname='UWckNb']",
            "div#rso a[href]",
        ]
        
        result_links = []
        for selector in result_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    result_links = elements
                    break
            except NoSuchElementException:
                continue
        
        if not result_links:
            print(f"  ⚠️ No search results found for '{company_name}'")
            domain_cache[company_name] = None
            return None
        
        # Extract domains from top results (try first 3)
        for link in result_links[:3]:
            try:
                href = link.get_attribute('href')
                if href and href.startswith('http'):
                    # Skip Google-related URLs
                    if 'google.com' in href or 'youtube.com' in href:
                        continue
                    
                    # Skip LinkedIn, Facebook, Twitter, etc.
                    skip_domains = ['linkedin.com', 'facebook.com', 'twitter.com', 
                                    'instagram.com', 'wikipedia.org']
                    if any(skip in href for skip in skip_domains):
                        continue
                    
                    domain = extract_domain_from_url(href)
                    if domain:
                        print(f"  ✓ Found domain for '{company_name}': {domain}")
                        domain_cache[company_name] = domain
                        return domain
                        
            except Exception:
                continue
        
        print(f"  ⚠️ Could not find valid domain for '{company_name}'")
        domain_cache[company_name] = None
        return None
        
    except Exception as e:
        print(f"  ❌ Error searching for '{company_name}': {str(e)}")
        domain_cache[company_name] = None
        return None


def search_multiple_companies(driver, companies):
    """
    Search for domains of multiple companies
    
    Args:
        driver: Selenium WebDriver instance
        companies: List of company names
        
    Returns:
        Dictionary mapping company names to domains
    """
    company_domains = {}
    
    for i, company in enumerate(companies):
        print(f"\n[{i+1}/{len(companies)}] Searching for: {company}")
        
        domain = search_company_domain(driver, company)
        
        if domain:
            company_domains[company] = domain
        
        # Add delay between searches to avoid rate limiting
        if i < len(companies) - 1:
            delay = 3
            print(f"  ⏸️  Waiting {delay}s before next search...")
            time.sleep(delay)
    
    return company_domains


def clear_cache():
    """Clear the domain cache"""
    global domain_cache
    domain_cache = {}
    print("🗑️ Domain cache cleared")
