"""
Profiles API Routes - unified view of all scraped/enriched profiles.
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from api.dependencies import create_job, update_job
from api.middleware.auth import verify_api_key
from auth.auth_manager import AuthManager
from config import LINKEDIN_EMAIL, LINKEDIN_PASSWORD
from core.database import (
    get_unified_profiles, get_profile_by_id, delete_profile_by_id,
)
from core.driver_manager import DriverManager
from core.services import ProfileEnricherService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profiles", tags=["Profiles"])


@router.get("", dependencies=[Depends(verify_api_key)])
async def list_profiles(
    limit: int = 50,
    offset: int = 0,
    search: str = "",
    status: str = "",
):
    """Paginated unified profile list with enrichment + connection status."""
    return get_unified_profiles(
        limit=limit, offset=offset, search=search, status_filter=status
    )


@router.get("/{profile_id}", dependencies=[Depends(verify_api_key)])
async def get_profile(profile_id: int):
    """Get a single profile by ID (full detail)."""
    profile = get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


class EnrichRequest(BaseModel):
    profile_ids: Optional[List[int]] = None
    max_profiles: Optional[int] = None


@router.post("/enrich", dependencies=[Depends(verify_api_key)])
async def enrich_profiles(request: EnrichRequest, background_tasks: BackgroundTasks):
    """Start a background enrichment job for unenriched profiles."""
    job_id = create_job("enrich_profiles")

    max_p = request.max_profiles

    def task():
        driver = None
        temp_profile = None
        try:
            update_job(job_id, status="running", progress=10)
            driver, temp_profile = DriverManager.setup_chrome_driver()
            auth = AuthManager(email=LINKEDIN_EMAIL, password=LINKEDIN_PASSWORD)
            if not auth.login(driver):
                raise Exception("Authentication failed")
            update_job(job_id, status="running", progress=30)
            result = ProfileEnricherService.enrich_profiles_from_db(
                driver, max_profiles=max_p
            )
            update_job(job_id, status="completed", progress=100, result=result)
            logger.info("Enrichment job %s completed: %s", job_id, result)
        except Exception as e:
            update_job(job_id, status="failed", error=str(e))
            logger.error("Enrichment job %s failed: %s", job_id, e, exc_info=True)
        finally:
            if driver:
                DriverManager.cleanup_driver(driver, temp_profile)

    background_tasks.add_task(task)
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Enrichment job started",
    }


@router.delete("/{profile_id}", dependencies=[Depends(verify_api_key)])
async def delete_profile(profile_id: int):
    """Delete a profile (and its enriched data) from the database."""
    ok = delete_profile_by_id(profile_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"success": True, "message": "Profile deleted"}
