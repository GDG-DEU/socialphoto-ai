"""
API Key authentication service for securing endpoints.
"""
from fastapi import Header, HTTPException, status
from src.config import get_settings


async def verify_api_key(
    x_api_key: str | None = Header(None, description="API Key for authentication")
):
   
    """
    Dependency function to verify API key from X-API-Key header.
    
    Args:
        x_api_key: API key from the X-API-Key header
        
    Raises:
        HTTPException: If API key is missing or invalid
        
    Returns:
        str: The validated API key
    """
    api_key = get_settings().x_api_key

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API_KEY not configured on server"
        )
    
    if not x_api_key or x_api_key != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return x_api_key
