"""
FastAPI dependencies for authentication.
"""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel.ext.asyncio.session import AsyncSession

from .auth import INVALID_TOKEN_DETAIL, decode_access_token, get_user_by_id
from .database import get_session
from .schemas.user import User

# tokenUrl is where clients obtain tokens; Swagger's Authorize dialog uses it.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Dependency aliases: one token per dependency in a route signature, the style
# FastAPI's documentation recommends. CurrentUserDep is defined below
# get_current_user.
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: SessionDep,
) -> User:
    """
    The user the bearer token belongs to, loaded from the database.

    Loading the user on every request is what makes deletion and deactivation
    take effect at once, instead of when the token expires. The subject claim
    is the user's UUID, so a username released by a deletion and taken by a new
    account can never make an old token resolve to the new user.

    Args:
        token: Bearer token from the Authorization header (injected).
        session: Database session (injected).

    Returns:
        The User the token belongs to.

    Raises:
        HTTPException: 401 when the token is invalid, its subject is not an id,
            or the user no longer exists; 403 when the user is disabled.

    Example:
        @router.get("/mine")
        async def mine(current_user: CurrentUserDep):
            return {"username": current_user.username}
    """
    payload = decode_access_token(token)
    subject = payload.get("sub")
    try:
        user_id = uuid.UUID(subject) if subject is not None else None
    except TypeError, ValueError, AttributeError:
        user_id = None
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_TOKEN_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await get_user_by_id(session, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is currently disabled",
        )
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
