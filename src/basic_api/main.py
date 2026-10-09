"""
FastAPI application entry point.

A starter: OAuth2 password flow with JWT bearer tokens over async PostgreSQL,
a client API key on the API routes, rate limits on the unauthenticated routes,
and a modular layout to build on. Configuration comes from config.py.

Authentication:
    POST /token with form fields `username` (a username, email or phone
    number) and `password`; send the returned token as
    "Authorization: Bearer <token>". Routes under /api also require the
    client API key in "X-API-Key". /, /health and /token need neither.

Usage:
    Development:
        uvicorn basic_api.main:app --reload --app-dir src

    Production:
        uvicorn basic_api.main:app --host 0.0.0.0 --port 8000 --app-dir src
"""

import logging
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Annotated

from fastapi import Depends, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from slowapi.errors import RateLimitExceeded
from starlette.middleware.body_limit import RequestBodyLimitMiddleware

from .auth import access_token_lifetime, authenticate_user, create_access_token
from .config import (
    APP_VERSION,
    CORS_HEADERS,
    CORS_METHODS,
    CORS_ORIGINS,
    ENABLE_DOCS,
    ENVIRONMENT,
    MAX_REQUEST_BODY_BYTES,
    ROOT_PATH,
)
from .database import engine, init_db, ping
from .dependencies import CurrentUserDep, SessionDep
from .exceptions import IdentifierTakenError, PasswordVerificationError
from .limiter import RATE_LIMIT_LOGIN, limiter, rate_limit_exceeded_handler
from .logging_config import configure_logging
from .request_id import REQUEST_ID_HEADER, RequestIdMiddleware
from .routers import auth, users
from .schemas.errors import error_responses
from .schemas.system import (
    BannerResponse,
    GreetingResponse,
    HealthResponse,
    TokenResponse,
)
from .security import verify_api_key

SERVICE_NAME = "basic-api"

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The listener thread that writes log lines runs for exactly as long as the
    # app does; leaving the block drains the queue, so the last lines are not
    # lost on shutdown.
    with configure_logging():
        logger.info("Starting %s %s (%s)", SERVICE_NAME, APP_VERSION, ENVIRONMENT)
        await init_db()
        yield
        # Close pooled connections on the way out instead of letting the process
        # drop them, which PostgreSQL logs as aborted connections.
        await engine.dispose()
        logger.info("Stopped %s", SERVICE_NAME)


app = FastAPI(
    title="Basic API",
    description="REST API starter with OAuth2 + JWT",
    version=APP_VERSION,
    root_path=ROOT_PATH,
    lifespan=lifespan,
    # Off in production unless ENABLE_DOCS says otherwise (config.docs_enabled).
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


def _domain_error(status_code: int):
    """A handler that turns a domain exception into {"detail": str(exc)}."""

    def handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return handler


# Domain exceptions from the services are mapped to status codes here, once,
# instead of in a try/except in every route. The services stay HTTP-free; a
# route only catches what it has to log.
app.add_exception_handler(IdentifierTakenError, _domain_error(409))
app.add_exception_handler(PasswordVerificationError, _domain_error(400))

# Middleware order: each add_middleware() wraps the ones before it, so the last
# added runs first. The body limit goes in first so that CORS, added after it,
# wraps it and a 413 still carries CORS headers for a browser client; the
# request id goes in last, outermost, so that every response has one, 413s and
# CORS preflights included.
# Starlette's own `max_body_size` parameter is not forwarded by FastAPI(), hence
# the middleware directly.
app.add_middleware(RequestBodyLimitMiddleware, max_body_size=MAX_REQUEST_BODY_BYTES)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=CORS_METHODS,
    allow_headers=CORS_HEADERS,
    # Let a browser client read the id off the response.
    expose_headers=[REQUEST_ID_HEADER],
)

app.add_middleware(RequestIdMiddleware)


