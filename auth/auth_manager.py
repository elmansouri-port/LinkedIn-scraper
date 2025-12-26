"""
Unified Authentication Manager for LinkedIn Scraper
Handles both cookie-based and credential-based authentication
"""
import pickle
import os
import time
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Optional, Tuple


class AuthManager:
    """Centralized authentication manager for LinkedIn"""
    
    # Authentication data directory
    AUTH_DIR = Path(".auth")
    COOKIES_FILE = AUTH_DIR / "cookies.pkl"
    
    def __init__(self, email: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize AuthManager
        
        Args:
            email: LinkedIn email (optional, can use env var LINKEDIN_EMAIL)
            password: LinkedIn password (optional, can use env var LINKEDIN_PASSWORD)
        """
        # Ensure auth directory exists
        self.AUTH_DIR.mkdir(exist_ok=True)
        
        # Get credentials from parameters or environment variables
        self.email = email or os.getenv("LINKEDIN_EMAIL")
        self.password = password or os.getenv("LINKEDIN_PASSWORD")
    
    def login(self, driver, force_credentials: bool = False) -> bool:
        """
        Attempt to login to LinkedIn
        
        First tries cookie-based login, falls back to credentials if needed.
        
        Args:
            driver: Selenium WebDriver instance
            force_credentials: Force login with credentials even if cookies exist
            
        Returns:
            bool: True if login successful, False otherwise
        """
        # Try cookie login first (unless forced)
        if not force_credentials and self.COOKIES_FILE.exists():
            print("🔑 Attempting login with saved cookies...")
            if self.login_with_cookies(driver):
                return True
            print("⚠️  Cookie login failed, falling back to credentials...")
        
        # Fall back to credentials
        if self.email and self.password:
            print("🔑 Attempting login with credentials...")
            if self.login_with_credentials(driver):
                return True
        else:
            print("❌ No credentials available. Please set LINKEDIN_EMAIL and LINKEDIN_PASSWORD")
            return False
        
        return False
    
    def login_with_cookies(self, driver) -> bool:
        """
        Login using saved cookies
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            if not self.COOKIES_FILE.exists():
                return False
            
            print(f"📂 Loading cookies from {self.COOKIES_FILE}")
            driver.get("https://www.linkedin.com")
            
            # Load and add cookies
            with open(self.COOKIES_FILE, "rb") as file:
                cookies = pickle.load(file)
            
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    print(f"⚠️  Could not add cookie: {e}")
            
            driver.refresh()
            
            # Verify login success
            if self._verify_login(driver):
                print("✅ Cookie login successful!")
                return True
            else:
                print("❌ Cookie login failed (cookies may be expired)")
                return False
                
        except Exception as e:
            print(f"❌ Cookie login error: {e}")
            return False
    
    def login_with_credentials(self, driver) -> bool:
        """
        Login using email and password
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            print("📧 Navigating to LinkedIn login...")
            driver.get("https://www.linkedin.com/login")
            
            wait = WebDriverWait(driver, 15)
            
            # Wait for and fill login form
            print("⌨️  Filling in credentials...")
            email_input = wait.until(EC.element_to_be_clickable((By.ID, "username")))
            password_input = wait.until(EC.element_to_be_clickable((By.ID, "password")))
            
            email_input.clear()
            email_input.send_keys(self.email)
            
            password_input.clear()
            password_input.send_keys(self.password)
            
            # Human-like delay
            time.sleep(1)
            
            # Submit login
            login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
            login_button.click()
            
            print("⏳ Waiting for login response...")
            
            # Handle potential verification
            time.sleep(3)  # Brief wait for page to load
            
            current_url = driver.current_url
            if "challenge" in current_url or "checkpoint" in current_url:
                print("🔐 LinkedIn verification required!")
                print("Please complete the verification in the browser window.")
                input("Press Enter after completing verification...")
            
            # Verify login success
            if self._verify_login(driver):
                print("✅ Credential login successful!")
                self.save_cookies(driver)
                return True
            else:
                print("❌ Credential login failed")
                return False
                
        except Exception as e:
            print(f"❌ Credential login error: {e}")
            print(f"Current URL: {driver.current_url}")
            return False
    
    def save_cookies(self, driver) -> bool:
        """
        Save current session cookies
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            bool: True if cookies saved successfully
        """
        try:
            cookies = driver.get_cookies()
            with open(self.COOKIES_FILE, "wb") as file:
                pickle.dump(cookies, file)
            print(f"✅ Cookies saved to {self.COOKIES_FILE}")
            return True
        except Exception as e:
            print(f"❌ Error saving cookies: {e}")
            return False
    
    def clear_cookies(self) -> bool:
        """
        Delete saved cookies file
        
        Returns:
            bool: True if cookies deleted successfully
        """
        try:
            if self.COOKIES_FILE.exists():
                self.COOKIES_FILE.unlink()
                print(f"✅ Cookies deleted from {self.COOKIES_FILE}")
                return True
            else:
                print("ℹ️  No cookies file to delete")
                return False
        except Exception as e:
            print(f"❌ Error deleting cookies: {e}")
            return False
    
    def _verify_login(self, driver, timeout: int = 10) -> bool:
        """
        Verify if login was successful
        
        Args:
            driver: Selenium WebDriver instance
            timeout: Maximum time to wait for verification
            
        Returns:
            bool: True if logged in, False otherwise
        """
        try:
            wait = WebDriverWait(driver, timeout)
            wait.until(EC.any_of(
                EC.url_contains("/feed/"),
                EC.url_contains("/in/"),
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test-id='nav-user-profile']")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".global-nav__primary-link-me-menu-trigger"))
            ))
            return True
        except:
            return False
    
    @classmethod
    def from_env(cls) -> 'AuthManager':
        """
        Create AuthManager using environment variables
        
        Returns:
            AuthManager: Configured instance
        """
        return cls(
            email=os.getenv("LINKEDIN_EMAIL"),
            password=os.getenv("LINKEDIN_PASSWORD")
        )
    
    @classmethod
    def from_config(cls, config_module) -> 'AuthManager':
        """
        Create AuthManager from config module
        
        Args:
            config_module: Module with LINKEDIN_EMAIL and LINKEDIN_PASSWORD
            
        Returns:
            AuthManager: Configured instance
        """
        return cls(
            email=getattr(config_module, 'LINKEDIN_EMAIL', None),
            password=getattr(config_module, 'LINKEDIN_PASSWORD', None)
        )
