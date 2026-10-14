"""
The rate limiter: budget headers, the 429, per-route counters. No database.
"""

import json
import time

from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from limits import parse

from basic_api.limiter import (
    RateLimitExceeded,
    limiter,
    rate_limit_exceeded_handler,
)


def test_rate_limit_response_uses_detail_and_retry_after():
    # Clients read "detail" like every other error, need to know how long to
    # wait, and get the budget headers with nothing left.
    reset_time = time.time() + 42
    exc = RateLimitExceeded(parse("10/minute"), reset_time)

    response = rate_limit_exceeded_handler(None, exc)  # type: ignore[arg-type]

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"
    assert response.headers["X-RateLimit-Limit"] == "10"
    assert response.headers["X-RateLimit-Remaining"] == "0"
    assert int(response.headers["X-RateLimit-Reset"]) >= int(reset_time)
    assert json.loads(response.body) == {
        "detail": "Too many requests. Try again in 60 seconds."
    }


def _app() -> FastAPI:
    # The same Limiter the app uses, on a throwaway app wired like main.py.
    # The routes take no request or response parameter: the dependency alone
    # counts the call and writes the headers.
    app = FastAPI()
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    @app.get("/limited", dependencies=[Depends(limiter.limit("3/minute"))])
    async def limited():
        return {"ok": True}

    @app.get("/other", dependencies=[Depends(limiter.limit("3/minute"))])
    async def other():
        return {"ok": True}

    return app


async def test_a_limited_route_reports_its_budget_in_headers():
    limiter.enabled = True
    limiter.reset()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=_app()), base_url="http://test"
        ) as client:
            first = await client.get("/limited")
            second = await client.get("/limited")
    finally:
        limiter.enabled = False
        limiter.reset()

    assert first.status_code == 200
    assert first.headers["X-RateLimit-Limit"] == "3"
    assert first.headers["X-RateLimit-Remaining"] == "2"
    assert second.headers["X-RateLimit-Remaining"] == "1"
    assert int(first.headers["X-RateLimit-Reset"]) > time.time()  # Unix time


async def test_the_request_over_the_limit_gets_a_429_and_other_routes_do_not():
    limiter.enabled = True
    limiter.reset()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=_app()), base_url="http://test"
        ) as client:
            statuses = [(await client.get("/limited")).status_code for _ in range(3)]
            refused = await client.get("/limited")
            other = await client.get("/other")
    finally:
        limiter.enabled = False
        limiter.reset()

    assert statuses == [200, 200, 200]
    assert refused.status_code == 429
    assert refused.headers["Retry-After"] == "60"
    assert refused.headers["X-RateLimit-Remaining"] == "0"
    assert refused.json()["detail"].startswith("Too many requests")
    # Counters are per route: the same limit on another route is untouched.
    assert other.status_code == 200
    assert other.headers["X-RateLimit-Remaining"] == "2"


async def test_a_disabled_limiter_counts_nothing_and_writes_no_headers():
    limiter.enabled = False
    limiter.reset()
    async with AsyncClient(
        transport=ASGITransport(app=_app()), base_url="http://test"
    ) as client:
        responses = [await client.get("/limited") for _ in range(5)]

    assert [r.status_code for r in responses] == [200] * 5
    assert "X-RateLimit-Limit" not in responses[0].headers
