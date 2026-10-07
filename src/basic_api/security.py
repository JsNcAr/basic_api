"""
API key verification.

The key identifies the client application, not a user: a key shipped inside a
mobile or browser app can be extracted from it. Treat it as a way to tell your
own clients from random traffic, and rely on per-user authentication and rate
limits for protection.
"""

import os
import secrets

from dotenv import load_dotenv
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

load_dotenv()

API_KEY = os.getenv("API_KEY")

# A declared security scheme, so it appears in the OpenAPI document and the
# Swagger "Authorize" dialog can send it. auto_error=False lets this module
# answer a missing header itself, with the same status as a wrong one.
api_key_header = APIKeyHeader(
    name="X-API-Key", auto_error=False, description="Client API key"
)


async def verify_api_key(x_api_key: str | None = Security(api_key_header)) -> str:
    """
    Dependency for routes that require the client API key.

    Raises:
        HTTPException 500: no key configured on the server (fail closed).
        HTTPException 401: header missing or not equal to the configured key.
    """
    if not API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key not configured on server",
        )
    # compare_digest: equal time whatever the first differing byte is.
    if not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return x_api_key
