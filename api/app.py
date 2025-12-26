"""
FastAPI Application - LinkedIn Scraper API
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from config.api_config import APIConfig
from api.routes import scraper_router, connections_router, messaging_router
from api.models.responses import HealthResponse, ErrorResponse
from datetime import datetime
import traceback


# Create FastAPI app
app = FastAPI(
    title=APIConfig.TITLE,
    description=APIConfig.DESCRIPTION,
    version=APIConfig.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=APIConfig.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions"""
    error_detail = traceback.format_exc() if APIConfig.DEBUG else str(exc)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="InternalServerError",
            message="An unexpected error occurred",
            detail=error_detail
        ).dict()
    )


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Health check endpoint
    
    Returns the current status and version of the API.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version=APIConfig.VERSION
    )


# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """
    Root endpoint
    
    Returns basic information about the API.
    """
    return {
        "name": APIConfig.TITLE,
        "version": APIConfig.VERSION,
        "docs": "/docs",
        "health": "/health"
    }


# Include routers
app.include_router(scraper_router, prefix="/api/v1")
app.include_router(connections_router, prefix="/api/v1")
app.include_router(messaging_router, prefix="/api/v1")


# Startup event
@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    print(f"🚀 {APIConfig.TITLE} v{APIConfig.VERSION} starting...")
    print(f"📚 API Documentation: http://{APIConfig.HOST}:{APIConfig.PORT}/docs")
    print(f"🔑 API Key Authentication: {APIConfig.API_KEY_NAME} header required")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    print("👋 Shutting down API server...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.app:app",
        host=APIConfig.HOST,
        port=APIConfig.PORT,
        reload=APIConfig.DEBUG
    )
