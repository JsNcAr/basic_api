"""
A request id on every response and every log line.

The client may send its own in `X-Request-ID` (a gateway usually does); it is
kept when it is 1 to 128 characters of letters, digits, dot, underscore or
hyphen, and replaced otherwise so that a log line never carries arbitrary
input. Without one, the API generates a UUIDv7 (Python 3.14), which sorts by
time, so ids in a log are in request order.

Pure ASGI middleware, not BaseHTTPMiddleware: it costs nothing per request,
works with streaming responses, and the context variable it sets is visible to
the route and to everything the route awaits.
"""

import re
import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .logging_config import request_id_var

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")


def resolve_request_id(supplied: str | None) -> str:
    """
    The id a request gets: the supplied one when acceptable, else a new UUIDv7.

    Args:
        supplied: Value of the incoming X-Request-ID header, or None.

    Returns:
        The id to use for the request.
    """
    if supplied is not None and _VALID_REQUEST_ID.fullmatch(supplied):
        return supplied
    return str(uuid.uuid7())


class RequestIdMiddleware:
    """
    Set `request_id_var` for the request and echo the id on the response.

    Args:
        app: The ASGI application to wrap.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = resolve_request_id(Headers(scope=scope).get(REQUEST_ID_HEADER))

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message).append(REQUEST_ID_HEADER, request_id)
            await send(message)

        token = request_id_var.set(request_id)
        try:
            await self.app(scope, receive, send_with_id)
        finally:
            request_id_var.reset(token)
