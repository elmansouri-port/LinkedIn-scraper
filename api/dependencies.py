"""
API Dependencies - Shared dependencies for API routes
"""
from typing import Dict
import uuid
from datetime import datetime
from core.driver_manager import DriverManager
from auth.login_with_cookies import login_with_cookies
from auth.login_with_credentials import login_with_credentials
from utils.cookie_handler import save_cookies


# In-memory job storage (for simplicity - use Redis/DB in production)
jobs_store: Dict[str, Dict] = {}


def create_job(job_type: str) -> str:
    """Create a new job and return job ID
    
    Args:
        job_type: Type of job (scrape, connection, message)
        
    Returns:
        str: Unique job ID
    """
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    jobs_store[job_id] = {
        "id": job_id,
        "type": job_type,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "progress": 0,
        "result": None,
        "error": None
    }
    return job_id


def update_job(job_id: str, **kwargs):
    """Update job status and data
    
    Args:
        job_id: Job identifier
        **kwargs: Fields to update (status, progress, result, error)
    """
    if job_id in jobs_store:
        jobs_store[job_id].update(kwargs)


def get_job(job_id: str) -> Dict:
    """Get job information
    
    Args:
        job_id: Job identifier
        
    Returns:
        dict: Job information or None if not found
    """
    return jobs_store.get(job_id)


async def get_authenticated_driver():
    """Get an authenticated LinkedIn driver
    
    This is a dependency that can be injected into route handlers.
    
    Returns:
        tuple: (driver, temp_profile)
        
    Raises:
        Exception: If driver setup or login fails
    """
    from auth.auth_manager import AuthManager
    from config import settings
    
    driver = None
    temp_profile = None
    
    try:
        # Setup driver
        driver, temp_profile = DriverManager.setup_chrome_driver()
        
        # Use AuthManager for login
        auth_manager = AuthManager(
            email=settings.LINKEDIN_EMAIL,
            password=settings.LINKEDIN_PASSWORD
        )
        
        if auth_manager.login(driver):
            return driver, temp_profile
        else:
            if driver:
                DriverManager.cleanup_driver(driver, temp_profile)
            raise Exception("Authentication failed")
        
    except Exception as e:
        if driver:
            DriverManager.cleanup_driver(driver, temp_profile)
        raise Exception(f"Failed to get authenticated driver: {str(e)}")
