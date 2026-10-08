"""
The authenticated user's own account: read, update, change password, delete.
Database-backed; runs in CI.
"""

from basic_api.auth import INVALID_CREDENTIALS_DETAIL

ME = "/api/users/me"


async def login(client, username, password):
    return await client.post(
        "/token", data={"username": username, "password": password}
    )


async def test_read_me_returns_the_profile_without_the_hash(
    client, auth_headers, test_user
):
    response = await client.get(ME, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(test_user.id)
    assert data["username"] == "testuser"
    assert "hashed_password" not in data


async def test_patch_me_changes_only_the_fields_sent(client, auth_headers):
    response = await client.patch(
        ME, headers=auth_headers, json={"phone_number": "+15550177"}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["phone_number"] == "+15550177"
    assert data["email"] == "test@example.com"  # untouched

    again = await client.get(ME, headers=auth_headers)
    assert again.json()["data"]["phone_number"] == "+15550177"


async def test_patch_me_with_null_clears_a_field(client, auth_headers):
    response = await client.patch(ME, headers=auth_headers, json={"email": None})
    assert response.status_code == 200
    assert response.json()["data"]["email"] is None


async def test_patch_me_normalises_the_picture_url(client, auth_headers):
    response = await client.patch(
        ME,
        headers=auth_headers,
        json={"profile_picture_url": "https://example.com/p.png"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["profile_picture_url"] == "https://example.com/p.png"


async def test_patch_me_refuses_another_accounts_email(
    client, auth_headers, second_user
):
    response = await client.patch(
        ME, headers=auth_headers, json={"email": second_user.email}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Email address is already registered"


async def test_patch_me_keeping_my_own_email_is_not_a_conflict(client, auth_headers):
    response = await client.patch(
        ME, headers=auth_headers, json={"email": "test@example.com"}
    )
    assert response.status_code == 200


async def test_patch_me_ignores_fields_a_user_may_not_change(client, auth_headers):
    response = await client.patch(
        ME,
        headers=auth_headers,
        json={"is_active": False, "username": "hacker", "password": "newpassword1"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["is_active"] is True
    assert data["username"] == "testuser"
    assert (await login(client, "testuser", "testpassword123")).status_code == 200


async def test_change_password_requires_the_current_one(client, auth_headers):
    response = await client.post(
        f"{ME}/change-password",
        headers=auth_headers,
        json={"current_password": "wrong", "new_password": "brandNewPassword1"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect current password"


async def test_change_password_rejects_a_short_new_password(client, auth_headers):
    response = await client.post(
        f"{ME}/change-password",
        headers=auth_headers,
        json={"current_password": "testpassword123", "new_password": "short"},
    )
    assert response.status_code == 422


async def test_change_password_takes_effect_at_the_next_login(client, auth_headers):
    response = await client.post(
        f"{ME}/change-password",
        headers=auth_headers,
        json={
            "current_password": "testpassword123",
            "new_password": "brandNewPassword1",
        },
    )
    assert response.status_code == 200

    old = await login(client, "testuser", "testpassword123")
    assert old.status_code == 401
    assert old.json()["detail"] == INVALID_CREDENTIALS_DETAIL
    assert (await login(client, "testuser", "brandNewPassword1")).status_code == 200


async def test_delete_me_requires_the_password(client, auth_headers):
    missing = await client.request("DELETE", ME, headers=auth_headers)
    assert missing.status_code == 422

    wrong = await client.request(
        "DELETE", ME, headers=auth_headers, json={"password": "wrong"}
    )
    assert wrong.status_code == 400
    assert wrong.json()["detail"] == "Incorrect password"


async def test_delete_me_removes_the_account_and_kills_its_tokens(client, auth_headers):
    response = await client.request(
        "DELETE", ME, headers=auth_headers, json={"password": "testpassword123"}
    )
    assert response.status_code == 200

    gone = await client.get(ME, headers=auth_headers)
    assert gone.status_code == 401
    assert gone.json()["detail"] == "User not found"
    assert (await login(client, "testuser", "testpassword123")).status_code == 401
