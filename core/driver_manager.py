"""
Chrome Driver Manager - Centralized driver setup and management
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import os
import tempfile
import time


class DriverManager:
    """Manages Chrome WebDriver instances for scraping"""
    
    @staticmethod
    def setup_chrome_driver():
        """Setup Chrome with basic configuration for smart search scraping
        
        Returns:
            tuple: (driver, temp_profile_path)
        """
        
        # Possible paths for chromedriver.exe
        driver_paths = [
            "./chromedriver.exe",
            "C:/chromedriver/chromedriver.exe", 
            "C:/WebDrivers/chromedriver.exe",
            "./drivers/chromedriver.exe",
        ]
        
        driver_path = None
        for path in driver_paths:
            if os.path.exists(path):
                driver_path = path
                print(f"Found ChromeDriver at: {path}")
                break
        
        if not driver_path:
            print("ChromeDriver not found! Please download and place it in one of these locations:")
            for path in driver_paths:
                print(f"  - {path}")
            raise Exception("ChromeDriver executable not found")
        
        # Chrome options optimized for search-based scraping
        options = webdriver.ChromeOptions()
        
        # Anti-detection options
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Basic performance options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-debugging-port=9222")

        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        
        # Memory management
        options.add_argument("--memory-pressure-off")
        options.add_argument("--max_old_space_size=2048")
        
        # User agent
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Use temporary profile
        temp_profile = tempfile.mkdtemp(prefix="chrome_profile_")
        options.add_argument(f"--user-data-dir={temp_profile}")
        
        # Create service and driver
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        
        # Remove automation indicators
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # Set reasonable timeouts
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)
        
        print("🚀 Chrome driver setup complete!")
        return driver, temp_profile
    
    @staticmethod
    def cleanup_driver(driver, temp_profile=None):
        """Clean up driver and temporary profile
        
        Args:
            driver: Selenium WebDriver instance
            temp_profile: Path to temporary profile directory
        """
        if driver:
            try:
                print("🧹 Cleaning up browser...")
                time.sleep(2)  # Brief pause before cleanup
                driver.quit()
                print("✅ Browser closed successfully")
            except Exception as e:
                print(f"⚠️ Error closing browser: {e}")
        
        # Note: temp_profile cleanup is handled by OS for now
        # Can implement explicit cleanup if needed
