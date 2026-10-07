"""
Registration is rate-limited per client IP. Database-backed.
"""

from basic_api.limiter import limiter


async def test_registration_is_limited_per_client(client):
    """Default RATE_LIMIT_REGISTER is 10/minute: ten accepted, the eleventh refused."""
    limiter.enabled = True
    limiter.reset()
    try:
        statuses = []
        for i in range(11):
            response = await client.post(
                "/api/users/",
                json={"username": f"user{i}", "password": "strongPassword123!"},
            )
            statuses.append(response.status_code)
        last = response
    finally:
        limiter.enabled = False
        limiter.reset()

    assert statuses[:10] == [201] * 10
    assert statuses[10] == 429
    assert last.headers["Retry-After"] == "60"
    assert last.json()["detail"].startswith("Too many requests")
