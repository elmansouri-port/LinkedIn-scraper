"""
Scraper API Routes
"""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from api.models.requests import GroupScrapeRequest, SearchScrapeRequest, GoogleScrapeRequest
from api.models.responses import JobResponse, StatusResponse, ScrapeResultResponse
from api.middleware.auth import verify_api_key
from api.dependencies import create_job, update_job, get_job, get_authenticated_driver
from core.services.scraper_service import ScraperService
from core.driver_manager import DriverManager
from datetime import datetime
import asyncio


router = APIRouter(prefix="/scrape", tags=["Scraping"])


def run_scrape_group_task(job_id: str, request: GroupScrapeRequest):
    """Background task for group scraping"""
    driver = None
    temp_profile = None
    
    try:
        update_job(job_id, status="running", progress=10)
        
        # Get authenticated driver
        driver, temp_profile = DriverManager.setup_chrome_driver()
        from auth.auth_manager import AuthManager
        from config import settings
        
        auth_manager = AuthManager(settings.LINKEDIN_EMAIL, settings.LINKEDIN_PASSWORD)
        if not auth_manager.login(driver):
            raise Exception("Authentication failed")
        
        update_job(job_id, status="running", progress=30)
        
        # Run scraping
        result = ScraperService.scrape_group_members(
            driver, 
            request.group_url, 
            request.max_members,
            request.scraping_mode
        )
        
        update_job(job_id, status="completed", progress=100, result=result)
        
    except Exception as e:
        update_job(job_id, status="failed", error=str(e))
    finally:
        if driver:
            DriverManager.cleanup_driver(driver, temp_profile)


def run_search_scrape_task(job_id: str, request: SearchScrapeRequest):
    """Background task for search scraping"""
    driver = None
    temp_profile = None
    
    try:
        update_job(job_id, status="running", progress=10)
        
        # Get authenticated driver
        driver, temp_profile = DriverManager.setup_chrome_driver()
        from auth.auth_manager import AuthManager
        from config import settings
        
        auth_manager = AuthManager(settings.LINKEDIN_EMAIL, settings.LINKEDIN_PASSWORD)
        if not auth_manager.login(driver):
            raise Exception("Authentication failed")
        
        update_job(job_id, status="running", progress=30)
        
        # Run scraping
        result = ScraperService.search_and_scrape_profiles(
            driver,
            request.keywords,
            request.max_profiles,
            request.start_page
        )
        
        update_job(job_id, status="completed", progress=100, result=result)
        
    except Exception as e:
        update_job(job_id, status="failed", error=str(e))
    finally:
        if driver:
            DriverManager.cleanup_driver(driver, temp_profile)


def run_google_scrape_task(job_id: str, request: GoogleScrapeRequest):
    """Background task for Google-based scraping"""
    driver = None
    temp_profile = None
    
    try:
        update_job(job_id, status="running", progress=10)
        
        # Get authenticated driver
        driver, temp_profile = DriverManager.setup_chrome_driver()
        from auth.auth_manager import AuthManager
        from config import settings
        
        auth_manager = AuthManager(settings.LINKEDIN_EMAIL, settings.LINKEDIN_PASSWORD)
        if not auth_manager.login(driver):
            raise Exception("Authentication failed")
        
        update_job(job_id, status="running", progress=30)
        
        # Run scraping
        result = ScraperService.scrape_google_linkedin_profiles(
            driver,
            request.keywords,
            request.oblig_keywords,
            request.max_profiles,
            request.max_profiles_per_keyword
        )
        
        update_job(job_id, status="completed", progress=100, result=result)
        
    except Exception as e:
        update_job(job_id, status="failed", error=str(e))
    finally:
        if driver:
            DriverManager.cleanup_driver(driver, temp_profile)


@router.post("/group", response_model=JobResponse, dependencies=[Depends(verify_api_key)])
async def scrape_group(request: GroupScrapeRequest, background_tasks: BackgroundTasks):
    """
    Scrape LinkedIn group members
    
    This endpoint initiates a background job to scrape members from a LinkedIn group.
    Returns a job ID that can be used to check the status of the scraping operation.
    """
    job_id = create_job("scrape_group")
    
    # Add background task
    background_tasks.add_task(run_scrape_group_task, job_id, request)
    
    return JobResponse(
        job_id=job_id,
        status="pending",
        message="Group scraping job created successfully",
        created_at=datetime.utcnow().isoformat()
    )


@router.post("/search", response_model=JobResponse, dependencies=[Depends(verify_api_key)])
async def scrape_search(request: SearchScrapeRequest, background_tasks: BackgroundTasks):
    """
    Search and scrape LinkedIn profiles
    
    This endpoint initiates a background job to search and scrape profiles based on keywords.
    Returns a job ID that can be used to check the status of the scraping operation.
    """
    job_id = create_job("scrape_search")
    
    # Add background task
    background_tasks.add_task(run_search_scrape_task, job_id, request)
    
    return JobResponse(
        job_id=job_id,
        status="pending",
        message="Search scraping job created successfully",
        created_at=datetime.utcnow().isoformat()
    )


@router.post("/google", response_model=JobResponse, dependencies=[Depends(verify_api_key)])
async def scrape_google(request: GoogleScrapeRequest, background_tasks: BackgroundTasks):
    """
    Scrape LinkedIn profiles using Google search
    
    This endpoint initiates a background job to scrape profiles using Google search.
    Returns a job ID that can be used to check the status of the scraping operation.
    """
    job_id = create_job("scrape_google")
    
    # Add background task
    background_tasks.add_task(run_google_scrape_task, job_id, request)
    
    return JobResponse(
        job_id=job_id,
        status="pending",
        message="Google scraping job created successfully",
        created_at=datetime.utcnow().isoformat()
    )


@router.get("/status/{job_id}", response_model=StatusResponse, dependencies=[Depends(verify_api_key)])
async def get_scrape_status(job_id: str):
    """
    Get the status of a scraping job
    
    Returns the current status, progress, and results (if completed) of a scraping job.
    """
    job = get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return StatusResponse(
        job_id=job["id"],
        status=job["status"],
        progress=job.get("progress"),
        message=f"Job is {job['status']}",
        result=job.get("result"),
        error=job.get("error")
    )
