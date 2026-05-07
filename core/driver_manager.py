"""
Chrome Driver Manager - Centralized driver setup and management.
Auto-updates ChromeDriver to match Chrome version.
"""
import logging
import tempfile
import time
import os
import ssl

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

logger = logging.getLogger(__name__)


class DriverManager:
    """Manages Chrome WebDriver instances for scraping."""

    @staticmethod
    def _get_chromedriver_path():
        """Auto-download ChromeDriver matching Chrome version.
        Handles SSL issues by disabling verification if needed.
        """
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            # Patch SSL issue for corporate firewalls
            original_context = ssl.create_default_context
            ssl._create_default_https_context = ssl._create_unverified_context

            manager = ChromeDriverManager()
            driver_path = manager.install()

            # Restore SSL context
            ssl._create_default_https_context = original_context

            logger.info("ChromeDriver auto-installed: %s", driver_path)
            return driver_path
        except Exception as e:
            logger.warning("webdriver_manager failed: %s", e)
            return None

    @staticmethod
    def setup_chrome_driver():
        """Set up Chrome with anti-detection configuration.

        Auto-downloads matching ChromeDriver version.

        Returns:
            tuple: (driver, temp_profile_path)
        """
        options = Options()

        # Anti-detection
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # Performance / compatibility
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--memory-pressure-off")

        # User agent (use current Chrome version)
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/148.0.7778.96 Safari/537.36"
        )
        options.add_argument(f"--user-agent={user_agent}")

        # Temporary profile
        temp_profile = tempfile.mkdtemp(prefix="chrome_profile_")
        options.add_argument(f"--user-data-dir={temp_profile}")

        # Get ChromeDriver (auto-download if needed)
        driver_path = DriverManager._get_chromedriver_path()

        logger.info("Starting Chrome browser...")
        if driver_path:
            service = Service(executable_path=driver_path)
            driver = webdriver.Chrome(service=service, options=options)
        else:
            # Fallback: let Selenium try its own way
            driver = webdriver.Chrome(options=options)

        # Remove automation indicators
        driver.execute_cdp_cmd(
            "Network.setUserAgentOverride", {"userAgent": user_agent}
        )

        driver.set_page_load_timeout(30)

        logger.info("Chrome driver setup complete")
        return driver, temp_profile

    @staticmethod
    def cleanup_driver(driver, temp_profile=None):
        """Clean up driver and temporary profile.

        Args:
            driver: Selenium WebDriver instance
            temp_profile: Path to temporary profile directory
        """
        if driver:
            try:
                logger.info("Closing browser...")
                time.sleep(2)
                driver.quit()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.warning("Error closing browser: %s", e)

        if temp_profile:
            try:
                import shutil
                shutil.rmtree(temp_profile, ignore_errors=True)
                logger.info("Temporary profile cleaned up")
            except Exception as e:
                logger.warning("Could not clean temp profile: %s", e)
