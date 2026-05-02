"""
API Configuration Settings
"""
import os
from typing import List


class APIConfig:
    """API Configuration"""
    
    # API Server Settings
    HOST: str = os.getenv("API_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("API_PORT", "8000"))
    DEBUG: bool = os.getenv("API_DEBUG", "True").lower() == "true"
    
    # API Information
    TITLE: str = "LinkedIn Scraper API"
    DESCRIPTION: str = """
    LinkedIn Scraper API provides programmatic access to LinkedIn scraping operations.
    
    Features:
    * Scrape LinkedIn group members
    * Search and scrape profiles
    * Google-based profile scraping
    * Send connection requests
    * Send messages to group members
    """
    VERSION: str = "1.0.0"
    
    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://localhost:8080",
    ]
    
    # Security
    API_KEY_NAME: str = "X-API-Key"
    API_KEYS: List[str] = [
        os.getenv("API_KEY", ""),
    ]
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_PER_HOUR: int = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
    
    # Background Jobs
    MAX_CONCURRENT_JOBS: int = int(os.getenv("MAX_CONCURRENT_JOBS", "3"))
    JOB_TIMEOUT_SECONDS: int = int(os.getenv("JOB_TIMEOUT_SECONDS", "3600"))
    
    # File Upload
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
