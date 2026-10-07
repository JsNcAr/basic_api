"""
The routes that exist today, as they behave today. Database-backed; runs in CI.
"""


async def test_health_answers_with_the_api_key(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


async def test_login_returns_a_bearer_token(client, test_user):
    response = await client.post(
        "/token", data={"username": "testuser", "password": "testpassword123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


async def test_login_with_a_wrong_password_is_refused(client, test_user):
    response = await client.post(
        "/token", data={"username": "testuser", "password": "nope"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


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


async def test_auth_me_returns_the_token_owner(client, auth_headers):
    response = await client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["username"] == "testuser"