@app.get("/", response_model=BannerResponse)
async def root():
    """
    Service banner. Public: needs neither API key nor token.

    Returns:
        dict: Service name, version, status and a hint on how to authenticate.
    """
    return {
        "message": "Basic API",
        "version": APP_VERSION,
        "status": "healthy",
        "authentication": "OAuth2 + JWT (POST /token to get access token)",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse, "description": "Database unreachable"}},
)
async def health_check():
    """
    Health check for monitoring. Public, so a monitor needs no credentials.

    Checks the database with a short-timeout SELECT 1, because an API whose
    database is down is not healthy however alive the process is.

    Returns:
        dict: {"status": "healthy", "service": ..., "database": "ok"} with 200,
            or {"status": "unhealthy", ..., "database": "unreachable"} with 503.
    """
    if not await ping():
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": SERVICE_NAME,
                "database": "unreachable",
            },
        )
    return {"status": "healthy", "service": SERVICE_NAME, "database": "ok"}


@app.post(
    "/token",
    response_model=TokenResponse,
    responses=error_responses(401, 403, 413, 429),
)
@limiter.limit(RATE_LIMIT_LOGIN)
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
    expires_delta: Annotated[
        timedelta | None,
        Query(
            description=(
                "Requested token lifetime, in seconds or as an ISO 8601 duration "
                "(e.g. P1D). Capped at JWT_MAX_ACCESS_TOKEN_EXPIRE_MINUTES; "
                "omitted, zero or negative gets JWT_ACCESS_TOKEN_EXPIRE_MINUTES."
            ),
        ),
    ] = None,
):
    """
    OAuth2 password flow. Public: no API key needed, which also lets Swagger's
    Authorize dialog log in. Rate-limited per client IP (RATE_LIMIT_LOGIN).

    `username` may be a username, an email address or a phone number.

    Args:
        request: Needed by the rate limiter (injected).
        form_data: OAuth2 password form with `username` and `password` fields.
        expires_delta: Requested token lifetime (query parameter); the server
            caps it, see access_token_lifetime.
        session: Database session.

    Returns:
        dict: Access token, granted lifetime and token type
            {
                "access_token": "eyJ...",
                "expires_in": 1800,
                "token_type": "bearer"
            }

    Raises:
        HTTPException: 401 for an unknown identifier or a wrong password, with
            one message for both; 403 for a disabled account; 429 over the
            rate limit, with a Retry-After header.

    Example:
        curl -X POST http://localhost:8000/token \\
             -H "Content-Type: application/x-www-form-urlencoded" \\
             -d "username=user@example.com&password=your-password"
    """
    user = await authenticate_user(session, form_data.username, form_data.password)
    lifetime = access_token_lifetime(expires_delta)
    token = create_access_token(data={"sub": str(user.id)}, expires_delta=lifetime)
    return {
        "access_token": token,
        "expires_in": int(lifetime.total_seconds()),
        "token_type": "bearer",
    }


@app.get(
    "/protected-example",
    response_model=GreetingResponse,
    responses=error_responses(401, 403),
)
async def protected_example(
    current_user: CurrentUserDep,
    api_key: Annotated[str, Depends(verify_api_key)],
):
    """
    Example of a route that needs both the client API key and a user token.
    Copy its signature to protect a new route the same way.

    Args:
        current_user: The User the bearer token belongs to (injected).
        api_key: The verified client API key (injected).

    Returns:
        dict: A greeting naming the authenticated user.

    Example:
        curl http://localhost:8000/protected-example \\
             -H "X-API-Key: your-api-key" \\
             -H "Authorization: Bearer eyJ..."
    """
    return {
        "message": f"Hello {current_user.username}! This is a protected endpoint.",
        "user": current_user.username,
    }


# Every route under /api needs the client API key; user routes add the bearer
# token through get_current_user themselves.
# Every route under /api needs the client API key and can answer 401 for it;
# user routes add the bearer token through get_current_user themselves and
# declare 403 where it applies.
app.include_router(
    auth.router,
    prefix="/api",
    dependencies=[Depends(verify_api_key)],
    responses=error_responses(401),
)
app.include_router(
    users.router,
    prefix="/api",
    dependencies=[Depends(verify_api_key)],
    responses=error_responses(401),
)
