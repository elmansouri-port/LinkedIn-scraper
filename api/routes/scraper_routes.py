"""
Scraper API Routes.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from api.dependencies import create_job, get_job, update_job
from api.middleware.auth import verify_api_key
from api.models.requests import GoogleScrapeRequest, GroupScrapeRequest, SearchScrapeRequest
from api.models.responses import JobResponse, StatusResponse
from auth.auth_manager import AuthManager
from config import LINKEDIN_EMAIL, LINKEDIN_PASSWORD
from core.driver_manager import DriverManager
from core.services.scraper_service import ScraperService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scrape", tags=["Scraping"])


def _run_with_driver(job_id: str, task_fn):
    """Common driver setup / teardown wrapper for background tasks."""
    driver = None
    temp_profile = None
    try:
        logger.info("Job %s: setting up driver", job_id)
        update_job(job_id, status="running", progress=10)
        driver, temp_profile = DriverManager.setup_chrome_driver()

        auth_manager = AuthManager(email=LINKEDIN_EMAIL, password=LINKEDIN_PASSWORD)
        if not auth_manager.login(driver):
            raise Exception("Authentication failed")

        update_job(job_id, status="running", progress=30)
        task_fn(driver, job_id)
        update_job(job_id, status="completed", progress=100)
        logger.info("Job %s completed", job_id)
    except Exception as e:
        update_job(job_id, status="failed", error=str(e))
        logger.error("Job %s failed: %s", job_id, e, exc_info=True)
    finally:
        if driver:
            DriverManager.cleanup_driver(driver, temp_profile)


def run_scrape_group_task(job_id: str, request: GroupScrapeRequest):
    """Background task for group scraping."""
    def task(driver, jid):
        result = ScraperService.scrape_group_members(
            driver, request.group_url, request.max_members, request.scraping_mode
        )
        update_job(jid, result=result)

    _run_with_driver(job_id, task)


def run_search_scrape_task(job_id: str, request: SearchScrapeRequest):
    """Background task for search scraping."""
    def task(driver, jid):
        result = ScraperService.search_and_scrape_profiles(
            driver, request.keywords, request.max_profiles, request.start_page
        )
        update_job(jid, result=result)

    _run_with_driver(job_id, task)


def run_google_scrape_task(job_id: str, request: GoogleScrapeRequest):
    """Background task for Google-based scraping."""
    def task(driver, jid):
        result = ScraperService.scrape_google_linkedin_profiles(
            driver,
            request.keywords,
            request.oblig_keywords,
            request.max_profiles,
            request.max_profiles_per_keyword,
        )
        update_job(jid, result=result)

    _run_with_driver(job_id, task)


@router.post("/group", response_model=JobResponse, dependencies=[Depends(verify_api_key)])
async def scrape_group(request: GroupScrapeRequest, background_tasks: BackgroundTasks):
    """Scrape LinkedIn group members."""
    job_id = create_job("scrape_group")
    background_tasks.add_task(run_scrape_group_task, job_id, request)
    return JobResponse(
        job_id=job_id,
        status="pending",
        message="Group scraping job created successfully",
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/search", response_model=JobResponse, dependencies=[Depends(verify_api_key)])
async def scrape_search(request: SearchScrapeRequest, background_tasks: BackgroundTasks):
    """Search and scrape LinkedIn profiles."""
    job_id = create_job("scrape_search")
    background_tasks.add_task(run_search_scrape_task, job_id, request)
    return JobResponse(
        job_id=job_id,
        status="pending",
        message="Search scraping job created successfully",
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/google", response_model=JobResponse, dependencies=[Depends(verify_api_key)])
async def scrape_google(request: GoogleScrapeRequest, background_tasks: BackgroundTasks):
    """Scrape LinkedIn profiles using Google search."""
    job_id = create_job("scrape_google")
    background_tasks.add_task(run_google_scrape_task, job_id, request)
    return JobResponse(
        job_id=job_id,
        status="pending",
        message="Google scraping job created successfully",
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/status/{job_id}", response_model=StatusResponse, dependencies=[Depends(verify_api_key)])
async def get_scrape_status(job_id: str):
    """Get the status of a scraping job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return StatusResponse(
        job_id=job["id"],
        status=job["status"],
        progress=job.get("progress"),
        message=f"Job is {job['status']}",
        result=job.get("result"),
        error=job.get("error"),
    )
