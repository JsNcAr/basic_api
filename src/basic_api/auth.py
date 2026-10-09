"""
Authentication utilities for OAuth2 + JWT.

- Password hashing and verification with bcrypt over a SHA-256 pre-hash
- JWT creation and validation
- User authentication that takes the same time whether or not the user exists

Settings come from config.py, which validates them at import: a missing or
weak secret, an algorithm outside the HMAC family, or too few bcrypt rounds stop
the process before it can serve a request with a bad configuration.
"""

import asyncio
import hashlib
import logging
import uuid
from datetime import timedelta

import bcrypt
from fastapi import HTTPException, status
import jwt
from jwt import PyJWTError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .config import (
    BCRYPT_ROUNDS,
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_MAX_ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_SECRET_KEY,
)
from .schemas.user import User
from .utils import utc_now

logger = logging.getLogger(__name__)

# One message for every credential failure, so a caller cannot tell an unknown
# account from a wrong password.
INVALID_CREDENTIALS_DETAIL = "Incorrect username or password"
INVALID_TOKEN_DETAIL = "Could not validate credentials"


def _prehash(password: str) -> bytes:
    """
    Pre-hash a password with SHA-256 before bcrypt.

    bcrypt reads at most 72 bytes of input; the hex digest is always 64, so a
    password of any length is hashed in full.

    Args:
        password: Plain text password.

    Returns:
        The 64-byte hex digest, encoded for bcrypt.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest().encode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a stored bcrypt hash.

    A malformed stored hash also verifies as False: bcrypt raises ValueError on
    one, and a boolean here keeps the login path answering 401 rather than 500.

    Args:
        plain_password: The password as the user typed it.
        hashed_password: The bcrypt hash stored for the account.

    Returns:
        True if the password matches, False if it does not or the hash is invalid.

    Example:
        >>> verify_password("my-password", get_password_hash("my-password"))
        True
    """
    try:
        return bcrypt.checkpw(_prehash(plain_password), hashed_password.encode("utf-8"))
    except ValueError, TypeError:
        return False


async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
    """
    verify_password in a worker thread.

    bcrypt takes about 250 ms at 12 rounds; running it on the event loop would
    stall every other request for that long.

    Args:
        plain_password: The password as the user typed it.
        hashed_password: The bcrypt hash stored for the account.

    Returns:
        True if the password matches, False otherwise.
    """
    return await asyncio.to_thread(verify_password, plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password with bcrypt at BCRYPT_ROUNDS over the SHA-256 pre-hash.

    Args:
        password: Plain text password.

    Returns:
        The bcrypt hash as a string, ready to store.

    Example:
        >>> get_password_hash("my-password")
        '$2b$12$...'
    """
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(_prehash(password), salt).decode("utf-8")


async def get_password_hash_async(password: str) -> str:
    """
    get_password_hash in a worker thread, for the same reason as
    verify_password_async.

    Args:
        password: Plain text password.

    Returns:
        The bcrypt hash as a string.
    """
    return await asyncio.to_thread(get_password_hash, password)


# A real hash to verify against when the account does not exist, so that path
# costs the same as a real verification and timing cannot reveal which it was.
_DUMMY_PASSWORD_HASH: str = get_password_hash("_constant_time_sentinel_")


def access_token_lifetime(requested: timedelta | None = None) -> timedelta:
    """
    The lifetime a login token actually gets.

    The client may ask; the server decides. No request, or a zero or negative
    one, gets the default. Anything above the maximum is capped.

    Args:
        requested: The lifetime the client asked for, or None.

    Returns:
        The lifetime to grant, between the default and the configured maximum.

    Example:
        >>> access_token_lifetime(timedelta(days=365)) == timedelta(days=7)
        True
    """
    default = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    maximum = timedelta(minutes=JWT_MAX_ACCESS_TOKEN_EXPIRE_MINUTES)
    if requested is None or requested <= timedelta(0):
        return default
    return min(requested, maximum)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a signed JWT with the given claims plus `iat` and `exp`.

    `data` must carry `sub`, the user's UUID as a string. The id rather than
    the username, because a username can be released by a deletion and taken
    by a new account; an id never comes back.

    Args:
        data: Claims to encode, including "sub".
        expires_delta: Lifetime of the token; the configured default if None.

    Returns:
        The encoded JWT.

    Example:
        >>> create_access_token({"sub": "42"})
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    """
    now = utc_now()
    lifetime = expires_delta or timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {**data, "iat": now, "exp": now + lifetime}
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT, returning its claims.

    Args:
        token: The encoded JWT from the Authorization header.

    Returns:
        The token's claims.

    Raises:
        HTTPException: 401 with one fixed message for every failure. The reason
            (expired, bad signature, malformed) goes to the log, not to the
            caller, so it cannot be used to probe the server.
    """
    try:
        return jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            # PyJWT's own key-length rule as an error, not a warning: a second
            # line behind the startup check in config.py, in case a key ever
            # reaches here another way.
            options={"enforce_minimum_key_length": True},
        )
    except PyJWTError as e:
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

    Args:
        session: Database session.
        identifier: Username, email address or phone number.
        password: Plain text password.

    Returns:
        The authenticated User.

    Raises:
        HTTPException: 401 for an unknown identifier or a wrong password, with
            the same message for both; 403 when the credentials are correct but
            the account is disabled, raised only after the password checked out.
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


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    """
    Load a user by primary key.

    Args:
        session: Database session.
        user_id: The user's UUID, as carried in the token subject.

    Returns:
        The User, or None if no row has that id.
    """
    return await session.get(User, user_id)
