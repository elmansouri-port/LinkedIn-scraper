"""
Unified FastAPI Backend for LinkedIn Scraper
Provides REST API access to ALL CLI actions:
- Scraping (group, search, Google)
- Enrichment + optional CV generation
- Email testing, sending, scheduling
- Email account management
- CV generation
- Statistics & export
"""
import os
import sys
import logging
from datetime import datetime, timezone
from typing import List, Optional
from contextlib import asynccontextmanager

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from config.api_config import APIConfig
from config.scraper_config import LINKEDIN_EMAIL, LINKEDIN_PASSWORD
from api.middleware.auth import verify_api_key
from api.dependencies import create_job, get_job, update_job
from auth.auth_manager import AuthManager
from core.driver_manager import DriverManager
from core.services import ScraperService, ConnectionService, MessagingService, ProfileEnricherService
from core.services.email_sending_service import EmailSendingService
from core.services.email_scheduler import EmailScheduler, run_scheduler
from core.database import (
    get_all_enriched_profiles, get_all_search_profiles, get_stats,
    get_all_email_campaigns, get_email_campaign,
    get_campaign_email_sends, get_email_accounts, add_email_account,
    update_campaign_schedule, get_due_campaigns,
    get_connection, init_db,
)
from utils.logger import init_logging

logger = logging.getLogger(__name__)

# ── Pydantic Models ──────────────────────────────────────

class GoogleScrapeRequest(BaseModel):
    keywords: str
    oblig_keywords: str = ""
    max_profiles: int = 50
    max_profiles_per_keyword: int = 20
    max_pages: int = 10
    verbose: bool = True

class GroupScrapeRequest(BaseModel):
    group_url: str
    max_members: Optional[int] = None
    scraping_mode: str = "normal"

class EnrichRequest(BaseModel):
    csv_file_path: str
    url_column: str = "Profile URL"
    max_profiles: Optional[int] = None
    generate_cv: bool = False

class EmailCampaignRequest(BaseModel):
    name: str
    subject: str
    body_text: str
    body_html: Optional[str] = None
    cv_path: Optional[str] = None
    cover_letter_path: Optional[str] = None

class ScheduleCampaignRequest(BaseModel):
    campaign_id: int
    scheduled_at: Optional[str] = None
    send_days: Optional[str] = None
    send_time_start: Optional[str] = None
    send_time_end: Optional[str] = None
    emails_per_day: Optional[int] = None
    use_account_rotation: Optional[bool] = None

class EmailAccountRequest(BaseModel):
    email: str
    smtp_preset: str = "gmail"
    username: str
    password: str
    daily_limit: int = 50

class SendEmailRequest(BaseModel):
    campaign_id: int
    smtp_preset: str = "gmail"
    username: str
    password: str
    max_send: Optional[int] = None
    only_verified: bool = True

class CVGenerateRequest(BaseModel):
    profile_url: Optional[str] = None
    generate_all: bool = False

# ── App Setup ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    os.makedirs("data/logs", exist_ok=True)
    os.makedirs("data/csv", exist_ok=True)
    os.makedirs("data/documents/generated_cvs", exist_ok=True)
    init_logging(level="INFO" if not APIConfig.DEBUG else "DEBUG")
    init_db()
    logger.info("API v%s starting", APIConfig.VERSION)
    yield
    logger.info("API shutting down")

app = FastAPI(
    title="LinkedIn Scraper API",
    description="Full control API for LinkedIn Scraper - all CLI actions available via REST",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=APIConfig.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health & Root ────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat(), "version": "2.0.0"}

@app.get("/api/")
async def root():
    return {
        "name": "LinkedIn Scraper API",
        "version": "2.0.0",
        "docs": "/docs",
        "actions": [
            "/api/scrape/google", "/api/scrape/group", "/api/scrape/search",
            "/api/enrich", "/api/cv/generate",
            "/api/email/campaigns", "/api/email/send", "/api/email/schedule",
            "/api/email/accounts",
            "/api/stats", "/api/export",
        ]
    }

# ── Helpers ──────────────────────────────────────────────

