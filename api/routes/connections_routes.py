"""
Connection API Routes
"""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from api.models.requests import ConnectionRequest, MassConnectionRequest
from api.models.responses import JobResponse, StatusResponse
from api.middleware.auth import verify_api_key
from api.dependencies import create_job, update_job, get_job
from core.services.connection_service import ConnectionService
from core.driver_manager import DriverManager
from datetime import datetime


router = APIRouter(prefix="/connections", tags=["Connections"])


def run_single_connection_task(job_id: str, request: ConnectionRequest):
    """Background task for sending single connection"""
    driver = None
    temp_profile = None
    
    try:
        update_job(job_id, status="running", progress=20)
        
        # Get authenticated driver
        driver, temp_profile = DriverManager.setup_chrome_driver()
        from auth.auth_manager import AuthManager
        from config import settings
        
        auth_manager = AuthManager(settings.LINKEDIN_EMAIL, settings.LINKEDIN_PASSWORD)
        if not auth_manager.login(driver):
            raise Exception("Authentication failed")
        
        update_job(job_id, status="running", progress=50)
        
        # Send connection
        result = ConnectionService.send_single_connection(
            driver,
            request.profile_url,
            request.note_message
        )
        
        update_job(job_id, status="completed", progress=100, result=result)
        
    except Exception as e:
        update_job(job_id, status="failed", error=str(e))
    finally:
        if driver:
            DriverManager.cleanup_driver(driver, temp_profile)


def run_mass_connection_task(job_id: str, request: MassConnectionRequest):
    """Background task for sending mass connections"""
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
        
        # Send mass connections
        result = ConnectionService.send_mass_connections(
            driver,
            request.csv_file_path,
            request.note_message,
            request.use_note
        )
        
        update_job(job_id, status="completed", progress=100, result=result)
        
    except Exception as e:
        update_job(job_id, status="failed", error=str(e))
    finally:
        if driver:
            DriverManager.cleanup_driver(driver, temp_profile)


@router.post("/send", response_model=JobResponse, dependencies=[Depends(verify_api_key)])
async def send_connection(request: ConnectionRequest, background_tasks: BackgroundTasks):
    """
    Send a single connection request
    
    This endpoint initiates a background job to send a connection request to a LinkedIn profile.
    Returns a job ID that can be used to check the status of the operation.
    """
    job_id = create_job("send_connection")
    
    # Add background task
    background_tasks.add_task(run_single_connection_task, job_id, request)
    
    return JobResponse(
        job_id=job_id,
        status="pending",
        message="Connection request job created successfully",
        created_at=datetime.utcnow().isoformat()
    )


@router.post("/mass-send", response_model=JobResponse, dependencies=[Depends(verify_api_key)])
async def send_mass_connections(request: MassConnectionRequest, background_tasks: BackgroundTasks):
    """
    Send mass connection requests from CSV
    
    This endpoint initiates a background job to send connection requests to multiple profiles from a CSV file.
    Returns a job ID that can be used to check the status of the operation.
    """
    job_id = create_job("mass_connections")
    
    # Add background task
    background_tasks.add_task(run_mass_connection_task, job_id, request)
    
    return JobResponse(
        job_id=job_id,
        status="pending",
        message="Mass connection job created successfully",
        created_at=datetime.utcnow().isoformat()
    )


@router.get("/status/{job_id}", response_model=StatusResponse, dependencies=[Depends(verify_api_key)])
async def get_connection_status(job_id: str):
    """
    Get the status of a connection job
    
    Returns the current status, progress, and results (if completed) of a connection job.
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
