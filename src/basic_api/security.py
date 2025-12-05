from fastapi import Header, HTTPException, status
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")

async def verify_api_key(x_api_key: str = Header(..., description="Global API Key")):
    """
    Verify the API key for all endpoints.
    """
    if not API_KEY:
        # If no key is configured, fail secure or allow all? 
        # Better to fail secure and require configuration.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key not configured on server"
        )
    
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    return x_api_key
