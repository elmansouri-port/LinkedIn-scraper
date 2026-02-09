"""
Scraper Configuration - Centralized settings for all scrapers.
All configurable parameters in one place for easy management.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# =============================================================================
# PATHS & DIRECTORIES
# =============================================================================
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DB_DIR = DATA_DIR / "db"
CSV_DIR = DATA_DIR / "csv"
LOGS_DIR = DATA_DIR / "logs"
AUTH_DIR = BASE_DIR / ".auth"

# Create directories if they don't exist
for dir_path in [DATA_DIR, DB_DIR, CSV_DIR, LOGS_DIR, AUTH_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


# =============================================================================
# AUTHENTICATION
# =============================================================================
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")
COOKIES_PATH = str(AUTH_DIR / "cookies.pkl")


# =============================================================================
# BROWSER SETTINGS
# =============================================================================
class BrowserConfig:
    """Chrome/Selenium browser configuration"""
    HEADLESS_MODE = os.getenv("HEADLESS_MODE", "false").lower() == "true"
    PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "30"))
    ELEMENT_WAIT_TIMEOUT = int(os.getenv("ELEMENT_WAIT_TIMEOUT", "10"))
    
    # Chrome driver paths to search
    DRIVER_PATHS = [
        "./chromedriver.exe",
        "C:/chromedriver/chromedriver.exe",
        "C:/WebDrivers/chromedriver.exe",
        "./drivers/chromedriver.exe",
    ]
    
    # User agent
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


# =============================================================================
# GOOGLE LINKEDIN SCRAPER SETTINGS
# =============================================================================
class GoogleScraperConfig:
    """Configuration for Google LinkedIn profile scraper"""
    
    # Performance settings
    PAGE_LOAD_TIMEOUT = int(os.getenv("GOOGLE_PAGE_TIMEOUT", "5"))
    ELEMENT_WAIT_TIMEOUT = int(os.getenv("GOOGLE_ELEMENT_TIMEOUT", "3"))
    MIN_DELAY = float(os.getenv("GOOGLE_MIN_DELAY", "0.3"))
    MAX_DELAY = float(os.getenv("GOOGLE_MAX_DELAY", "1.0"))
    PAGE_DELAY = float(os.getenv("GOOGLE_PAGE_DELAY", "0.5"))
    
    # Scraping limits
    DEFAULT_MAX_PAGES_PER_KEYWORD = int(os.getenv("GOOGLE_MAX_PAGES", "10"))
    DEFAULT_MAX_PROFILES = int(os.getenv("GOOGLE_MAX_PROFILES", "100"))
    DEFAULT_PROFILES_PER_KEYWORD = int(os.getenv("GOOGLE_PROFILES_PER_KEYWORD", "20"))
    RESULTS_PER_PAGE = int(os.getenv("GOOGLE_RESULTS_PER_PAGE", "20"))
    
    # Duplicate detection (ratio-based)
    DUPLICATE_RATIO_THRESHOLD = float(os.getenv("DUPLICATE_RATIO_THRESHOLD", "0.7"))
    CONSECUTIVE_BAD_PAGES = int(os.getenv("CONSECUTIVE_BAD_PAGES", "2"))
    
    # Logging
    VERBOSE = os.getenv("GOOGLE_VERBOSE", "true").lower() == "true"
    
    # Search settings
    LINKEDIN_DOMAIN = os.getenv("LINKEDIN_DOMAIN", "linkedin.com")  # or "fr.linkedin.com"


# =============================================================================
# GROUP SCRAPER SETTINGS
# =============================================================================
class GroupScraperConfig:
    """Configuration for LinkedIn group member scraper"""
    
    DEFAULT_GROUP_URL = os.getenv("GROUP_URL", "")
    MAX_MEMBERS = int(os.getenv("MAX_MEMBERS", "0")) or None  # 0 = unlimited
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))
    SCROLL_TIMEOUT = int(os.getenv("SCROLL_TIMEOUT", "10"))
    MAX_SCROLL_ATTEMPTS = int(os.getenv("MAX_SCROLL_ATTEMPTS", "3"))


# =============================================================================
# PROFILE ENRICHER SETTINGS
# =============================================================================
class ProfileEnricherConfig:
    """Configuration for profile enrichment (email finding)"""
    
    # Delay between profile visits
    PROFILE_DELAY = float(os.getenv("ENRICHER_PROFILE_DELAY", "2.0"))
    
    # Google search for company domain
    DOMAIN_SEARCH_TIMEOUT = int(os.getenv("DOMAIN_SEARCH_TIMEOUT", "5"))
    
    # Email formats to generate
    EMAIL_FORMATS = [
        "{first}.{last}@{domain}",
        "{first}@{domain}",
        "{first}{last}@{domain}",
        "{f}{last}@{domain}",
    ]


# =============================================================================
# CONNECTION SENDER SETTINGS
# =============================================================================
class ConnectionConfig:
    """Configuration for connection request sender"""
    
    # Delays to avoid detection
    MIN_DELAY_BETWEEN_REQUESTS = float(os.getenv("CONN_MIN_DELAY", "10"))
    MAX_DELAY_BETWEEN_REQUESTS = float(os.getenv("CONN_MAX_DELAY", "30"))
    
    # Limits
    MAX_CONNECTIONS_PER_DAY = int(os.getenv("MAX_CONNECTIONS_PER_DAY", "50"))
    MAX_CONNECTIONS_PER_SESSION = int(os.getenv("MAX_CONNECTIONS_PER_SESSION", "25"))


# =============================================================================
# MESSAGING SETTINGS
# =============================================================================
class MessagingConfig:
    """Configuration for messaging campaigns"""
    
    DEFAULT_MESSAGE = os.getenv("DEFAULT_MESSAGE", "Hi! I'd like to connect.")
    
    # Delays
    MIN_DELAY_BETWEEN_MESSAGES = float(os.getenv("MSG_MIN_DELAY", "30"))
    MAX_DELAY_BETWEEN_MESSAGES = float(os.getenv("MSG_MAX_DELAY", "60"))
    
    # Limits
    MAX_MESSAGES_PER_DAY = int(os.getenv("MAX_MESSAGES_PER_DAY", "50"))


# =============================================================================
# API SETTINGS
# =============================================================================
class APIConfig:
    """Configuration for REST API (if used)"""
    
    API_KEY = os.getenv("API_KEY", "")
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    API_DEBUG = os.getenv("API_DEBUG", "false").lower() == "true"
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))


# =============================================================================
# LOGGING SETTINGS
# =============================================================================
class LoggingConfig:
    """Configuration for logging"""
    
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    # File logging
    ENABLE_FILE_LOGGING = os.getenv("ENABLE_FILE_LOGGING", "true").lower() == "true"
    LOG_ROTATION_SIZE = int(os.getenv("LOG_ROTATION_SIZE", "10485760"))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    
    # Console output
    ENABLE_CONSOLE_LOGGING = os.getenv("ENABLE_CONSOLE_LOGGING", "true").lower() == "true"
