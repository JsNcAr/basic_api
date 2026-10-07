"""
FastAPI application entry point.

A starter: OAuth2 password flow with JWT bearer tokens over async PostgreSQL,
a client API key on the API routes, and a modular layout to build on.

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

from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession

from .auth import access_token_lifetime, authenticate_user, create_access_token
from .database import get_session, init_db
from .dependencies import get_current_user
from .routers import auth, users
from .schemas.user import User
from .security import verify_api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Basic API",
    description="REST API starter with OAuth2 + JWT",
    version="0.116.0",
    # If deploying behind a reverse proxy under a subpath, pass
    # root_path="/your-prefix" here or via `uvicorn --root-path`.
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """
    Service banner. Public: needs neither API key nor token.

    Returns:
        dict: Service name, version, status and a hint on how to authenticate.
    """
    return {
        "message": "Basic API",
        "version": "0.1.0",
        "status": "healthy",
        "authentication": "OAuth2 + JWT (POST /token to get access token)",
    }


@app.get("/health")
async def health_check():
    """
    Health check for monitoring. Public, so a monitor needs no credentials.

    Returns:
        dict: {"status": "healthy", "service": <name>}
    """
    return {"status": "healthy", "service": "leads-frontend-api"}


@app.post("/token")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    expires_delta: Optional[timedelta] = Query(
        default=None,
        description=(
            "Requested token lifetime, in seconds or as an ISO 8601 duration "
            "(e.g. P1D). Capped at JWT_MAX_ACCESS_TOKEN_EXPIRE_MINUTES; omitted, "
            "zero or negative gets JWT_ACCESS_TOKEN_EXPIRE_MINUTES."
        ),
    ),
    session: AsyncSession = Depends(get_session),
):
    """
    OAuth2 password flow. Public: no API key needed, which also lets Swagger's
    Authorize dialog log in.

    `username` may be a username, an email address or a phone number.

    Args:
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
            one message for both; 403 for a disabled account.

    Example:
        curl -X POST http://localhost:8000/token \
             -H "Content-Type: application/x-www-form-urlencoded" \
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


@app.get("/protected-example")
async def protected_example(
    current_user: Annotated[User, Depends(get_current_user)],
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
        curl http://localhost:8000/protected-example \
             -H "X-API-Key: your-api-key" \
             -H "Authorization: Bearer eyJ..."
    """
    return {
        "message": f"Hello {current_user.username}! This is a protected endpoint.",
        "user": current_user.username,
    }


# Every route under /api needs the client API key; user routes add the bearer
# token through get_current_user themselves.
app.include_router(auth.router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(users.router, prefix="/api", dependencies=[Depends(verify_api_key)])
