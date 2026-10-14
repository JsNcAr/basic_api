"""
Rate limiting shared by the app and its routers.

Built on the `limits` library: a fixed window per client IP and per route,
counted in this process's memory. The Limiter lives in its own module because
main.py imports the routers; a router importing it from main.py would be a
circular import.

Limits are per client IP, as uvicorn sees it (behind a reverse proxy, make sure
uvicorn trusts the proxy's forwarded headers), and per process: with several
workers each keeps its own count, so the effective limit is multiplied.

A limited route declares `Depends(limiter.limit("10/minute"))`. The dependency
counts the request, writes X-RateLimit-Limit, X-RateLimit-Remaining and
X-RateLimit-Reset (Unix time) onto the response so a client can pace itself
before a 429, and raises RateLimitExceeded over the limit; main.py maps that to
the 429 built by rate_limit_exceeded_handler.
"""

import math
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from limits import RateLimitItem, parse_many
from limits.storage import MemoryStorage
from limits.strategies import FixedWindowRateLimiter

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


class RateLimitExceeded(Exception):
    """
    A request went over one of its route's limits.

    Attributes:
        limit: The limit that was hit.
        reset_time: Unix time at which that limit's window resets.
    """

    def __init__(self, limit: RateLimitItem, reset_time: float) -> None:
        super().__init__(f"rate limit exceeded: {limit}")
        self.limit = limit
        self.reset_time = reset_time


def client_address(request: Request) -> str:
    """
    Key requests by client IP.

    Args:
        request: The incoming request.

    Returns:
        The peer address uvicorn reports, or "unknown" when there is none (an
        in-process test client, for instance).
    """
    return request.client.host if request.client else "unknown"


def route_scope(request: Request) -> str:
    """
    Name the counter a request belongs to: its method and route path.

    The route's path template (`/api/users/`) rather than the request URL, so a
    route with path parameters still has one counter.

    Args:
        request: The incoming request, already matched to a route.

    Returns:
        A string such as "POST /api/users/".
    """
    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)
    return f"{request.method} {path}"


class Limiter:
    """
    Fixed-window counters per client and per route, in this process's memory.

    Attributes:
        enabled: False makes every limit a no-op that writes no headers. The
            test suite turns it off because every test client shares one IP.
        key_func: Maps a request to its client key; client_address by default.
    """

    def __init__(
        self,
        key_func: Callable[[Request], str] = client_address,
        *,
        enabled: bool = True,
    ) -> None:
        self.enabled = enabled
        self.key_func = key_func
        self._storage = MemoryStorage()
        self._strategy = FixedWindowRateLimiter(self._storage)

    def reset(self) -> None:
        """Forget every count."""
        self._storage.reset()

    def limit(self, value: str) -> Callable[[Request, Response], Awaitable[None]]:
        """
        Build the dependency that enforces `value` on the route declaring it.

        Args:
            value: One or more limits in `limits` syntax ("10/minute",
                "100/hour;1000/day"), each of which must hold.

        Returns:
            A dependency for the route's `dependencies=[Depends(...)]`. It
            raises RateLimitExceeded when a limit is hit; otherwise it writes
            the X-RateLimit headers of the limit with the least budget left.
        """
        items = parse_many(value)

        async def enforce(request: Request, response: Response) -> None:
            if not self.enabled:
                return
            key = self.key_func(request)
            scope = route_scope(request)
            for item in items:
                if not self._strategy.hit(item, key, scope):
                    stats = self._strategy.get_window_stats(item, key, scope)
                    raise RateLimitExceeded(item, stats.reset_time)
            item, stats = min(
                ((i, self._strategy.get_window_stats(i, key, scope)) for i in items),
                key=lambda pair: pair[1].remaining,
            )
            response.headers["X-RateLimit-Limit"] = str(item.amount)
            response.headers["X-RateLimit-Remaining"] = str(stats.remaining)
            response.headers["X-RateLimit-Reset"] = str(math.ceil(stats.reset_time))

        return enforce


limiter = Limiter()


def rate_limit_exceeded_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Answer a limit hit in the API's usual error shape, with a Retry-After.

    Clients read {"detail": ...} like every other error. The wait is the
    limit's window, the longest a client has to wait under the fixed-window
    strategy; the X-RateLimit headers say when the window actually resets.

    Args:
        request: The request that hit the limit.
        exc: The RateLimitExceeded raised by the limiter (typed as Exception
            because that is Starlette's handler signature).

    Returns:
        A 429 JSON response with a Retry-After header in seconds and the
        X-RateLimit headers with no budget left.
    """
    assert isinstance(exc, RateLimitExceeded)
    retry_after = exc.limit.get_expiry()
    return JSONResponse(
        status_code=429,
        content={"detail": f"Too many requests. Try again in {retry_after} seconds."},
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": str(exc.limit.amount),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(math.ceil(exc.reset_time)),
        },
    )
