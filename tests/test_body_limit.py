"""
Requests over MAX_REQUEST_BODY_BYTES are refused before any route runs.
Database-backed only because the client fixture is; the route is never reached.
"""

from basic_api.config import MAX_REQUEST_BODY_BYTES


async def test_an_oversized_body_is_a_413_before_validation(client):
    # Twice the limit, as a syntactically valid JSON body: without the limit this
    # would reach pydantic and fail on username's max_length with a 422.
    oversized = {"username": "x" * (2 * MAX_REQUEST_BODY_BYTES), "password": "p" * 8}
    response = await client.post("/api/users/", json=oversized)
    assert response.status_code == 413


async def test_a_normal_body_is_unaffected(client):
    response = await client.post(
        "/api/users/", json={"username": "fits", "password": "strongPassword123!"}
    )
    assert response.status_code == 201
