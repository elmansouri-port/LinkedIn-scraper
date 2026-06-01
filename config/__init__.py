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

    # Convenience exports
    GROUP_URL,
    GROUP_ID,
    MESSAGE,

    # Config classes
    BrowserConfig,
    GoogleScraperConfig,
    GroupScraperConfig,
    ProfileEnricherConfig,
    ConnectionConfig,
    MessagingConfig,
    GroqConfig,
    LoggingConfig,
)

__all__ = [
    # Directories
    'BASE_DIR', 'DATA_DIR', 'DB_DIR', 'CSV_DIR', 'LOGS_DIR', 'AUTH_DIR',
    # Auth
    'LINKEDIN_EMAIL', 'LINKEDIN_PASSWORD', 'COOKIES_PATH',
    # Convenience
    'GROUP_URL', 'GROUP_ID', 'MESSAGE',
    # Configs
    'BrowserConfig', 'GoogleScraperConfig', 'GroupScraperConfig',
    'ProfileEnricherConfig', 'ConnectionConfig', 'MessagingConfig',
    'GroqConfig', 'LoggingConfig',
]
