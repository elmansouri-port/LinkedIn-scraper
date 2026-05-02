"""
Messaging API Routes.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from api.dependencies import create_job, get_job, update_job
from api.middleware.auth import verify_api_key
from api.models.requests import MessageRequest
from api.models.responses import JobResponse, StatusResponse
from auth.auth_manager import AuthManager
from config import LINKEDIN_EMAIL, LINKEDIN_PASSWORD
from core.driver_manager import DriverManager
from core.services.messaging_service import MessagingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/messages", tags=["Messaging"])


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


def run_group_messaging_task(job_id: str, request: MessageRequest):
    """Background task for group messaging."""
    def task(driver, jid):
        result = MessagingService.send_group_messages(driver)
        update_job(jid, result=result)

    _run_with_driver(job_id, task)


@router.post("/group", response_model=JobResponse, dependencies=[Depends(verify_api_key)])
async def send_group_messages(request: MessageRequest, background_tasks: BackgroundTasks):
    """Send messages to group members."""
    job_id = create_job("group_messaging")
    background_tasks.add_task(run_group_messaging_task, job_id, request)
    return JobResponse(
        job_id=job_id,
        status="pending",
        message="Group messaging job created successfully",
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/status/{job_id}", response_model=StatusResponse, dependencies=[Depends(verify_api_key)])
async def get_message_status(job_id: str):
    """Get the status of a messaging job."""
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
