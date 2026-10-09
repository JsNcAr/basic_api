"""
API key verification.

The key identifies the client application, not a user: a key shipped inside a
mobile or browser app can be extracted from it. Treat it as a way to tell your
own clients from random traffic, and rely on per-user authentication and rate
limits for protection.
"""

import secrets
from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from .config import API_KEY

# A declared security scheme, so it appears in the OpenAPI document and the
# Swagger "Authorize" dialog can send it. auto_error=False lets this module
# answer a missing header itself, with the same status as a wrong one.
api_key_header = APIKeyHeader(
    name="X-API-Key", auto_error=False, description="Client API key"
)


async def verify_api_key(
    x_api_key: Annotated[str | None, Security(api_key_header)],
) -> str:
    """
    Dependency for routes that require the client API key.

    Args:
        x_api_key: Value of the X-API-Key header, or None when absent (injected).

    Returns:
        The key, so a route can depend on it like any other value.

    Raises:
        HTTPException: 401 when the header is missing or does not equal the
            configured key. (A missing API_KEY stops the app at startup, in
            config.py, so there is no runtime "not configured" case.)

    Example:
        @router.get("/things", dependencies=[Depends(verify_api_key)])
        async def list_things(): ...
    """
    # compare_digest: equal time whatever the first differing byte is.
    if not x_api_key or not secrets.compare_digest(
        x_api_key, API_KEY.get_secret_value()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return x_api_key
