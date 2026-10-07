"""
Rate limiting shared by the app and its routers.

The Limiter lives in its own module because main.py imports the routers; a
router importing it from main.py would be a circular import.

Limits are per client IP, as uvicorn sees it (behind a reverse proxy, make sure
uvicorn trusts the proxy's forwarded headers), and per process: with several
workers each keeps its own count, so the effective limit is multiplied.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from limits import parse_many
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import RATE_LIMIT_LOGIN, RATE_LIMIT_REGISTER

# Fail at startup on a malformed value, not on the first request it applies to.
for _name, _value in (
    ("RATE_LIMIT_LOGIN", RATE_LIMIT_LOGIN),
    ("RATE_LIMIT_REGISTER", RATE_LIMIT_REGISTER),
):
    try:
        parse_many(_value)
    except ValueError as e:
        raise RuntimeError(f"{_name}={_value!r} is not a valid rate limit: {e}")

limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Answer a limit hit in the API's usual error shape, with a Retry-After.

    slowapi's default handler returns {"error": ...}; clients read {"detail":
    ...} like every other error. The wait is the limit's window, the longest a
    client has to wait under the default fixed-window strategy.

    Args:
        request: The request that hit the limit.
        exc: The RateLimitExceeded raised by slowapi (typed as Exception
            because that is Starlette's handler signature).

    Returns:
        A 429 JSON response with a Retry-After header in seconds.
    """
    assert isinstance(exc, RateLimitExceeded)
    wrapper = exc.limit
    retry_after = wrapper.limit.get_expiry() if wrapper is not None else 60
    return JSONResponse(
        status_code=429,
        content={"detail": f"Too many requests. Try again in {retry_after} seconds."},
        headers={"Retry-After": str(retry_after)},
    )
