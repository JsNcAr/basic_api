import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..auth import get_password_hash_async
from ..database import get_session
from ..limiter import RATE_LIMIT_REGISTER, limiter
from ..schemas import SuccessResponse
from ..schemas.user import User, UserCreateSchema, UserResponseSchema

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
            email or phone); a 409 with a generic message if two registrations
            race past the checks and the database's unique constraint decides;
            500, logged, for anything else; 429 over the rate limit, with a
            Retry-After header. The response never carries the database's
            error text.

    Example:
        curl -X POST http://localhost:8000/api/users/ \
             -H "X-API-Key: your-api-key" \
             -H "Content-Type: application/json" \
             -d '{"username": "alice", "email": "alice@example.com", "password": "..."}'
    """
    taken = (
        (User.username, user_create.username, "Username is already taken"),
        (User.email, user_create.email, "Email address is already registered"),
        (
            User.phone_number,
            user_create.phone_number,
            "Phone number is already associated with an account",
        ),
    )
    for column, value, message in taken:
        if value is None:
            continue
        existing = await session.exec(select(User).where(col(column) == value))
        if existing.first():
            raise HTTPException(status_code=409, detail=message)

    hashed_password = await get_password_hash_async(user_create.password)
    db_user = User(
        **user_create.model_dump(exclude={"password"}), hashed_password=hashed_password
    )
    try:
        session.add(db_user)
        await session.commit()
        await session.refresh(db_user)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="A user with this username, email, or phone number already exists",
        )
    except Exception:
        await session.rollback()
        logger.exception("Failed to create user")
        raise HTTPException(status_code=500, detail="Failed to create user")

    return SuccessResponse(
        success=True, message="User created successfully", data=db_user
    )
