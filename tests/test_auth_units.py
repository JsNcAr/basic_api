"""
Password hashing, token lifetimes and token decoding. No database.
"""

from datetime import timedelta

import pytest
from fastapi import HTTPException

from basic_api import auth
from basic_api.auth import (
    INVALID_TOKEN_DETAIL,
    access_token_lifetime,
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)

DEFAULT = timedelta(minutes=auth.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
MAXIMUM = timedelta(minutes=auth.JWT_MAX_ACCESS_TOKEN_EXPIRE_MINUTES)


def test_password_hash_round_trip():
    hashed = get_password_hash("correct horse battery staple")
    assert hashed.startswith("$2b$")
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong", hashed)


def test_long_passwords_are_supported_via_the_sha256_prehash():
    long = "x" * 200
    assert verify_password(long, get_password_hash(long))


def test_a_malformed_stored_hash_is_a_failed_verification_not_an_error():
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_lifetime_defaults_when_not_requested_or_not_positive():
    assert access_token_lifetime(None) == DEFAULT
    assert access_token_lifetime(timedelta(0)) == DEFAULT
    assert access_token_lifetime(timedelta(seconds=-1)) == DEFAULT


def test_lifetime_honours_a_request_within_the_maximum_and_caps_above_it():
    assert access_token_lifetime(timedelta(hours=2)) == timedelta(hours=2)
    assert access_token_lifetime(MAXIMUM + timedelta(days=1)) == MAXIMUM


def test_token_round_trip_carries_the_subject_and_the_lifetime():
    token = create_access_token({"sub": "42"}, expires_delta=timedelta(minutes=5))
    claims = decode_access_token(token)
    assert claims["sub"] == "42"
    assert claims["exp"] - claims["iat"] == 5 * 60


@pytest.mark.parametrize("bad", ["", "not-a-token", "a.b.c"])
def test_malformed_tokens_get_one_fixed_401_message(bad):
    with pytest.raises(HTTPException) as info:
        decode_access_token(bad)
    assert info.value.status_code == 401
    assert info.value.detail == INVALID_TOKEN_DETAIL