def _get_driver_and_auth():
    """Setup driver and authenticate. Returns (driver, auth_manager) or raises."""
    driver, temp_profile = DriverManager.setup_chrome_driver()
    auth_manager = AuthManager(LINKEDIN_EMAIL, LINKEDIN_PASSWORD)
    # Already logged in via browser profile? skip login
    if not auth_manager._verify_login(driver, timeout=3):
        if not auth_manager.login(driver):
            raise Exception("LinkedIn authentication failed")
    return driver, temp_profile, auth_manager

# ── Scraping Endpoints ─────────────────────────────────

@app.post("/api/scrape/google", dependencies=[Depends(verify_api_key)])
async def scrape_google(request: GoogleScrapeRequest, background_tasks: BackgroundTasks):
    """Scrape LinkedIn profiles via Google search."""
    job_id = create_job("scrape_google")
    
    def task():
        driver, temp_profile, _ = _get_driver_and_auth()
        try:
            update_job(job_id, status="running", progress=30)
            result = ScraperService.scrape_google_linkedin_profiles(
                driver, request.keywords, request.oblig_keywords,
                request.max_profiles, request.max_profiles_per_keyword,
                3, request.max_pages, request.verbose
            )
            update_job(job_id, status="completed", progress=100, result=result)
        except Exception as e:
            update_job(job_id, status="failed", error=str(e))
        finally:
            DriverManager.cleanup_driver(driver, temp_profile)
    
    background_tasks.add_task(task)
    return {"job_id": job_id, "status": "pending", "message": "Google scrape job created"}

@app.post("/api/scrape/group", dependencies=[Depends(verify_api_key)])
async def scrape_group(request: GroupScrapeRequest, background_tasks: BackgroundTasks):
    """Scrape LinkedIn group members."""
    job_id = create_job("scrape_group")
    
    def task():
        driver, temp_profile, _ = _get_driver_and_auth()
        try:
            update_job(job_id, status="running", progress=30)
            result = ScraperService.scrape_group_members(
                driver, request.group_url, request.max_members, request.scraping_mode
            )
            update_job(job_id, status="completed", progress=100, result=result)
        except Exception as e:
            update_job(job_id, status="failed", error=str(e))
        finally:
            DriverManager.cleanup_driver(driver, temp_profile)
    
    background_tasks.add_task(task)
    return {"job_id": job_id, "status": "pending", "message": "Group scrape job created"}

# ── Enrichment + CV Endpoints ──────────────────────────

@app.post("/api/enrich", dependencies=[Depends(verify_api_key)])
async def enrich_profiles_endpoint(request: EnrichRequest, background_tasks: BackgroundTasks):
    """Enrich profiles from CSV + optionally generate CVs."""
    job_id = create_job("enrich_profiles")
    
    def task():
        driver, temp_profile, _ = _get_driver_and_auth()
        try:
            update_job(job_id, status="running", progress=20)
            result = ProfileEnricherService.enrich_profiles_from_csv(
                driver, request.csv_file_path, request.url_column, request.max_profiles
            )
            update_job(job_id, status="completed", progress=100, result=result)
        except Exception as e:
            update_job(job_id, status="failed", error=str(e))
        finally:
            DriverManager.cleanup_driver(driver, temp_profile)
    
    background_tasks.add_task(task)
    return {"job_id": job_id, "status": "pending", "message": "Enrichment job created"}

