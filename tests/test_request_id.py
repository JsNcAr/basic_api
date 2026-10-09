"""
X-Request-ID on responses and in the request context. No database: GET / and
a bare ASGI app are enough.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from basic_api.logging_config import request_id_var
from basic_api.main import app
from basic_api.request_id import (
    REQUEST_ID_HEADER,
    RequestIdMiddleware,
    resolve_request_id,
)


def bare_client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_every_response_carries_a_generated_uuid7():
    async with bare_client() as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert uuid.UUID(response.headers[REQUEST_ID_HEADER]).version == 7


async def test_an_acceptable_supplied_id_is_echoed():
    async with bare_client() as client:
        response = await client.get("/", headers={REQUEST_ID_HEADER: "gw-42.a_b"})
    assert response.headers[REQUEST_ID_HEADER] == "gw-42.a_b"


@pytest.mark.parametrize("bad", ["", "x" * 129, "has space", "new\nline", "a;b"])
def test_an_unacceptable_supplied_id_is_replaced(bad):
    resolved = resolve_request_id(bad)
    assert resolved != bad
    assert uuid.UUID(resolved).version == 7


def test_none_gets_a_generated_id():
    assert uuid.UUID(resolve_request_id(None)).version == 7


async def test_the_context_variable_is_set_during_the_call_and_reset_after():
    seen = {}

    async def inner(scope, receive, send):
        seen["id"] = request_id_var.get()
        raise RuntimeError("route failed")

    middleware = RequestIdMiddleware(inner)
    scope = {"type": "http", "headers": [(b"x-request-id", b"ctx-1")]}

    async def receive():
        return {"type": "http.request"}

    async def send(message):
        pass

    with pytest.raises(RuntimeError):
        await middleware(scope, receive, send)
    assert seen["id"] == "ctx-1"
    assert request_id_var.get() is None
