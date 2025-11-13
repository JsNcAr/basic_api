"""
Authentication utilities for OAuth2 + JWT.

This module provides functions for:
- Password verification using bcrypt
- JWT token creation and validation
- User authentication

For single admin user, credentials are stored in environment variables.
Easy to migrate to database when multiple users are needed.
"""

from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from fastapi import HTTPException, status
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

# Load and validate JWT settings
_value = os.getenv("JWT_SECRET_KEY")
if not _value:
    raise RuntimeError("JWT_SECRET_KEY environment variable is required")
JWT_SECRET_KEY: str = _value

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM") or "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30))

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a bcrypt hash.
    
    Uses bcrypt directly for compatibility with Python 3.13 and bcrypt 5.0.0.
    
    Args:
        plain_password: The plain text password to verify
        hashed_password: The bcrypt hash to verify against
        
    Returns:
        True if password matches, False otherwise
    """
    # Convert strings to bytes
    password_bytes = plain_password.encode('utf-8')
    hash_bytes = hashed_password.encode('utf-8')

    # Verify using bcrypt directly
    return bcrypt.checkpw(password_bytes, hash_bytes)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Uses bcrypt directly for compatibility with Python 3.13 and bcrypt 5.0.0.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Bcrypt hash of the password
        
    Example:
        >>> hash = get_password_hash("my-secure-password")
        >>> print(hash)
        $2b$12$...
    """
    # Convert to bytes
    password_bytes = password.encode('utf-8')

    # Generate salt and hash
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)

    # Return as string
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary of claims to encode in the token (e.g., {"sub": "username"})
        expires_delta: Optional custom expiration time. If not provided, uses default from settings.
        
    Returns:
        Encoded JWT token string
        
    Example:
        >>> token = create_access_token({"sub": "admin"})
        >>> print(token)
        eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)  # Default 15 minutes

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    # Encode JWT
    encoded_jwt = jwt.encode(
        to_encode,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )

    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT access token.
    
    Args:
        token: JWT token string to decode
        
    Returns:
        Dictionary of claims from the token
        
    Raises:
        HTTPException: If token is invalid or expired (401 Unauthorized)
    """

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def authenticate_user(username: str, password: str) -> bool:
    """
    Authenticate a user by verifying username and password.
    
    For single admin user: validates against credentials in environment variables.
    For multiple users: this function would query the database instead.
    
    Args:
        username: Username to authenticate
        password: Plain text password to verify
        
    Returns:
        True if authentication successful, False otherwise
    """

    admin_username = os.getenv("ADMIN_USERNAME") or "admin"
    admin_password_hash = os.getenv("ADMIN_PASSWORD_HASH")

    if not admin_password_hash:
        raise RuntimeError("ADMIN_PASSWORD_HASH environment variable is required")

    if username != admin_username:
        return False

    if not verify_password(password, admin_password_hash):
        return False

    return True