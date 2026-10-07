"""
The rate-limit error response. No database.
"""

import json
from types import SimpleNamespace

from limits import parse
from slowapi.errors import RateLimitExceeded

from basic_api.limiter import rate_limit_exceeded_handler


def test_rate_limit_response_uses_detail_and_retry_after():
    # slowapi's own handler answers {"error": ...}; clients read "detail" like
    # every other error, and need to know how long to wait.
    exc = RateLimitExceeded(
        SimpleNamespace(limit=parse("10/minute"), error_message=None)
    )

    response = rate_limit_exceeded_handler(None, exc)  # type: ignore[arg-type]

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"
    assert json.loads(response.body) == {
        "detail": "Too many requests. Try again in 60 seconds."
    }
