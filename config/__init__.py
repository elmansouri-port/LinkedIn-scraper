"""
Configuration package for LinkedIn Scraper.
Provides centralized access to all configuration classes.
"""

from .scraper_config import (
    # Directories
    BASE_DIR,
    DATA_DIR,
    DB_DIR,
    CSV_DIR,
    LOGS_DIR,
    AUTH_DIR,
    
    # Authentication
    LINKEDIN_EMAIL,
    LINKEDIN_PASSWORD,
    COOKIES_PATH,
    
    # Config classes
    BrowserConfig,
    GoogleScraperConfig,
    GroupScraperConfig,
    ProfileEnricherConfig,
    ConnectionConfig,
    MessagingConfig,
    APIConfig,
    LoggingConfig,
)

# For backward compatibility with old imports
from .settings import *

__all__ = [
    # Directories
    'BASE_DIR', 'DATA_DIR', 'DB_DIR', 'CSV_DIR', 'LOGS_DIR', 'AUTH_DIR',
    
    # Auth
    'LINKEDIN_EMAIL', 'LINKEDIN_PASSWORD', 'COOKIES_PATH',
    
    # Configs
    'BrowserConfig', 'GoogleScraperConfig', 'GroupScraperConfig',
    'ProfileEnricherConfig', 'ConnectionConfig', 'MessagingConfig',
    'APIConfig', 'LoggingConfig',
]
