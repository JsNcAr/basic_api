"""
Registration rules. Database-backed; runs in CI.
"""

import pytest

PAYLOAD = {
    "username": "someone",
    "email": "someone@example.com",
    "phone_number": "+15550100",
    "password": "strongPassword123!",
}


async def register(client, **overrides):
    return await client.post("/api/users/", json={**PAYLOAD, **overrides})


@pytest.mark.parametrize(
    "field, message",
    [
        ("username", "Username is already taken"),
        ("email", "Email address is already registered"),
        ("phone_number", "Phone number is already associated with an account"),
    ],
)
async def test_a_taken_identifier_is_a_409_naming_the_field(client, field, message):
    assert (await register(client)).status_code == 201

    # Everything else differs; only `field` collides.
    fresh = {
        "username": "another",
        "email": "another@example.com",
        "phone_number": "+15550199",
    }
    fresh[field] = PAYLOAD[field]
    response = await register(client, **fresh)

    assert response.status_code == 409
    assert response.json() == {"detail": message}


async def test_error_bodies_never_carry_database_text(client):
    await register(client)
    body = (await register(client)).text.lower()
    for fragment in ("insert", "select", "sqlalchemy", "asyncpg", "duplicate key"):
        assert fragment not in body


async def test_username_is_required(client):
    payload = {k: v for k, v in PAYLOAD.items() if k != "username"}
    response = await client.post("/api/users/", json=payload)
    assert response.status_code == 422


async def test_a_non_http_profile_picture_url_is_refused(client):
    response = await register(client, profile_picture_url="javascript:alert(1)")
    assert response.status_code == 422


async def test_a_valid_profile_picture_url_is_stored(client):
    response = await register(client, profile_picture_url="https://example.com/a.png")
    assert response.status_code == 201
    assert response.json()["data"]["profile_picture_url"] == "https://example.com/a.png"


async def test_the_response_has_no_legacy_fields(client):
    data = (await register(client)).json()["data"]
    for legacy in ("bluetooth_address", "wifi_mac_address", "is_deleted"):
        assert legacy not in data


async def test_ids_are_version_7_uuids_ordered_by_creation(client):
    import uuid

    first = uuid.UUID((await register(client)).json()["data"]["id"])
    second = uuid.UUID(
        (
            await register(client, username="later", email=None, phone_number=None)
        ).json()["data"]["id"]
    )
    # Version 7 is time-ordered (RFC 9562), so a later account sorts after an
    # earlier one, and nothing about the value says how many accounts exist.
    assert first.version == second.version == 7
    assert first != second and first < second
