"""
API Models Package
"""
from .requests import (
    GroupScrapeRequest,
    SearchScrapeRequest,
    GoogleScrapeRequest,
    ConnectionRequest,
    MassConnectionRequest,
    MessageRequest
)
from .responses import (
    JobResponse,
    StatusResponse,
    ScrapeResultResponse,
    ConnectionResultResponse,
    MessageResultResponse,
    ErrorResponse,
    HealthResponse
)

__all__ = [
    # Request models
    'GroupScrapeRequest',
    'SearchScrapeRequest',
    'GoogleScrapeRequest',
    'ConnectionRequest',
    'MassConnectionRequest',
    'MessageRequest',
    # Response models
    'JobResponse',
    'StatusResponse',
    'ScrapeResultResponse',
    'ConnectionResultResponse',
    'MessageResultResponse',
    'ErrorResponse',
    'HealthResponse',
]
