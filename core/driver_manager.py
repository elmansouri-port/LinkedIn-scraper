"""
Chrome Driver Manager - Centralized driver setup and management.
Auto-detects Chromium snap or Google Chrome, uses matching ChromeDriver.
Supports selecting and reusing existing browser profiles to avoid re-auth.
Cross-platform: Windows, macOS, Linux.
"""
import json
import logging
import re
import sys
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

# Chrome profile must be in an ASCII-only path — Chrome crashes if --user-data-dir
# contains non-ASCII characters (e.g. accented letters on Windows).
DEFAULT_FRESH_PROFILE = os.path.join(os.path.expanduser("~"), ".linkedin_scraper", "chrome_profile")

# Profile choice persistence (stays in project .auth — Python handles Unicode paths fine)
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
        """Detect the installed Chromium/Chrome browser binary (Windows/macOS/Linux)."""
        # Linux snap
        if os.path.exists(SNAP_CHROMIUM_BINARY):
            return SNAP_CHROMIUM_BINARY

        # macOS app bundles
        if sys.platform == "darwin":
            for mac_path in [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
                os.path.expanduser(
                    "~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                ),
            ]:
                if os.path.isfile(mac_path):
                    return mac_path

        # Windows — common install locations
        if os.name == "nt":
            local_app    = os.environ.get("LOCALAPPDATA", "")
            prog_files   = os.environ.get("PROGRAMFILES", "")
            prog_files86 = os.environ.get("PROGRAMFILES(X86)", "")
            for win_path in [
                os.path.join(local_app,    "Google",    "Chrome",        "Application", "chrome.exe"),
                os.path.join(prog_files,   "Google",    "Chrome",        "Application", "chrome.exe"),
                os.path.join(prog_files86, "Google",    "Chrome",        "Application", "chrome.exe"),
                os.path.join(local_app,    "Chromium",  "Application",   "chrome.exe"),
                os.path.join(local_app,    "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                os.path.join(prog_files,   "Microsoft", "Edge", "Application", "msedge.exe"),
            ]:
                if win_path and os.path.isfile(win_path):
                    return win_path

        # Cross-platform: anything on PATH
        for name in [
            "google-chrome-stable", "google-chrome",
            "chromium-browser", "chromium",
            "brave-browser",
        ]:
            path = shutil.which(name)
            if path:
                return path

        return None

    @staticmethod
    def _get_chromedriver_path():
        """Get the correct ChromeDriver path — webdriver-manager first (version-matched),
        then fall back to any system chromedriver on PATH."""
        try:
            from webdriver_manager.chrome import ChromeDriverManager

            original_context = ssl.create_default_context
            ssl._create_default_https_context = ssl._create_unverified_context

            driver_path = ChromeDriverManager().install()

            ssl._create_default_https_context = original_context

            logger.info("ChromeDriver auto-installed: %s", driver_path)
            return driver_path
        except Exception as e:
            logger.warning("webdriver_manager failed: %s — trying system PATH", e)

        system_driver = DriverManager._find_chromedriver_on_system()
        if system_driver:
            return system_driver

        return None

    # ------------------------------------------------------------------
    # Profile detection
    # ------------------------------------------------------------------

    @staticmethod
    def get_data_dir():
        """Return the browser's user-data directory (parent of profiles).

        Checks Chrome, Edge, Brave, and Chromium on Windows / macOS / Linux.

        Returns:
            str or None: Path to the data dir.
        """
        def _first_valid(*candidates):
            for c in candidates:
                if c and os.path.isdir(c) and os.path.isfile(os.path.join(c, "Local State")):
                    return c
            return None

        # ── Windows ──────────────────────────────────────────────────
        if os.name == "nt":
            local_app    = os.environ.get("LOCALAPPDATA", "")
            roaming      = os.environ.get("APPDATA", "")
            return _first_valid(
                os.path.join(local_app, "Google",        "Chrome",        "User Data"),
                os.path.join(local_app, "Microsoft",     "Edge",          "User Data"),
                os.path.join(local_app, "BraveSoftware", "Brave-Browser", "User Data"),
                os.path.join(local_app, "Chromium",      "User Data"),
            )

        # ── macOS ─────────────────────────────────────────────────────
        if sys.platform == "darwin":
            base = os.path.expanduser("~/Library/Application Support")
            return _first_valid(
                os.path.join(base, "Google",        "Chrome"),
                os.path.join(base, "BraveSoftware", "Brave-Browser"),
                os.path.join(base, "Chromium"),
                os.path.join(base, "Microsoft Edge"),
            )

        # ── Linux ─────────────────────────────────────────────────────
        # Chromium snap first (different data-dir structure)
        snap_dir = os.path.expanduser("~/snap/chromium/common/chromium")
        if os.path.isdir(snap_dir) and os.path.isfile(os.path.join(snap_dir, "Local State")):
            return snap_dir

        return _first_valid(
            os.path.expanduser("~/.config/google-chrome"),
            os.path.expanduser("~/.config/chromium"),
            os.path.expanduser("~/.config/BraveSoftware/Brave-Browser"),
            os.path.expanduser("~/.config/brave"),
            os.path.expanduser("~/.config/microsoft-edge"),
        )

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
    def save_profile_choice(profile_dir, profile_name=None, data_dir=None):
        """Persist the chosen profile for future sessions."""
        os.makedirs(AUTH_DIR, exist_ok=True)
        choice = {
            "profile_dir": profile_dir,
            "profile_name": profile_name or profile_dir,
        }
        if data_dir:
            choice["data_dir"] = data_dir
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
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-sync")

        # Prevent Chrome from running background processes after all windows close.
        # Without this, Chrome stays in the system tray and locks the profile
        # directory, preventing Selenium from starting a new instance.
        options.add_argument("--disable-background-mode")
        options.add_argument("--disable-features=BackgroundingApp")

        # Prevent session-restore dialogs that block WebDriver when using
        # an existing Chrome profile.
        options.add_argument("--disable-session-crashed-bubble")
        options.add_argument("--hide-crash-restore-bubble")
        options.add_argument("--disable-features=InfiniteSessionRestore")

        # Avoid port lock issues after crashes (Chrome 117+)
        options.add_argument("--remote-debugging-pipe")
        
        # Wait for DOMContentLoaded (HTML parsed, DOM ready) but not for
        # images/fonts. Faster than "normal" on content-heavy pages like
        # LinkedIn, and more reliable than "none" (which returns before
        # the navigation even starts, causing downstream timeouts).
        options.page_load_strategy = "eager"

        if sys.platform == "darwin":
            user_agent = (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
        elif sys.platform.startswith("linux"):
            user_agent = (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
        else:
            user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
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
    # Chrome process management
    # ------------------------------------------------------------------

    @staticmethod
    def _kill_existing_chrome(profile_dir):
        """Kill any running Chrome processes that lock the user-data-dir."""
        import subprocess

        if os.name != "nt":
            try:
                subprocess.run(["pkill", "-f", "chromedriver"], capture_output=True)
                subprocess.run(["pkill", "-f", "chrome"], capture_output=True)
            except Exception:
                pass
            return

        # Windows: Aggressively taskkill chromedriver AND chrome.exe
        try:
            # Kill chromedriver first to release driver locks
            subprocess.run(
                ["taskkill", "/F", "/IM", "chromedriver.exe", "/T"],
                capture_output=True, timeout=5,
            )
            # Kill all chrome.exe processes (including background/system tray)
            # to guarantee the profile directory lock is completely released.
            subprocess.run(
                ["taskkill", "/F", "/IM", "chrome.exe", "/T"],
                capture_output=True, timeout=5,
            )
        except Exception as e:
            logger.warning("Could not force-kill chromedriver/chrome: %s", e)

    @staticmethod
    def _fix_profile_state(profile_dir):
        """Reset the profile's Preferences to avoid the 'Crashed' state hang.
        
        When Chrome is force-closed, it sets exit_type to Crashed. On the next
        start, Chrome hangs the renderer waiting for the session restore bubble,
        causing Selenium to timeout with DevToolsActivePort or Renderer errors.
        """
        pref_path = os.path.join(profile_dir, "Preferences")
        if not os.path.isfile(pref_path):
            return

        try:
            with open(pref_path, "r", encoding="utf-8") as f:
                prefs = json.load(f)
            
            modified = False
            if "profile" in prefs:
                if prefs["profile"].get("exit_type") != "Normal":
                    prefs["profile"]["exit_type"] = "Normal"
                    modified = True
                if not prefs["profile"].get("exited_cleanly"):
                    prefs["profile"]["exited_cleanly"] = True
                    modified = True
            
            if modified:
                with open(pref_path, "w", encoding="utf-8") as f:
                    json.dump(prefs, f)
                logger.info("Reset Chrome profile exit_state to Normal.")
        except Exception as e:
            logger.warning("Could not fix profile Preferences: %s", e)

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
            # Always use the dedicated scraper profile (bypassing main Chrome profile)
            # This prevents all locking, crashing, and DevToolsActivePort issues.
            profile_dir = DEFAULT_FRESH_PROFILE
            os.makedirs(profile_dir, exist_ok=True)
            options, user_agent = DriverManager._build_options(profile_dir, browser_binary)

        # Get ChromeDriver
        driver_path = DriverManager._get_chromedriver_path()

        # When using an existing Chrome profile, Chrome background processes
        # (system tray, background apps) lock the user-data-dir and cause
        # "Chrome instance exited" or "DevToolsActivePort" errors.  Kill
        # them automatically so Selenium can claim the profile.
        DriverManager._kill_existing_chrome(profile_dir)

        # Clean up stale Chrome lock files that block startup when a
        # previous session crashed or was force-killed.
        data_dir_for_cleanup = os.path.dirname(profile_dir)
        for cleanup_dir in (profile_dir, data_dir_for_cleanup):
            for lock_name in ("SingletonLock", "SingletonSocket", "SingletonCookie", "DevToolsActivePort"):
                lock_file = os.path.join(cleanup_dir, lock_name)
                try:
                    if os.path.exists(lock_file):
                        os.remove(lock_file)
                        logger.info("Removed stale lock file: %s", lock_file)
                except OSError:
                    pass

        # Prevent Chrome renderer hang on startup due to previous crash
        DriverManager._fix_profile_state(profile_dir)

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
                exc_msg = str(exc)
                logger.warning("Browser start attempt %d/%d failed: %s",
                               attempt, MAX_START_ATTEMPTS, exc_msg)
                if attempt < MAX_START_ATTEMPTS:
                    # Allow retry even for DevToolsActivePort — the kill loop +
                    # lock-file cleanup above may need a moment to take effect.
                    if "DevToolsActivePort" in exc_msg or "user data directory is already in use" in exc_msg:
                        logger.warning(
                            "Profile directory was still locked — waiting longer before retry..."
                        )
                        time.sleep(5)
                    else:
                        logger.info("Waiting 2s before retry...")
                        time.sleep(2)
                else:
                    # Last attempt failed — surface a helpful message.
                    if "DevToolsActivePort" in exc_msg or "user data directory is already in use" in exc_msg:
                        raise RuntimeError(
                            "Chrome cannot start because another Chrome instance is using "
                            "the same profile directory. Please close ALL Chrome windows "
                            "(including system tray) and try again. "
                            "Chrome locks its profile directory and only one process can "
                            "use it at a time."
                        ) from exc
                    raise  # re-raise generic error on last attempt

        driver.execute_cdp_cmd(
            "Network.setUserAgentOverride", {"userAgent": user_agent}
        )

        driver.set_page_load_timeout(30)

        logger.info("Chrome driver setup complete")
        return driver, profile_dir

    @staticmethod
    def cleanup_driver(driver, profile_dir=None):
        """Close the browser and kill any lingering background Chrome processes."""
        if driver:
            try:
                logger.info("Closing browser...")
                time.sleep(2)
                driver.quit()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.warning("Error closing browser: %s", e)

        # Kill any remaining Chrome background processes so they don't
        # hold the profile directory lock between sessions.
        if profile_dir:
            DriverManager._kill_existing_chrome(profile_dir)
