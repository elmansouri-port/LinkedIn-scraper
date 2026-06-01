"""
Unified FastAPI Backend for LinkedIn Scraper
Provides REST API access to ALL CLI actions:
- Scraping (group, search, Google)
- Enrichment (CSV + DB) + optional CV generation
- Connections (single + mass)
- Messaging (group outreach)
- Email campaigns: create, send, schedule
- Email account rotation management
- CV generation
- Statistics & export
"""
import os
import sys
import logging
from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config.api_config import APIConfig
from config.scraper_config import LINKEDIN_EMAIL, LINKEDIN_PASSWORD
from api.middleware.auth import verify_api_key
from api.dependencies import create_job, get_job, update_job
from auth.auth_manager import AuthManager
from core.driver_manager import DriverManager
from core.services import ScraperService, ProfileEnricherService
# email services now handled in api/routes/email_routes.py
from core.database import (
    get_all_enriched_profiles, get_all_search_profiles, get_stats, init_db,
)
from utils.logger import init_logging

# ── Routers ──────────────────────────────────────────────
from api.routes.scraper_routes import router as scraper_router
from api.routes.connections_routes import router as connections_router
from api.routes.messaging_routes import router as messaging_router
from api.routes.auth_routes import router as auth_router
from api.routes.profiles_routes import router as profiles_router
from api.routes.email_routes import router as email_router

logger = logging.getLogger(__name__)


# ── Request Models ────────────────────────────────────────

class EnrichRequest(BaseModel):
    csv_file_path: str
    url_column: str = "Profile URL"
    max_profiles: Optional[int] = None

class EnrichFromDBRequest(BaseModel):
    max_profiles: Optional[int] = None
    profile_indices: Optional[list] = None
    range_start: Optional[int] = None
    range_end: Optional[int] = None

class CVGenerateRequest(BaseModel):
    profile_url: Optional[str] = None
    generate_all: bool = False


# ── App Setup ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("data/logs", exist_ok=True)
    os.makedirs("data/csv", exist_ok=True)
    os.makedirs("data/documents/generated_cvs", exist_ok=True)
    init_logging(level="DEBUG" if APIConfig.DEBUG else "INFO")
    init_db()
    logger.info("API v%s starting (debug=%s)", APIConfig.VERSION, APIConfig.DEBUG)
    yield
    logger.info("API shutting down")


