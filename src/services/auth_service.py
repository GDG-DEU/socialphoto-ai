"""
API Key authentication service for securing endpoints.
"""
from fastapi import Header, HTTPException, status
from src.config import get_settings


settings = get_settings()
API_KEY = settings.x_api_key



async def verify_api_key(x_api_key: str = Header(..., description="API Key for authentication")):
   
    """
    Dependency function to verify API key from X-API-Key header.
    
    Args:
        x_api_key: API key from the X-API-Key header
        
    Raises:
        HTTPException: If API key is missing or invalid
        
    Returns:
        str: The validated API key
    """
    if not API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API_KEY not configured on server"
        )
    
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return x_api_key
