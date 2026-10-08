"""
Response models for the routes outside the /api envelope.

Declaring them does two things: the OpenAPI document gets a schema for each
response (the token response had none), and FastAPI serialises the body with
pydantic-core instead of the slower generic encoder it uses for a bare dict.
"""

from pydantic import BaseModel, Field


class BannerResponse(BaseModel):
    """GET /: service name, version and how to authenticate."""

    message: str
    version: str
    status: str = Field(description='Always "healthy"; /health is the real check')
    authentication: str


class HealthResponse(BaseModel):
    """GET /health, with 200 or, when the database does not answer, 503."""

    status: str = Field(description='"healthy" or "unhealthy"')
    service: str
    database: str = Field(description='"ok" or "unreachable"')


class TokenResponse(BaseModel):
    """POST /token: the OAuth2 token response."""

    access_token: str
    expires_in: int = Field(description="Granted lifetime in seconds")
    token_type: str = Field(description='Always "bearer"')


class GreetingResponse(BaseModel):
    """GET /protected-example."""

    message: str
    user: str
