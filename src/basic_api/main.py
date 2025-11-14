"""
FastAPI application main entry point.

This is a basic FastAPI application structure for the leads_frontend pipeline.
The app provides REST API endpoints for the 4 main workflows:
- Refresh: Compute metrics and update controller status
- Retrieve: Search Apollo API for leads
- Enrich: Enrich people with email data and AI scripts
- Campaign: Add prospects to Snov campaigns

Authentication:
    OAuth2 + JWT authentication with single admin user.
    Get token: POST /token with username and password
    Use token: Include "Authorization: Bearer <token>" header in requests

Usage:
    Development:
        uvicorn leads_frontend.api.main:app --reload
    
    Production:
        uvicorn leads_frontend.api.main:app --host 0.0.0.0 --port 8000
"""

from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from .auth import authenticate_user, create_access_token
from .dependencies import get_current_user

from .routers import auth, users

# Create FastAPI app
app = FastAPI(
    title="Leads Frontend API",
    description="REST API for lead generation pipeline workflows with OAuth2 + JWT authentication",
    version="0.116.0",
    root_path="/back"  # For running behind a reverse proxy
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
        "message": "Korvyn",
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
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    """
    OAuth2 compatible token login endpoint.
    
    Get an access token by providing username and password.
    The token should be included in subsequent requests as:
    `Authorization: Bearer <token>`
    
    Args:
        form_data: OAuth2 password form with username and password fields
        
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
    if not authenticate_user(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = create_access_token(data={"sub": form_data.username})

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