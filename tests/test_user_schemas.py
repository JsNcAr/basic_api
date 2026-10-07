"""
Registration schema rules that need no database.
"""

import pytest
from pydantic import ValidationError

from basic_api.schemas.user import (
    EMAIL_MAX_LENGTH,
    PHONE_NUMBER_MAX_LENGTH,
    USERNAME_MAX_LENGTH,
    UserCreateSchema,
)


def create(**overrides):
    return UserCreateSchema(
        **{"username": "someone", "password": "12345678", **overrides}
    )


def test_fields_at_their_maximum_length_are_accepted():
    user = create(
        username="u" * USERNAME_MAX_LENGTH,
        email="a" * (EMAIL_MAX_LENGTH - len("@example.com")) + "@example.com",
        phone_number="1" * PHONE_NUMBER_MAX_LENGTH,
    )
    assert len(user.username) == USERNAME_MAX_LENGTH


@pytest.mark.parametrize(
    "field, value",
    [
        ("username", "u" * (USERNAME_MAX_LENGTH + 1)),
        ("phone_number", "1" * (PHONE_NUMBER_MAX_LENGTH + 1)),
    ],
)
def test_a_field_over_its_maximum_length_is_refused(field, value):
    with pytest.raises(ValidationError):
        create(**{field: value})


def test_username_is_required():
    with pytest.raises(ValidationError):
        UserCreateSchema(password="12345678", email="a@example.com")


@pytest.mark.parametrize(
    "bad",
    ["javascript:alert(1)", "data:text/html;base64,PHNjcmlwdD4=", "ftp://x/y", "nope"],
)
def test_a_profile_picture_url_that_is_not_http_is_refused(bad):
    with pytest.raises(ValidationError):
        create(profile_picture_url=bad)


def test_a_short_password_is_refused():
    with pytest.raises(ValidationError):
        create(password="short")
