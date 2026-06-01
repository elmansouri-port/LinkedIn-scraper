"""
API Dependencies - Shared dependencies for API routes.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List

from core.driver_manager import DriverManager
from auth.auth_manager import AuthManager
from config import LINKEDIN_EMAIL, LINKEDIN_PASSWORD

logger = logging.getLogger(__name__)

# In-memory job storage (for simplicity - use Redis/DB in production)
jobs_store: Dict[str, Dict] = {}


def create_job(job_type: str) -> str:
    """Create a new job and return job ID."""
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    jobs_store[job_id] = {
        "id": job_id,
        "type": job_type,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "progress": 0,
        "result": None,
        "error": None,
        "logs": [],
    }
    logger.info("Job created | id=%s type=%s", job_id, job_type)
    return job_id


def update_job(job_id: str, **kwargs):
    """Update job status and data."""
    if job_id in jobs_store:
        jobs_store[job_id].update(kwargs)
        logger.debug("Job updated | id=%s status=%s", job_id, kwargs.get("status", "unchanged"))
    else:
        logger.warning("Attempted to update non-existent job | id=%s", job_id)


def get_job(job_id: str) -> Dict:
    """Get job information."""
    return jobs_store.get(job_id)


MAX_JOB_LOGS = 40

def append_job_log(job_id: str, level: str, message: str):
    """Append a log line to the job's live log buffer (capped at MAX_JOB_LOGS)."""
    job = jobs_store.get(job_id)
    if not job:
        return
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    job["logs"].append({"ts": ts, "level": level, "msg": message})
    if len(job["logs"]) > MAX_JOB_LOGS:
        job["logs"] = job["logs"][-MAX_JOB_LOGS:]


def get_authenticated_driver():
    """Get an authenticated LinkedIn driver.

    Returns:
        tuple: (driver, temp_profile)

    Raises:
        Exception: If driver setup or login fails
    """
    driver = None
    temp_profile = None

    try:
        logger.info("Setting up Chrome driver for API job")
        driver, temp_profile = DriverManager.setup_chrome_driver()

        auth_manager = AuthManager(email=LINKEDIN_EMAIL, password=LINKEDIN_PASSWORD)

        if auth_manager.login(driver):
            logger.info("API job authenticated successfully")
            return driver, temp_profile
        else:
            logger.error("API job authentication failed")
            if driver:
                DriverManager.cleanup_driver(driver, temp_profile)
            raise Exception("Authentication failed")

    except Exception as e:
        if driver:
            DriverManager.cleanup_driver(driver, temp_profile)
        logger.error("Failed to get authenticated driver: %s", e)
        raise Exception(f"Failed to get authenticated driver: {str(e)}")
