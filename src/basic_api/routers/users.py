"""
User routes: registration, and self-service on the authenticated account.

There is deliberately no listing or read-by-id: a user reads their own profile
at /users/me, and nothing here exposes other accounts.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from ..database import get_session
from ..dependencies import get_current_user
from ..exceptions import IdentifierTakenError, PasswordVerificationError
from ..limiter import RATE_LIMIT_REGISTER, limiter
from ..schemas import SuccessResponse
from ..schemas.user import (
    PasswordChangeSchema,
    User,
    UserCreateSchema,
    UserDeleteSchema,
    UserResponseSchema,
    UserUpdateSchema,
)
from ..services import users as user_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=SuccessResponse[UserResponseSchema], status_code=201)
@limiter.limit(RATE_LIMIT_REGISTER)
async def create_user(
    request: Request,
    user_create: UserCreateSchema = Body(...),
    session: AsyncSession = Depends(get_session),
):
    """
    Register a user. Rate-limited per client IP (RATE_LIMIT_REGISTER).

    Args:
        request: Needed by the rate limiter (injected).
        user_create: Registration payload; `username` and `password` required.
        session: Database session.

    Returns:
        SuccessResponse[UserResponseSchema]: The stored user, never the hash.

    Raises:
        HTTPException: 409 naming the field that is already taken (username,
            email or phone), or with a generic message if two registrations
            raced past the checks; 500, logged, for anything else; 429 over
            the rate limit, with a Retry-After header. The response never
            carries the database's error text.

    Example:
        curl -X POST http://localhost:8000/api/users/ \\
             -H "X-API-Key: your-api-key" \\
             -H "Content-Type: application/json" \\
             -d '{"username": "alice", "email": "alice@example.com", "password": "..."}'
    """
    try:
        db_user = await user_service.create_user(session, user_create)
    except IdentifierTakenError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception:
        await session.rollback()
        logger.exception("Failed to create user")
        raise HTTPException(status_code=500, detail="Failed to create user")
    return SuccessResponse(
        success=True, message="User created successfully", data=db_user
    )


@router.get("/me", response_model=SuccessResponse[UserResponseSchema])
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    The authenticated user's profile.

    Args:
        current_user: The User the bearer token belongs to (injected).

    Returns:
        SuccessResponse[UserResponseSchema]: The profile, never the hash.

    Example:
        curl http://localhost:8000/api/users/me \\
             -H "X-API-Key: your-api-key" \\
             -H "Authorization: Bearer eyJ..."
    """
    return SuccessResponse(
        success=True, message="User profile retrieved successfully", data=current_user
    )


@router.patch("/me", response_model=SuccessResponse[UserResponseSchema])
async def update_current_user(
    user_update: UserUpdateSchema,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
):
    """
    Update the authenticated user's profile.

    Only the fields sent are changed: an omitted field is left alone, an
    explicit null clears it. `username`, `is_active` and the password are not
    profile fields and are ignored if sent; the password has its own route.

    Args:
        user_update: Profile fields to change.
        current_user: The User the bearer token belongs to (injected).
        session: Database session.

    Returns:
        SuccessResponse[UserResponseSchema]: The updated profile.

    Raises:
        HTTPException: 409 when the new email or phone number belongs to another
            account; 422 for a malformed value; 500, logged, otherwise.

    Example:
        curl -X PATCH http://localhost:8000/api/users/me \\
             -H "X-API-Key: your-api-key" \\
             -H "Authorization: Bearer eyJ..." \\
             -H "Content-Type: application/json" \\
             -d '{"email": "new@example.com"}'
    """
    try:
        db_user = await user_service.update_user(session, current_user, user_update)
    except IdentifierTakenError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception:
        await session.rollback()
        logger.exception("Failed to update user")
        raise HTTPException(status_code=500, detail="Failed to update user")
    return SuccessResponse(
        success=True, message="Profile updated successfully", data=db_user
    )


@router.post("/me/change-password", response_model=SuccessResponse[None])
async def change_password(
    password_change: PasswordChangeSchema,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
):
    """
    Change the authenticated user's password.

    The current password is required, so a stolen token alone cannot lock the
    owner out. Existing tokens stay valid until they expire (tokens are
    stateless; see docs/known_issues.md).

    Args:
        password_change: Current and new password.
        current_user: The User the bearer token belongs to (injected).
        session: Database session.

    Returns:
        SuccessResponse[None]: Confirmation.

    Raises:
        HTTPException: 400 when the current password is wrong; 422 when the new
            one is shorter than 8 characters; 500, logged, otherwise.

    Example:
        curl -X POST http://localhost:8000/api/users/me/change-password \\
             -H "X-API-Key: your-api-key" \\
             -H "Authorization: Bearer eyJ..." \\
             -H "Content-Type: application/json" \\
             -d '{"current_password": "old", "new_password": "longer-new-one"}'
    """
    try:
        await user_service.change_user_password(session, current_user, password_change)
    except PasswordVerificationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        await session.rollback()
        logger.exception("Failed to change password")
        raise HTTPException(status_code=500, detail="Failed to change password")
    return SuccessResponse(
        success=True, message="Password changed successfully", data=None
    )


@router.delete("/me", response_model=SuccessResponse[None])
async def delete_current_user(
    body: UserDeleteSchema,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
):
    """
    Permanently delete the authenticated user's account.

    The password is required in the body, so a stolen token alone cannot
    destroy the account. The row is removed; every token for it is refused
    from the next request on. (A DELETE with a body is unusual but widely
    supported; a client that cannot send one may use a POST route instead.)

    Args:
        body: The account's current password.
        current_user: The User the bearer token belongs to (injected).
        session: Database session.

    Returns:
        SuccessResponse[None]: Confirmation.

    Raises:
        HTTPException: 400 when the password is wrong; 422 when it is missing;
            500, logged, otherwise.

    Example:
        curl -X DELETE http://localhost:8000/api/users/me \\
             -H "X-API-Key: your-api-key" \\
             -H "Authorization: Bearer eyJ..." \\
             -H "Content-Type: application/json" \\
             -d '{"password": "..."}'
    """
    try:
        await user_service.delete_user(session, current_user, body.password)
    except PasswordVerificationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        await session.rollback()
        logger.exception("Failed to delete user")
        raise HTTPException(status_code=500, detail="Failed to delete user account")
    return SuccessResponse(
        success=True, message="Account permanently deleted", data=None
    )
