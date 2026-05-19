"""
Chrome Driver Manager - Centralized driver setup and management.
Auto-detects Chromium snap or Google Chrome, uses matching ChromeDriver.
Supports selecting and reusing existing browser profiles to avoid re-auth.
"""
import json
import logging
import re
import time
import os
import ssl
import shutil

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTH_DIR = os.path.join(BASE_DIR, ".auth")

# Chromium snap paths
SNAP_CHROMIUM_DRIVER = "/snap/chromium/current/usr/lib/chromium-browser/chromedriver"
SNAP_CHROMIUM_BINARY = "/snap/bin/chromium"

# Fallback fresh profile
DEFAULT_FRESH_PROFILE = os.path.join(AUTH_DIR, "chrome_profile")

# Profile choice persistence
PROFILE_CONFIG_PATH = os.path.join(AUTH_DIR, "profile_choice.json")


class DriverManager:
    """Manages Chrome WebDriver instances for scraping."""

    # ------------------------------------------------------------------
    # Browser / ChromeDriver detection
    # ------------------------------------------------------------------

    @staticmethod
    def _find_chromedriver_on_system():
        """Look for a chromedriver already installed on the system (snap, PATH, etc.)."""
        if os.path.exists(SNAP_CHROMIUM_DRIVER):
            logger.info("Found snap chromedriver: %s", SNAP_CHROMIUM_DRIVER)
            return SNAP_CHROMIUM_DRIVER

        system_driver = shutil.which("chromedriver")
        if system_driver:
            logger.info("Found chromedriver on PATH: %s", system_driver)
            return system_driver

        return None

    @staticmethod
    def _find_browser_binary():
        """Detect the installed Chromium/Chrome browser binary."""
        if os.path.exists(SNAP_CHROMIUM_BINARY):
            return SNAP_CHROMIUM_BINARY

        for name in ["chromium-browser", "chromium", "google-chrome", "google-chrome-stable"]:
            path = shutil.which(name)
            if path:
                return path

        return None

    @staticmethod
    def _get_chromedriver_path():
        """Get the correct ChromeDriver path — system driver or webdriver-manager."""
        system_driver = DriverManager._find_chromedriver_on_system()
        if system_driver:
            return system_driver

        try:
            from webdriver_manager.chrome import ChromeDriverManager

            original_context = ssl.create_default_context
            ssl._create_default_https_context = ssl._create_unverified_context

            manager = ChromeDriverManager()
            driver_path = manager.install()

            ssl._create_default_https_context = original_context

            logger.info("ChromeDriver auto-installed: %s", driver_path)
            return driver_path
        except Exception as e:
            logger.warning("webdriver_manager failed: %s", e)
            return None

    # ------------------------------------------------------------------
    # Profile detection
    # ------------------------------------------------------------------

    @staticmethod
    def get_data_dir():
        """Return the browser's user-data directory (parent of profiles).

        Returns:
            str or None: Path to the data dir.
        """
        # Chromium snap
        snap_dir = os.path.expanduser("~/snap/chromium/common/chromium")
        if os.path.isdir(snap_dir) and os.path.isfile(os.path.join(snap_dir, "Local State")):
            return snap_dir

        # Standard Chromium
        std_dir = os.path.expanduser("~/.config/chromium")
        if os.path.isdir(std_dir):
            return std_dir

        # Google Chrome
        chrome_dir = os.path.expanduser("~/.config/google-chrome")
        if os.path.isdir(chrome_dir):
            return chrome_dir

        return None

    @staticmethod
    def detect_profiles():
        """Scan for available browser profiles.

        Returns:
            list[dict]: Each entry has keys: 'name', 'dir' (profile dir name),
                        'data_dir' (parent), 'path' (full absolute path).
        """
        data_dir = DriverManager.get_data_dir()
        if not data_dir:
            return []

        local_state = os.path.join(data_dir, "Local State")
        if not os.path.isfile(local_state):
            return []

        try:
            with open(local_state) as f:
                state = json.load(f)
        except Exception:
            return []

        info_cache = state.get("profile", {}).get("info_cache", {})
        profiles = []
        for profile_dir, info in info_cache.items():
            profiles.append({
                "name": info.get("name", profile_dir),
                "dir": profile_dir,
                "data_dir": data_dir,
                "path": os.path.join(data_dir, profile_dir),
            })

        # Also check if a Default directory exists (not always in info_cache)
        default_path = os.path.join(data_dir, "Default")
        if os.path.isdir(default_path) and not any(p["dir"] == "Default" for p in profiles):
            profiles.insert(0, {
                "name": "Default",
                "dir": "Default",
                "data_dir": data_dir,
                "path": default_path,
            })

        return profiles

    # ------------------------------------------------------------------
    # Profile choice persistence
    # ------------------------------------------------------------------

    @staticmethod
    def clear_profile_choice():
        """Remove saved profile choice — next session uses a fresh profile."""
        if os.path.isfile(PROFILE_CONFIG_PATH):
            os.remove(PROFILE_CONFIG_PATH)
            logger.info("Profile choice cleared")

    @staticmethod
    def save_profile_choice(profile_dir, profile_name=None):
        """Persist the chosen profile for future sessions."""
        os.makedirs(AUTH_DIR, exist_ok=True)
        choice = {
            "profile_dir": profile_dir,
            "profile_name": profile_name or profile_dir,
        }
        with open(PROFILE_CONFIG_PATH, "w") as f:
            json.dump(choice, f)
        logger.info("Saved profile choice: %s", choice)

    @staticmethod
    def load_profile_choice():
        """Load the previously saved profile choice.

        Returns:
            dict or None: {"profile_dir": str, "profile_name": str, "data_dir": str}
        """
        if not os.path.isfile(PROFILE_CONFIG_PATH):
            return None
        try:
            with open(PROFILE_CONFIG_PATH) as f:
                choice = json.load(f)
            # Infer data_dir as parent of the saved profile_dir
            profile_path = choice.get("profile_dir", "")
            if os.path.isdir(profile_path):
                choice["data_dir"] = os.path.dirname(profile_path)
            return choice
        except Exception:
            return None

    @staticmethod
    def get_active_profile_config():
        """Return the active profile config, or None if using a fresh profile.

        The config dict contains:
            data_dir  – the --user-data-dir value
            prof_dir  – the --profile-directory value
            name      – human-readable name
        """
        choice = DriverManager.load_profile_choice()
        if not choice:
            return None

        data_dir = choice.get("data_dir") or DriverManager.get_data_dir()
        prof_dir_name = choice.get("profile_dir")

        # If choice stores the full path, extract just the directory name
        if prof_dir_name and os.path.isabs(prof_dir_name) and data_dir:
            prof_dir_name = os.path.basename(prof_dir_name)

        if not data_dir or not prof_dir_name:
            return None

        return {
            "data_dir": data_dir,
            "prof_dir": prof_dir_name,
            "name": choice.get("profile_name", prof_dir_name),
        }

    # ------------------------------------------------------------------
    # Common Chrome options
    # ------------------------------------------------------------------

    @staticmethod
    def _build_options(profile_dir, browser_binary):
        """Build ChromeOptions with anti-detection measures."""
        options = Options()

        if browser_binary:
            options.binary_location = browser_binary

        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-debugging-port=0")
        options.add_argument("--memory-pressure-off")

        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/148.0.7778.96 Safari/537.36"
        )
        options.add_argument(f"--user-agent={user_agent}")

        norm = os.path.normpath(profile_dir)
        basename = os.path.basename(norm)
        parent = os.path.dirname(norm)
        if basename in ("Default", "System Profile") or re.match(r"^Profile\s+\d+$", basename):
            options.add_argument(f"--user-data-dir={parent}")
            options.add_argument(f"--profile-directory={basename}")
        else:
            options.add_argument(f"--user-data-dir={profile_dir}")

        return options, user_agent

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def setup_chrome_driver(profile_dir=None):
        """Set up Chrome/Chromium with anti-detection and profile support.

        Args:
            profile_dir: If set, use this as the --user-data-dir.
                         If None, checks saved profile choice; falls back to a
                         fresh profile in .auth/chrome_profile.

        Returns:
            tuple: (driver, profile_path)
        """
        browser_binary = DriverManager._find_browser_binary()

        if profile_dir:
            # Explicit profile_dir → use it directly
            os.makedirs(profile_dir, exist_ok=True)
            options, user_agent = DriverManager._build_options(profile_dir, browser_binary)

        else:
            active = DriverManager.get_active_profile_config()
            if active:
                # Use existing browser profile
                data_dir = active["data_dir"]
                prof_dir_name = active["prof_dir"]
                logger.info("Using saved profile: %s (%s)", active["name"], prof_dir_name)
                options, user_agent = DriverManager._build_options(data_dir, browser_binary)
                options.add_argument(f"--profile-directory={prof_dir_name}")
                profile_dir = os.path.join(data_dir, prof_dir_name)
            else:
                # Fresh disposable profile
                profile_dir = DEFAULT_FRESH_PROFILE
                os.makedirs(profile_dir, exist_ok=True)
                options, user_agent = DriverManager._build_options(profile_dir, browser_binary)

        # Get ChromeDriver
        driver_path = DriverManager._get_chromedriver_path()

        # — retry loop for transient Chrome startup crashes —
        MAX_START_ATTEMPTS = 2
        driver = None
        for attempt in range(1, MAX_START_ATTEMPTS + 1):
            try:
                logger.info("Starting browser with profile: %s (attempt %d/%d)",
                            profile_dir, attempt, MAX_START_ATTEMPTS)
                if driver_path:
                    service = Service(executable_path=driver_path)
                    driver = webdriver.Chrome(service=service, options=options)
                else:
                    driver = webdriver.Chrome(options=options)
                break  # success
            except Exception as exc:
                logger.warning("Browser start attempt %d/%d failed: %s",
                               attempt, MAX_START_ATTEMPTS, exc)
                if attempt < MAX_START_ATTEMPTS:
                    logger.info("Waiting 2s before retry...")
                    time.sleep(2)
                else:
                    raise  # re-raise on last attempt

        driver.execute_cdp_cmd(
            "Network.setUserAgentOverride", {"userAgent": user_agent}
        )

        driver.set_page_load_timeout(30)

        logger.info("Chrome driver setup complete")
        return driver, profile_dir

    @staticmethod
    def cleanup_driver(driver, profile_dir=None):
        """Close the browser. Profile is persistent — kept for future sessions."""
        if driver:
            try:
                logger.info("Closing browser...")
                time.sleep(2)
                driver.quit()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.warning("Error closing browser: %s", e)
