"""
FastAPI application main entry point.

A basic FastAPI application structure providing OAuth2 + JWT authentication
over an async PostgreSQL backend, intended as a starting point for new APIs.

Authentication:
    OAuth2 password flow with JWT bearer tokens.
    Get a token: POST /token with an identifier, its type, and a password.
    Use the token: send "Authorization: Bearer <token>" on subsequent requests.

Usage:
    Development:
        uvicorn basic_api.main:app --reload --app-dir src

    Production:
        uvicorn basic_api.main:app --host 0.0.0.0 --port 8000 --app-dir src
"""

from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from .auth import authenticate_user, create_access_token
from .dependencies import get_current_user, get_session
from sqlmodel.ext.asyncio.session import AsyncSession

from .routers import auth, users
from contextlib import asynccontextmanager
from .database import init_db
from .security import verify_api_key

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

# Create FastAPI app
app = FastAPI(
    title="Basic API",
    description="REST API starter with OAuth2 + JWT",
    version="0.116.0",
    # If deploying behind a reverse proxy under a subpath, pass
    # root_path="/your-prefix" here or via `uvicorn --root-path`.
    lifespan=lifespan,
    dependencies=[Depends(verify_api_key)]
)

# Get settings for CORS configuration

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "message": "Basic API",
        "version": "0.1.0",
        "status": "healthy",
        "authentication": "OAuth2 + JWT (POST /token to get access token)"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "leads-frontend-api"
    }


@app.post("/token")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: AsyncSession = Depends(get_session)
):
    """
    OAuth2 compatible token login endpoint.
    
    Get an access token by providing username and password.
    The token should be included in subsequent requests as:
    `Authorization: Bearer <token>`
    
    Args:
        form_data: OAuth2 password form with username and password fields
        session: Database session
        
    Returns:
        dict: Access token and token type
            {
                "access_token": "eyJ...",
                "token_type": "bearer"
            }
            
    Raises:
        HTTPException: 401 if credentials are invalid
        
    Example:
        curl -X POST http://localhost:8000/token \\
             -H "Content-Type: application/x-www-form-urlencoded" \\
             -d "username=admin&password=your-password"
    """
    # Authenticate user
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = create_access_token(data={"sub": user.username})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.get("/protected-example")
async def protected_example(
    current_user: Annotated[str, Depends(get_current_user)]
):
    """
    Example of a protected endpoint that requires authentication.
    
    This endpoint demonstrates how to protect routes with JWT authentication.
    The `current_user` dependency will validate the JWT token and return the username.
    
    Args:
        current_user: Username extracted from JWT token (injected)
        
    Returns:
        dict: Message with authenticated username
        
    Example:
        curl http://localhost:8000/protected-example \\
             -H "Authorization: Bearer eyJ..."
    """
    return {
        "message": f"Hello {current_user}! This is a protected endpoint.",
        "user": current_user
    }



# Include implemented routers

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")