@app.post("/api/cv/generate", dependencies=[Depends(verify_api_key)])
async def generate_cv_endpoint(request: CVGenerateRequest):
    """Generate CV(s) using Groq AI."""
    try:
        from core.groq_service import GroqService
        from core.cv_generator import generate_cv_for_profile, get_profiles_without_cv
        
        groq = GroqService()
        
        if request.profile_url:
            cv_path = generate_cv_for_profile(request.profile_url, groq)
            return {"success": True, "cv_path": cv_path, "message": "CV generated"}
        elif request.generate_all:
            profiles = get_profiles_without_cv()
            generated = 0
            for p in profiles:
                try:
                    generate_cv_for_profile(p['profile_url'], groq)
                    generated += 1
                except Exception:
                    pass
            return {"success": True, "generated": generated, "message": f"Generated {generated} CVs"}
        else:
            return {"success": False, "message": "Provide profile_url or set generate_all=True"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Email Campaign Endpoints ────────────────────────────

@app.post("/api/email/campaigns", dependencies=[Depends(verify_api_key)])
async def create_campaign(request: EmailCampaignRequest):
    """Create a new email campaign."""
    try:
        from core.database import create_email_campaign
        campaign_id = create_email_campaign(
            request.name, request.subject, request.body_text,
            request.body_html, request.cv_path, request.cover_letter_path
        )
        return {"success": True, "campaign_id": campaign_id, "message": "Campaign created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/email/campaigns", dependencies=[Depends(verify_api_key)])
async def list_campaigns():
    """List all email campaigns."""
    campaigns = get_all_email_campaigns()
    return {"campaigns": campaigns}

@app.post("/api/email/send", dependencies=[Depends(verify_api_key)])
async def send_emails(request: SendEmailRequest):
    """Send emails for a campaign."""
    try:
        result = EmailSendingService.send_campaign(
            campaign_id=request.campaign_id,
            smtp_preset=request.smtp_preset,
            username=request.username,
            password=request.password,
            max_send=request.max_send,
            only_verified=request.only_verified
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Scheduling Endpoints ────────────────────────────────

@app.post("/api/email/schedule", dependencies=[Depends(verify_api_key)])
async def schedule_campaign(request: ScheduleCampaignRequest):
    """Schedule a campaign."""
    try:
        scheduler = EmailScheduler()
        result = scheduler.schedule_campaign(
            campaign_id=request.campaign_id,
            scheduled_at=request.scheduled_at,
            send_days=request.send_days,
            send_time_start=request.send_time_start,
            send_time_end=request.send_time_end,
            emails_per_day=request.emails_per_day,
            use_account_rotation=request.use_account_rotation
        )
        return {"success": result, "message": "Campaign scheduled" if result else "Failed to schedule"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/email/scheduler/run", dependencies=[Depends(verify_api_key)])
async def run_scheduler_endpoint(background_tasks: BackgroundTasks):
    """Run the email scheduler manually."""
    def task():
        run_scheduler()
    background_tasks.add_task(task)
    return {"success": True, "message": "Scheduler started"}

# ── Email Account Endpoints ─────────────────────────────

@app.post("/api/email/accounts", dependencies=[Depends(verify_api_key)])
async def add_account(request: EmailAccountRequest):
    """Add a new email account."""
    account_id = add_email_account(
        request.email, request.smtp_preset, request.username,
        request.password, request.daily_limit
    )
    return {"success": True, "account_id": account_id, "message": "Account added"}

@app.get("/api/email/accounts", dependencies=[Depends(verify_api_key)])
async def list_accounts(active_only: bool = False):
    """List email accounts."""
    accounts = get_email_accounts(active_only=active_only)
    return {"accounts": accounts}

# ── Statistics & Export ─────────────────────────────────

@app.get("/api/stats", dependencies=[Depends(verify_api_key)])
async def get_statistics():
    """Get database statistics."""
    stats = get_stats()
    return {"stats": stats}

@app.get("/api/profiles/enriched", dependencies=[Depends(verify_api_key)])
async def list_enriched_profiles(limit: int = 100, offset: int = 0):
    """List enriched profiles."""
    profiles = get_all_enriched_profiles()
    return {"profiles": profiles[offset:offset+limit], "total": len(profiles)}

# ── Job Status ───────────────────────────────────────────

@app.get("/api/jobs/{job_id}", dependencies=[Depends(verify_api_key)])
async def get_job_status(job_id: str):
    """Get job status."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

# ── Serve Frontend ──────────────────────────────────────

# Mount static files (frontend)
if os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

# ── Main ────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host=APIConfig.HOST,
        port=APIConfig.PORT,
        reload=APIConfig.DEBUG,
    )
