"""
Messaging API Routes
"""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from api.models.requests import MessageRequest
from api.models.responses import JobResponse, StatusResponse
from api.middleware.auth import verify_api_key
from api.dependencies import create_job, update_job, get_job
from core.services.messaging_service import MessagingService
from core.driver_manager import DriverManager
from datetime import datetime


router = APIRouter(prefix="/messages", tags=["Messaging"])


def run_group_messaging_task(job_id: str, request: MessageRequest):
    """Background task for group messaging"""
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
        
        # Send messages
        result = MessagingService.send_group_messages(driver)
        
        update_job(job_id, status="completed", progress=100, result=result)
        
    except Exception as e:
        update_job(job_id, status="failed", error=str(e))
    finally:
        if driver:
            DriverManager.cleanup_driver(driver, temp_profile)


@router.post("/group", response_model=JobResponse, dependencies=[Depends(verify_api_key)])
async def send_group_messages(request: MessageRequest, background_tasks: BackgroundTasks):
    """
    Send messages to group members
    
    This endpoint initiates a background job to send messages to LinkedIn group members.
    Returns a job ID that can be used to check the status of the operation.
    """
    job_id = create_job("group_messaging")
    
    # Add background task
    background_tasks.add_task(run_group_messaging_task, job_id, request)
    
    return JobResponse(
        job_id=job_id,
        status="pending",
        message="Group messaging job created successfully",
        created_at=datetime.utcnow().isoformat()
    )


@router.get("/status/{job_id}", response_model=StatusResponse, dependencies=[Depends(verify_api_key)])
async def get_message_status(job_id: str):
    """
    Get the status of a messaging job
    
    Returns the current status, progress, and results (if completed) of a messaging job.
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
