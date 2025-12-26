"""
API Response Models - Pydantic schemas for responses
"""
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
from datetime import datetime


class JobResponse(BaseModel):
    """Response for job creation"""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status: pending, running, completed, failed")
    message: str = Field(..., description="Status message")
    created_at: str = Field(..., description="Job creation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job_abc123",
                "status": "pending",
                "message": "Job created successfully",
                "created_at": "2025-12-26T19:42:00Z"
            }
        }


class StatusResponse(BaseModel):
    """Response for job status check"""
    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Job status")
    progress: Optional[int] = Field(None, description="Progress percentage (0-100)")
    message: str = Field(..., description="Status message")
    result: Optional[Dict[str, Any]] = Field(None, description="Result data if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job_abc123",
                "status": "running",
                "progress": 45,
                "message": "Scraping in progress...",
                "result": None,
                "error": None
            }
        }


class ScrapeResultResponse(BaseModel):
    """Response for scraping operations"""
    success: bool = Field(..., description="Whether operation succeeded")
    data: Optional[Dict[str, Any]] = Field(None, description="Scraped data")
    total_scraped: Optional[int] = Field(None, description="Total items scraped")
    message: str = Field(..., description="Result message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"profiles": []},
                "total_scraped": 50,
                "message": "Successfully scraped 50 profiles"
            }
        }


class ConnectionResultResponse(BaseModel):
    """Response for connection operations"""
    success: bool = Field(..., description="Whether operation succeeded")
    profile_url: Optional[str] = Field(None, description="Profile URL")
    sent_count: Optional[int] = Field(None, description="Number of connections sent")
    message: str = Field(..., description="Result message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "profile_url": "https://www.linkedin.com/in/johndoe/",
                "sent_count": 1,
                "message": "Connection request sent successfully"
            }
        }


class MessageResultResponse(BaseModel):
    """Response for messaging operations"""
    success: bool = Field(..., description="Whether operation succeeded")
    sent_count: Optional[int] = Field(None, description="Number of messages sent")
    message: str = Field(..., description="Result message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "sent_count": 25,
                "message": "Messages sent to 25 group members"
            }
        }


class ErrorResponse(BaseModel):
    """Error response"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid request parameters",
                "detail": "group_url field is required"
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Current timestamp")
    version: str = Field(..., description="API version")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-12-26T19:42:00Z",
                "version": "1.0.0"
            }
        }
