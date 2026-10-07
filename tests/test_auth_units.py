"""
Password hashing and token round trips. No database; runs with --noconftest.
"""

from fastapi import HTTPException
import pytest

from basic_api.auth import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


def test_password_hash_round_trip():
    hashed = get_password_hash("correct horse battery staple")
    assert hashed.startswith("$2b$")
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong", hashed)


def test_long_passwords_are_supported_via_the_sha256_prehash():
    long = "x" * 200
    assert verify_password(long, get_password_hash(long))


def test_token_round_trip_carries_the_subject():
    token = create_access_token({"sub": "alice"})
    claims = decode_access_token(token)
    assert claims["sub"] == "alice"
    assert claims["exp"] > claims["iat"]


@pytest.mark.parametrize("bad", ["", "not-a-token", "a.b.c"])
def test_malformed_tokens_are_refused_with_401(bad):
    with pytest.raises(HTTPException) as info:
        decode_access_token(bad)
    assert info.value.status_code == 401
