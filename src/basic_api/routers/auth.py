"""
Authentication wrapper endpoints.

Provides standardized /auth/* endpoints for frontend compatibility.
These are thin wrappers around the existing OAuth2 + JWT authentication.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from ..dependencies import get_current_user
from ..schemas import SuccessResponse

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me", response_model=SuccessResponse[dict])
async def get_current_user_info(
    current_user: Annotated[str, Depends(get_current_user)],
):
    """
    Get current authenticated user information.

    Returns information about the currently authenticated user based on the JWT token.
    This is a wrapper endpoint for frontend compatibility.

    Args:
        current_user: Username extracted from JWT token (injected)

    Returns:
        SuccessResponse[dict]: User information
            {
                "success": true,
                "message": "User retrieved successfully",
                "data": {
                    "username": "admin",
                    "email": "admin@example.com",
                    "role": "admin"
                }
            }

    Example:
        curl http://localhost:8000/auth/me \\
             -H "Authorization: Bearer eyJ..."
    """
    return SuccessResponse(
        success=True,
        message="User retrieved successfully",
        data={
            "username": current_user,
            # Placeholder - extend with real user data
            "email": f"{current_user}@example.com",
            "role": "admin",  # Placeholder - extend with real role management
        },
    )


@router.post("/logout", response_model=SuccessResponse[None])
async def logout(current_user: Annotated[str, Depends(get_current_user)]):
    """
    Logout endpoint (client-side token deletion).

    This endpoint validates the token and returns success. The actual logout
    is handled client-side by deleting the JWT token from storage.

    JWT tokens are stateless, so there's no server-side session to invalidate.
    The client should delete the token from localStorage/sessionStorage.

    Args:
        current_user: Username extracted from JWT token (injected)

    Returns:
        SuccessResponse[None]: Logout confirmation
            {
                "success": true,
                "message": "Logout successful. Please delete your token client-side.",
                "data": null
            }

    Note:
        For enhanced security in production, consider:
        - Token blacklisting with Redis
        - Short token expiration times
        - Refresh token rotation

    Example:
        curl -X POST http://localhost:8000/auth/logout \\
             -H "Authorization: Bearer eyJ..."
    """
    return SuccessResponse(
        success=True,
        message="Logout successful. Please delete your token client-side.",
        data=None,
    )
