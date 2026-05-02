"""
FastAPI Application - LinkedIn Scraper API
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from config.api_config import APIConfig
from api.routes import scraper_router, connections_router, messaging_router
from api.models.responses import HealthResponse, ErrorResponse
from utils.logger import init_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    import os
    os.makedirs("data/logs", exist_ok=True)
    os.makedirs("data/csv", exist_ok=True)

    init_logging(level="INFO" if not APIConfig.DEBUG else "DEBUG")
    logger.info("%s v%s starting", APIConfig.TITLE, APIConfig.VERSION)
    logger.info("API documentation: http://%s:%s/docs", APIConfig.HOST, APIConfig.PORT)
    logger.info("API key authentication: %s header required", APIConfig.API_KEY_NAME)

    yield

    # Shutdown
    logger.info("Shutting down API server")


# Create FastAPI app
app = FastAPI(
    title=APIConfig.TITLE,
    description=APIConfig.DESCRIPTION,
    version=APIConfig.VERSION,
    docs_url="/docs" if APIConfig.DEBUG else None,
    redoc_url="/redoc" if APIConfig.DEBUG else None,
    openapi_url="/openapi.json" if APIConfig.DEBUG else None,
    lifespan=lifespan,
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
    """Handle all uncaught exceptions."""
    import traceback
    error_detail = traceback.format_exc() if APIConfig.API_DEBUG else str(exc)
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="InternalServerError",
            message="An unexpected error occurred",
            detail=error_detail,
        ).dict(),
    )


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=APIConfig.VERSION,
    )


# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """Root endpoint."""
    return {
        "name": APIConfig.TITLE,
        "version": APIConfig.VERSION,
        "docs": "/docs",
        "health": "/health",
    }


# Include routers
app.include_router(scraper_router, prefix="/api/v1")
app.include_router(connections_router, prefix="/api/v1")
app.include_router(messaging_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.app:app",
        host=APIConfig.HOST,
        port=APIConfig.PORT,
        reload=APIConfig.DEBUG,
    )
