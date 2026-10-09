"""
The rate-limit error response and the budget headers. No database.
"""

import json
from types import SimpleNamespace

from fastapi import FastAPI, Request, Response
from httpx import ASGITransport, AsyncClient
from limits import parse
from slowapi.errors import RateLimitExceeded

from basic_api.limiter import limiter, rate_limit_exceeded_handler


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


async def test_a_limited_route_reports_its_budget_in_headers():
    # The same Limiter the app uses, on a throwaway app: the route returns a
    # plain object, so slowapi needs the `response: Response` parameter to
    # carry the headers (the reason the app's limited routes declare one).
    app = FastAPI()
    app.state.limiter = limiter

    @app.get("/limited")
    @limiter.limit("3/minute")
    async def limited(request: Request, response: Response):
        return {"ok": True}

    limiter.enabled = True
    limiter.reset()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            first = await client.get("/limited")
            second = await client.get("/limited")
    finally:
        limiter.enabled = False
        limiter.reset()

    assert first.headers["X-RateLimit-Limit"] == "3"
    assert first.headers["X-RateLimit-Remaining"] == "2"
    assert second.headers["X-RateLimit-Remaining"] == "1"
    assert float(first.headers["X-RateLimit-Reset"]) > 0  # Unix time
