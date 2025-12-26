# Updated LinkedIn Scraper Settings
import os
from pathlib import Path

# Authentication - Now uses environment variables or .env file
# For backward compatibility, we keep these but recommend using .env
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "ddifjdnfkdj23@gmail.com")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "-'wincGB$LWB2r<")

# Paths
AUTH_DIR = Path(".auth")
COOKIES_PATH = str(AUTH_DIR / "cookies.pkl")  # New organized path

# LinkedIn URLs
GROUP_URL = "https://www.linkedin.com/groups/1912468/members/"
GROUP_ID = 1912468

# Messaging
MESSAGE = "hi"

# Scraping settings
MAX_MEMBERS = None  # Set to None for unlimited, or specify a number like 100
BATCH_SIZE = 10  # Number of members to save per batch
SCROLL_TIMEOUT = 10  # Seconds to wait for new content to load
MAX_SCROLL_ATTEMPTS = 3  # Maximum attempts to scroll without finding new content

# File settings
DATA_DIRECTORY = "data"  # Directory to save CSV files
LOG_FILENAME = "scraper.log"

# Browser settings
HEADLESS_MODE = False  # Set to True to run browser in background
WAIT_TIMEOUT = 15  # Default wait timeout for elements