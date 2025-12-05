"""
FastAPI dependency injection providers.

Provides reusable dependencies for:
- Service instantiation
- Database sessions
- Authentication (OAuth2 + JWT)
- Configuration access
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlmodel.ext.asyncio.session import AsyncSession

from .auth import decode_access_token
from .database import get_session

# OAuth2 scheme for JWT token authentication
# tokenUrl is the endpoint where clients can get tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user_from_cookie(request: Request) -> str | None:
    """
    Validate JWT token from cookie and return username.
    This is for browser-based flows where headers are not sent.
    """
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        username: str | None = payload.get("sub")
        return username
    except HTTPException:
        return None


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)]
) -> str:
    """
    Validate JWT token and return current username.
    
    This dependency should be used to protect endpoints that require authentication.
    It extracts the token from the Authorization header, validates it, and returns
    the username from the token claims.
    
    Args:
        token: JWT token from Authorization header (provided by oauth2_scheme)
        settings: Application settings (provided by get_settings)
        
    Returns:
        Username from token claims
        
    Raises:
        HTTPException: 401 if token is invalid or expired
        
    Example:
        @router.get("/protected")
        async def protected_endpoint(
            current_user: Annotated[str, Depends(get_current_user)]
        ):
            return {"message": f"Hello {current_user}"}
    """
    # Decode and validate token (raises HTTPException if invalid)
    payload = decode_access_token(token)

    # Extract username from token claims
    username: str | None = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials: missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return username