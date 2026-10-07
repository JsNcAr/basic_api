"""
Authentication utilities for OAuth2 + JWT.

- Password hashing and verification with bcrypt over a SHA-256 pre-hash
- JWT creation and validation
- User authentication that takes the same time whether or not the user exists

Settings are read and validated once, at import: a missing or weak secret, an
algorithm outside the HMAC family, or too few bcrypt rounds stop the process
before it can serve a request with a bad configuration.
"""

import asyncio
import hashlib
import logging
import os
from datetime import timedelta
from typing import Optional

import bcrypt
from dotenv import load_dotenv
from fastapi import HTTPException, status
from jose import jwt
from jose.exceptions import JOSEError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .schemas.user import User
from .utils import utc_now

load_dotenv()

logger = logging.getLogger(__name__)

# 32 bytes is the HMAC key size the HS256 family is specified for; a shorter
# secret weakens every token at once.
_MIN_SECRET_BYTES = 32
_ALLOWED_ALGORITHMS = ("HS256", "HS384", "HS512")
_MIN_BCRYPT_ROUNDS = 12

_secret = os.getenv("JWT_SECRET_KEY")
if not _secret:
    raise RuntimeError("JWT_SECRET_KEY environment variable is required")
if len(_secret.encode("utf-8")) < _MIN_SECRET_BYTES:
    raise RuntimeError(
        f"JWT_SECRET_KEY must be at least {_MIN_SECRET_BYTES} bytes. Generate one "
        "with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    )
JWT_SECRET_KEY: str = _secret

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM") or "HS256"
if JWT_ALGORITHM not in _ALLOWED_ALGORITHMS:
    raise RuntimeError(
        f"JWT_ALGORITHM={JWT_ALGORITHM!r} is not one of "
        + ", ".join(_ALLOWED_ALGORITHMS)
    )

JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30))
# Longest lifetime a client may request at login (default 7 days).
JWT_MAX_ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("JWT_MAX_ACCESS_TOKEN_EXPIRE_MINUTES", 7 * 24 * 60)
)
if JWT_MAX_ACCESS_TOKEN_EXPIRE_MINUTES < JWT_ACCESS_TOKEN_EXPIRE_MINUTES:
    raise RuntimeError(
        "JWT_MAX_ACCESS_TOKEN_EXPIRE_MINUTES must be at least "
        "JWT_ACCESS_TOKEN_EXPIRE_MINUTES."
    )

BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", _MIN_BCRYPT_ROUNDS))
if BCRYPT_ROUNDS < _MIN_BCRYPT_ROUNDS:
    raise RuntimeError(
        f"BCRYPT_ROUNDS={BCRYPT_ROUNDS} is below the minimum of {_MIN_BCRYPT_ROUNDS}."
    )

# One message for every credential failure, so a caller cannot tell an unknown
# account from a wrong password.
INVALID_CREDENTIALS_DETAIL = "Incorrect username or password"
INVALID_TOKEN_DETAIL = "Could not validate credentials"


def _prehash(password: str) -> bytes:
    """SHA-256 the password first so bcrypt always sees 64 bytes, never 72+."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest().encode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a stored bcrypt hash.

    Returns False for a wrong password and also for a malformed stored hash:
    bcrypt raises ValueError on one, and a boolean here keeps the login path
    answering 401 rather than 500.
    """
    try:
        return bcrypt.checkpw(_prehash(plain_password), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
    """verify_password off the event loop: bcrypt takes ~250 ms at 12 rounds."""
    return await asyncio.to_thread(verify_password, plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password with bcrypt at BCRYPT_ROUNDS over the SHA-256 pre-hash."""
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(_prehash(password), salt).decode("utf-8")


async def get_password_hash_async(password: str) -> str:
    """get_password_hash off the event loop."""
    return await asyncio.to_thread(get_password_hash, password)


# A real hash to verify against when the account does not exist, so that path
# costs the same as a real verification and timing cannot reveal which it was.
_DUMMY_PASSWORD_HASH: str = get_password_hash("_constant_time_sentinel_")


def access_token_lifetime(requested: Optional[timedelta] = None) -> timedelta:
    """
    The lifetime a login token actually gets.

    The client may ask; the server decides. No request, or a zero or negative
    one, gets the default. Anything above the maximum is capped.
    """
    default = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    maximum = timedelta(minutes=JWT_MAX_ACCESS_TOKEN_EXPIRE_MINUTES)
    if requested is None or requested <= timedelta(0):
        return default
    return min(requested, maximum)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT with the given claims plus `iat` and `exp`.

    `data` must carry `sub`, the user's id as a string. The id rather than the
    username, because a username can be released by a deletion and taken by a
    new account; an id never comes back.
    """
    now = utc_now()
    lifetime = expires_delta or timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {**data, "iat": now, "exp": now + lifetime}
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT, returning its claims.

    Raises:
        HTTPException 401 with one fixed message for every failure. The reason
        (expired, bad signature, malformed) goes to the log, not to the caller.
    """
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JOSEError as e:
        logger.debug("Rejected token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_TOKEN_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )


async def authenticate_user(
    session: AsyncSession, identifier: str, password: str
) -> User:
    """
    Authenticate by username, email or phone number plus password.

    Takes the same time whether or not the identifier matches an account: the
    password is always verified, against the account's hash or the sentinel.

    Raises:
        HTTPException 401: unknown identifier or wrong password, same message.
        HTTPException 403: credentials correct but the account is disabled.
    """
    statement = select(User).where(
        (User.username == identifier)
        | (User.email == identifier)
        | (User.phone_number == identifier)
    )
    user = (await session.exec(statement)).first()

    target_hash = user.hashed_password if user else _DUMMY_PASSWORD_HASH
    is_valid = await verify_password_async(password, target_hash)

    if user is None or not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is currently disabled",
        )
    return user


async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
    """The user with this id, or None."""
    return await session.get(User, user_id)
