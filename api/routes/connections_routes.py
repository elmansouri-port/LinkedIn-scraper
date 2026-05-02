"""
Connection API Routes.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from api.dependencies import create_job, get_job, update_job
from api.middleware.auth import verify_api_key
from api.models.requests import ConnectionRequest, MassConnectionRequest
from api.models.responses import JobResponse, StatusResponse
from auth.auth_manager import AuthManager
from config import LINKEDIN_EMAIL, LINKEDIN_PASSWORD
from core.driver_manager import DriverManager
from core.services.connection_service import ConnectionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connections", tags=["Connections"])


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


def run_single_connection_task(job_id: str, request: ConnectionRequest):
    """Background task for sending single connection."""
    def task(driver, jid):
        result = ConnectionService.send_single_connection(
            driver, request.profile_url, request.note_message
        )
        update_job(jid, result=result)

    _run_with_driver(job_id, task)


def run_mass_connection_task(job_id: str, request: MassConnectionRequest):
    """Background task for sending mass connections."""
    def task(driver, jid):
        result = ConnectionService.send_mass_connections(
            driver, request.csv_file_path, request.note_message, request.use_note
        )
        update_job(jid, result=result)

    _run_with_driver(job_id, task)


@router.post("/send", response_model=JobResponse, dependencies=[Depends(verify_api_key)])
async def send_connection(request: ConnectionRequest, background_tasks: BackgroundTasks):
    """Send a single connection request."""
    job_id = create_job("send_connection")
    background_tasks.add_task(run_single_connection_task, job_id, request)
    return JobResponse(
        job_id=job_id,
        status="pending",
        message="Connection request job created successfully",
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/mass-send", response_model=JobResponse, dependencies=[Depends(verify_api_key)])
async def send_mass_connections(request: MassConnectionRequest, background_tasks: BackgroundTasks):
    """Send mass connection requests from CSV."""
    job_id = create_job("mass_connections")
    background_tasks.add_task(run_mass_connection_task, job_id, request)
    return JobResponse(
        job_id=job_id,
        status="pending",
        message="Mass connection job created successfully",
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/status/{job_id}", response_model=StatusResponse, dependencies=[Depends(verify_api_key)])
async def get_connection_status(job_id: str):
    """Get the status of a connection job."""
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