app = FastAPI(
    title="LinkedIn Scraper API",
    description="Full control API — all scraping, enrichment, connection, messaging, and email actions",
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

# ── Register routers ──────────────────────────────────────
app.include_router(scraper_router, prefix="/api")
app.include_router(connections_router, prefix="/api")
app.include_router(messaging_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(profiles_router, prefix="/api")
app.include_router(email_router, prefix="/api")


# ── Health & Root ──────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0",
    }

@app.get("/api/")
async def root():
    return {
        "name": "LinkedIn Scraper API",
        "version": "2.0.0",
        "docs": "/docs",
        "scraping": [
            "POST /api/scrape/google",
            "POST /api/scrape/group",
            "POST /api/scrape/search",
        ],
        "enrichment": [
            "POST /api/enrich",
            "POST /api/enrich/db",
        ],
        "connections": [
            "POST /api/connections/send",
            "POST /api/connections/mass-send",
        ],
        "messaging": [
            "POST /api/messages/group",
        ],
        "email": [
            "GET  /api/email/campaigns",
            "POST /api/email/campaigns",
            "POST /api/email/send",
            "POST /api/email/schedule",
            "POST /api/email/scheduler/run",
            "GET  /api/email/accounts",
            "POST /api/email/accounts",
            "POST /api/email/accounts/reset",
        ],
        "cv": ["POST /api/cv/generate"],
        "data": [
            "GET /api/stats",
            "GET /api/export",
            "GET /api/profiles/enriched",
            "GET /api/profiles/search",
            "GET /api/jobs/{job_id}",
        ],
    }


# ── Shared driver helper ───────────────────────────────────

def _get_driver_and_auth():
    """Setup Chrome driver + authenticate. Raises on failure."""
    driver, temp_profile = DriverManager.setup_chrome_driver()
    auth = AuthManager(LINKEDIN_EMAIL, LINKEDIN_PASSWORD)
    if not auth._verify_login(driver, timeout=3):
        if not auth.login(driver):
            DriverManager.cleanup_driver(driver, temp_profile)
            raise RuntimeError("LinkedIn authentication failed")
    return driver, temp_profile


# ── Enrichment ─────────────────────────────────────────────

@app.post("/api/enrich", dependencies=[Depends(verify_api_key)])
async def enrich_from_csv(request: EnrichRequest, background_tasks: BackgroundTasks):
    """Enrich profiles from a CSV file (visits each LinkedIn profile)."""
    job_id = create_job("enrich_csv")

    def task():
        driver, temp_profile = _get_driver_and_auth()
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
    return {"job_id": job_id, "status": "pending", "message": "CSV enrichment job created"}


@app.post("/api/enrich/db", dependencies=[Depends(verify_api_key)])
async def enrich_from_db(request: EnrichFromDBRequest, background_tasks: BackgroundTasks):
    """Enrich profiles that are already in the database (from a previous scrape)."""
    job_id = create_job("enrich_db")

    profile_range = None
    if request.range_start is not None and request.range_end is not None:
        profile_range = (request.range_start, request.range_end)

    def task():
        driver, temp_profile = _get_driver_and_auth()
        try:
            update_job(job_id, status="running", progress=20)
            result = ProfileEnricherService.enrich_profiles_from_db(
                driver,
                profile_indices=request.profile_indices,
                profile_range=profile_range,
                max_profiles=request.max_profiles,
            )
            update_job(job_id, status="completed", progress=100, result=result)
        except Exception as e:
            update_job(job_id, status="failed", error=str(e))
        finally:
            DriverManager.cleanup_driver(driver, temp_profile)

    background_tasks.add_task(task)
    return {"job_id": job_id, "status": "pending", "message": "DB enrichment job created"}


# ── CV Generation ──────────────────────────────────────────

@app.post("/api/cv/generate", dependencies=[Depends(verify_api_key)])
async def generate_cv(request: CVGenerateRequest):
    """Generate CV(s) using Groq AI."""
    try:
        from core.groq_service import GroqService
        from core.cv_generator import generate_cv_for_profile, get_profiles_without_cv

        groq = GroqService()

        if request.profile_url:
            cv_path = generate_cv_for_profile(request.profile_url, groq)
            return {"success": True, "cv_path": cv_path, "message": "CV generated"}

        if request.generate_all:
            profiles = get_profiles_without_cv()
            generated = 0
            for p in profiles:
                try:
                    generate_cv_for_profile(p["profile_url"], groq)
                    generated += 1
                except Exception:
                    pass
            return {"success": True, "generated": generated, "message": f"Generated {generated} CVs"}

        return {"success": False, "message": "Provide profile_url or set generate_all=True"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Statistics & Data ──────────────────────────────────────

@app.get("/api/stats", dependencies=[Depends(verify_api_key)])
async def get_statistics():
    """Row counts for all database tables."""
    return {"stats": get_stats()}

@app.get("/api/profiles/enriched", dependencies=[Depends(verify_api_key)])
async def list_enriched_profiles(limit: int = 100, offset: int = 0):
    """Paginated list of enriched profiles."""
    profiles = get_all_enriched_profiles()
    return {"profiles": profiles[offset:offset + limit], "total": len(profiles)}

@app.get("/api/profiles/search", dependencies=[Depends(verify_api_key)])
async def list_search_profiles(limit: int = 100, offset: int = 0):
    """Paginated list of profiles from Google/LinkedIn search."""
    profiles = get_all_search_profiles()
    return {"profiles": profiles[offset:offset + limit], "total": len(profiles)}

@app.get("/api/export", dependencies=[Depends(verify_api_key)])
async def export_csv():
    """Download enriched profiles + emails as CSV."""
    import tempfile
    from core.export_manager import export_preset_to_csv
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
        tmp.close()
        ok = export_preset_to_csv("enriched_emails", tmp.name)
        if not ok:
            raise HTTPException(status_code=404, detail="No enriched profiles to export")
        return FileResponse(tmp.name, media_type="text/csv", filename="enriched_profiles.csv")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Job Status ─────────────────────────────────────────────

@app.get("/api/jobs/{job_id}", dependencies=[Depends(verify_api_key)])
async def get_job_status(job_id: str):
    """Poll the status of a background job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ── Serve Frontend ─────────────────────────────────────────

if os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


# ── Entry point ────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host=APIConfig.HOST,
        port=APIConfig.PORT,
        reload=APIConfig.DEBUG,
    )
