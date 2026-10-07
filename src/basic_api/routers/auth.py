"""
Authentication wrapper endpoints.

Thin /auth/* routes around the OAuth2 + JWT flow for frontend convenience.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from ..dependencies import get_current_user
from ..schemas import SuccessResponse, UserResponseSchema
from ..schemas.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me", response_model=SuccessResponse[UserResponseSchema])
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    The authenticated user, as stored.

    Args:
        current_user: The User the bearer token belongs to (injected).

    Returns:
        SuccessResponse[UserResponseSchema]: The user's profile fields, never
            the password hash
            {
                "success": true,
                "message": "User retrieved successfully",
                "data": {"id": 1, "username": "alice", "email": "...", ...}
            }

    Example:
        curl http://localhost:8000/api/auth/me \\
             -H "X-API-Key: your-api-key" \\
             -H "Authorization: Bearer eyJ..."
    """
    return SuccessResponse(
        success=True, message="User retrieved successfully", data=current_user
    )


@router.post("/logout", response_model=SuccessResponse[None])
async def logout(current_user: Annotated[User, Depends(get_current_user)]):
    """
    Confirm a logout. Tokens are stateless, so the client deletes its copy;
    nothing is invalidated server-side (see docs/known_issues.md).

    Args:
        current_user: The User the bearer token belongs to (injected); a valid
            token is required so that only a logged-in client can "log out".

    Returns:
        SuccessResponse[None]: Confirmation
            {
                "success": true,
                "message": "Logout successful. Please delete your token client-side.",
                "data": null
            }

    Example:
        curl -X POST http://localhost:8000/api/auth/logout \\
             -H "X-API-Key: your-api-key" \\
             -H "Authorization: Bearer eyJ..."
    """
    return SuccessResponse(
        success=True,
        message="Logout successful. Please delete your token client-side.",
        data=None,
    )
