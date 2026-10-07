"""
Login and token behaviour against real accounts. Database-backed; runs in CI.
"""

from datetime import timedelta

from basic_api import auth
from basic_api.auth import INVALID_CREDENTIALS_DETAIL, create_access_token


async def login(client, username, password, **params):
    return await client.post(
        "/token", params=params, data={"username": username, "password": password}
    )


async def test_unknown_user_and_wrong_password_are_indistinguishable(client, test_user):
    unknown = await login(client, "nobody", "testpassword123")
    wrong = await login(client, "testuser", "wrong-password")
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json() == {"detail": INVALID_CREDENTIALS_DETAIL}


async def test_login_accepts_the_email_as_identifier(client, test_user):
    response = await login(client, "test@example.com", "testpassword123")
    assert response.status_code == 200


async def test_a_disabled_account_is_refused_after_the_password_is_checked(
    client, test_user, session
):
    test_user.is_active = False
    session.add(test_user)
    await session.commit()

    response = await login(client, "testuser", "testpassword123")
    assert response.status_code == 403
    assert response.json()["detail"] == "This account is currently disabled"

    wrong = await login(client, "testuser", "wrong-password")
    assert wrong.status_code == 401  # a wrong password reveals nothing about state


async def test_token_lifetime_default_request_and_cap(client, test_user):
    default = await login(client, "testuser", "testpassword123")
    assert default.json()["expires_in"] == auth.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60

    two_hours = await login(client, "testuser", "testpassword123", expires_delta="PT2H")
    assert two_hours.json()["expires_in"] == 2 * 60 * 60

    a_year = await login(client, "testuser", "testpassword123", expires_delta="P365D")
    maximum = timedelta(minutes=auth.JWT_MAX_ACCESS_TOKEN_EXPIRE_MINUTES)
    assert a_year.json()["expires_in"] == int(maximum.total_seconds())


async def test_a_deleted_users_token_stops_working_at_once(
    client, auth_headers, test_user, session
):
    await session.delete(test_user)
    await session.commit()

    response = await client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "User not found"


async def test_a_disabled_users_token_stops_working_at_once(
    client, auth_headers, test_user, session
):
    test_user.is_active = False
    session.add(test_user)
    await session.commit()

    response = await client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 403


async def test_a_token_whose_subject_is_not_an_id_is_refused(client):
    token = create_access_token(data={"sub": "testuser"})
    response = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"
