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
# EMAIL SETTINGS
# =============================================================================
class EmailConfig:
    """Configuration for email testing and sending"""
    
    # SMTP Defaults
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    
    # Verification
    VERIFICATION_METHOD = os.getenv("EMAIL_VERIFICATION_METHOD", "smtp")
    VERIFICATION_DELAY = float(os.getenv("EMAIL_VERIFICATION_DELAY", "1.0"))
    
    # Sending Limits
    MAX_PER_DAY = int(os.getenv("EMAIL_MAX_PER_DAY", "50"))
    MIN_DELAY = float(os.getenv("EMAIL_MIN_DELAY", "60"))
    MAX_DELAY = float(os.getenv("EMAIL_MAX_DELAY", "120"))
    
    # Default Templates
    DEFAULT_SUBJECT = os.getenv("DEFAULT_EMAIL_SUBJECT", "Hello {first_name}")
    DEFAULT_BODY_TEXT = os.getenv(
        "DEFAULT_EMAIL_BODY_TEXT",
        "Hi {first_name},\n\nI came across your profile and wanted to connect.\n\nBest regards"
    )
    DEFAULT_BODY_HTML = os.getenv("DEFAULT_EMAIL_BODY_HTML", "")


# =============================================================================
# GROQ AI SETTINGS
# =============================================================================
class GroqConfig:
    """Configuration for Groq AI API (CV generation, etc.)"""

    API_KEY = os.getenv("GROQ_API_KEY", "")
    MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # Generation settings
    MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "4000"))
    TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.7"))
    MAX_RETRIES = int(os.getenv("GROQ_MAX_RETRIES", "3"))

    # Rate limiting
    REQUEST_DELAY = 60  # Seconds between requests (free tier: 30 RPM)

    # Model fallback chain (if primary fails 3 times)
    FALLBACK_MODELS = [
        "llama-3.3-70b-versatile",
        "openai/gpt-oss-120b",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "qwen/qwen3-32b",
    ]

    # LaTeX
    BASE_CV_PATH = os.getenv("BASE_CV_PATH", "templates/base_cv.tex")
    LATEX_COMPILER = os.getenv("LATEX_COMPILER", "pdflatex")


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


# =============================================================================
# MODULE-LEVEL CONVENIENCE EXPORTS
# =============================================================================
GROUP_URL = os.getenv("GROUP_URL", "")
GROUP_ID = int(os.getenv("GROUP_ID", "1912468"))
MESSAGE = os.getenv("DEFAULT_MESSAGE", "Hi! I'd like to connect.")
