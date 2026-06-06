"""
Domain Finder v2.0 for Profile Enricher
Optimized company domain search with caching and parallel processing.

Features:
- Intelligent caching (cross-session with file persistence)
- Faster Google searches with minimal delays
- Better domain extraction
- Skip known non-company domains
"""
import time
import re
import json
import os
from urllib.parse import urlparse, quote_plus
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from typing import Dict, Optional, List


# In-memory cache
_domain_cache = {}

# Cache file path
CACHE_FILE = "data/db/domain_cache.json"

# Domains to skip (not company websites)
SKIP_DOMAINS = {
    'linkedin.com', 'facebook.com', 'twitter.com', 'instagram.com',
    'youtube.com', 'wikipedia.org', 'crunchbase.com', 'glassdoor.com',
    'indeed.com', 'bloomberg.com', 'reuters.com', 'forbes.com',
    'google.com', 'bing.com', 'yahoo.com', 'amazon.com',
    'github.com', 'stackoverflow.com', 'medium.com',
    'zoominfo.com', 'apollo.io', 'yelp.com', 'time.com', 'nytimes.com',
    'wsj.com', 'cnbc.com', 'rocketreach.co', 'dnb.com', 'capterra.com',
    'g2.com', 'trustpilot.com', 'upwork.com', 'fiverr.com', 'freelancer.com',
}

# Flag to track if popup was handled this session
_popup_handled = False


def load_cache():
    """Load domain cache from file"""
    global _domain_cache
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                _domain_cache = json.load(f)
                print(f"📂 Loaded {len(_domain_cache)} cached domains")
    except Exception:
        _domain_cache = {}


def save_cache():
    """Save domain cache to file"""
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(_domain_cache, f, indent=2)
    except Exception:
        pass


def clear_cache():
    """Clear domain cache"""
    global _domain_cache
    _domain_cache = {}
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
    print("🗑️ Domain cache cleared")


def _handle_google_popup(driver):
    """Handle Google consent popup — delegates to component."""
    global _popup_handled
    
    if _popup_handled:
        return
    
    from components.common.popups import handle_google_consent
    if handle_google_consent(driver):
        _popup_handled = True


def clean_company_name(name: str) -> str:
    """Clean company name for better search results."""
    if not name:
        return ""
        
    generic_terms = ["self-employed", "freelance", "independent contractor", "full-time", "part-time", "contract"]
    name_lower = name.lower().strip()
    for term in generic_terms:
        if name_lower == term:
            return ""
            
    # Clean up legal suffixes
    suffixes = [
        r'\binc\b\.?', r'\bllc\b\.?', r'\bltd\b\.?', r'\bcorp\b\.?', 
        r'\bcorporation\b', r'\bgmbh\b', r'\bsa\b', r'\bas\b', r'\bplc\b'
    ]
    cleaned = name
    for suffix in suffixes:
        cleaned = re.sub(suffix, '', cleaned, flags=re.IGNORECASE)
        
    # Remove extra spaces and punctuation
    cleaned = re.sub(r'[^a-zA-Z0-9\s&]', ' ', cleaned)
    cleaned = ' '.join(cleaned.split())
    
    return cleaned


def extract_domain_from_url(url: str) -> Optional[str]:
    """
    Extract clean domain from URL.
    
    Examples:
        "https://www.al-enterprise.com/en/" -> "al-enterprise.com"
        "https://about.google" -> "google.com"
    """
    if not url:
        return None
    
    try:
        from urllib.parse import parse_qs
        parsed = urlparse(url)
        
        # Handle Google tracking redirect links
        if 'google.' in parsed.netloc and '/url' in parsed.path:
            query_params = parse_qs(parsed.query)
            if 'q' in query_params:
                url = query_params['q'][0]
                parsed = urlparse(url)

        domain = parsed.netloc or parsed.path
        
        # Remove www. prefix
        domain = re.sub(r'^www\.', '', domain, flags=re.IGNORECASE)
        
        # Remove trailing slashes and paths
        domain = domain.split('/')[0]
        
        # Skip if in blocklist
        if domain.lower() in SKIP_DOMAINS:
            return None
        
        # Must have at least one dot
        if '.' not in domain:
            return None
        
        return domain.lower() if domain else None
        
    except Exception:
        return None


def search_company_domain(driver, company_name: str, use_cache: bool = True) -> Optional[str]:
    """
    Search Google for company domain - optimized version.
    
    Args:
        driver: Selenium WebDriver
        company_name: Company name to search
        use_cache: Use cached results
        
    Returns:
        Domain string or None
    """
    cleaned_company_name = clean_company_name(company_name)
    if not cleaned_company_name:
        print(f"    ⚠️ Skipping generic or empty company: '{company_name}'")
        return None

    # Normalize company name for cache key
    cache_key = cleaned_company_name.strip().lower()
    
    # Check memory cache
    if use_cache and cache_key in _domain_cache:
        cached = _domain_cache[cache_key]
        if cached:  # Only log if domain was found
            print(f"    💾 Cached: {cached}")
        return cached
    
    try:
        # Add "official website" to improve results
        search_query = f"{cleaned_company_name} official website"
        google_url = f"https://www.google.com/search?q={quote_plus(search_query)}&num=10"
        
        print(f"    🔍 Searching...")
        driver.get(google_url)
        
        # Handle popup once per session
        _handle_google_popup(driver)
        
        # Wait for results (short timeout)
        try:
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#search"))
            )
        except TimeoutException:
            _domain_cache[cache_key] = None
            return None
        
        # Extract domains from search results
        result_links = driver.find_elements(By.CSS_SELECTOR, "div#search a[href]")
        
        for link in result_links[:5]:  # Check first 5 results
            try:
                href = link.get_attribute('href')
                if href and href.startswith('http'):
                    domain = extract_domain_from_url(href)
                    if domain:
                        print(f"    ✓ Found: {domain}")
                        _domain_cache[cache_key] = domain
                        save_cache()  # Persist to file
                        return domain
            except Exception:
                continue
        
        print(f"    ⚠️ No domain found")
        _domain_cache[cache_key] = None
        return None
        
    except Exception as e:
        print(f"    ❌ Error: {e}")
        _domain_cache[cache_key] = None
        return None


def search_multiple_companies(driver, companies: List[str], delay: float = 1.5) -> Dict[str, str]:
    """
    Search domains for multiple companies - optimized.
    
    Args:
        driver: Selenium WebDriver
        companies: List of company names
        delay: Delay between searches (seconds)
        
    Returns:
        Dict mapping company names to domains
    """
    # Load cache at start
    load_cache()
    
    results = {}
    
    for i, company in enumerate(companies):
        company = company.strip()
        if not company:
            continue
        
        print(f"  [{i+1}/{len(companies)}] {company}")
        
        domain = search_company_domain(driver, company)
        if domain:
            results[company] = domain
        
        # Delay between searches (but not after last one)
        if i < len(companies) - 1:
            time.sleep(delay)
    
    return results


def get_cached_domain(company_name: str) -> Optional[str]:
    """Get domain from cache without searching"""
    load_cache()
    return _domain_cache.get(company_name.strip().lower())


def add_to_cache(company_name: str, domain: str):
    """Manually add a domain to cache"""
    _domain_cache[company_name.strip().lower()] = domain.lower()
    save_cache()


if __name__ == "__main__":
    # Test cache operations
    print("Domain Finder v2.0 Test")
    print("=" * 50)
    
    load_cache()
    print(f"Cache entries: {len(_domain_cache)}")
    
    # Show some cached entries
    for company, domain in list(_domain_cache.items())[:5]:
        print(f"  {company} -> {domain}")
