"""
API Authentication Middleware
"""
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from config.api_config import APIConfig


# API Key header
api_key_header = APIKeyHeader(name=APIConfig.API_KEY_NAME, auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    """Verify API key from request header
    
    Args:
        api_key: API key from header
        
    Returns:
        str: The validated API key
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if api_key not in APIConfig.API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    
    return api_key
