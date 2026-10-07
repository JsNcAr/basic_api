"""
Which routes need the client API key, and what a missing or wrong key gets.
Database-backed; runs in CI.
"""

from tests.test_smoke import bare_client


async def test_public_routes_need_no_api_key(client, test_user):
    async with bare_client() as bare:
        assert (await bare.get("/")).status_code == 200
        assert (await bare.get("/health")).status_code == 200
        login = await bare.post(
            "/token", data={"username": "testuser", "password": "testpassword123"}
        )
    assert login.status_code == 200


async def test_api_routes_refuse_a_missing_key(client, auth_headers):
    async with bare_client() as bare:
        response = await bare.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


async def test_api_routes_refuse_a_wrong_key(client, auth_headers):
    response = await client.get(
        "/api/auth/me", headers={**auth_headers, "X-API-Key": "not-the-key"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


async def test_protected_example_needs_both_key_and_token(client, auth_headers):
    async with bare_client() as bare:
        no_key = await bare.get("/protected-example", headers=auth_headers)
    assert no_key.status_code == 401

    no_token = await client.get("/protected-example")
    assert no_token.status_code == 401
    assert no_token.json()["detail"] == "Not authenticated"

    both = await client.get("/protected-example", headers=auth_headers)
    assert both.status_code == 200
    assert "testuser" in both.json()["message"]
