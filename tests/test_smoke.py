"""
The routes as they behave now. Database-backed; runs in CI.
"""

from httpx import ASGITransport, AsyncClient

from basic_api.auth import INVALID_CREDENTIALS_DETAIL
from basic_api.main import app


def bare_client():
    """A client that sends no API key: what a monitor or a login form looks like."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_health_needs_no_credentials():
    async with bare_client() as bare:
        response = await bare.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


async def test_login_returns_a_bearer_token_without_an_api_key(client, test_user):
    async with bare_client() as bare:
        response = await bare.post(
            "/token", data={"username": "testuser", "password": "testpassword123"}
        )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0


async def test_login_with_a_wrong_password_is_refused(client, test_user):
    response = await client.post(
        "/token", data={"username": "testuser", "password": "nope"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == INVALID_CREDENTIALS_DETAIL


async def test_create_user_returns_201_without_the_hash(client):
    response = await client.post(
        "/api/users/",
        json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "strongPassword123!",
        },
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["username"] == "newuser"
    assert "hashed_password" not in data


async def test_auth_me_returns_the_stored_user(client, auth_headers, test_user):
    response = await client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == test_user.id
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "role" not in data
