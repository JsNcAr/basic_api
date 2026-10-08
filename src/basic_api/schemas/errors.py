"""
Error responses, declared once so the OpenAPI document shows them.

Errors are FastAPI's default body, {"detail": "..."}; this module gives that
shape a schema and a description per status code, and a helper to attach the
codes a route can answer. FastAPI adds 422 itself for routes with parameters.
"""

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """The body of every non-validation error."""

    detail: str = Field(description="What went wrong, in one sentence")


# Code -> what it means in this API. Kept in step with docs/api.md.
_DESCRIPTIONS: dict[int, str] = {
    400: "A confirmation password was wrong",
    401: (
        "Missing or invalid X-API-Key; or missing, invalid, expired or orphaned "
        "bearer token; or wrong login credentials"
    ),
    403: "The account is disabled",
    409: "Username, email or phone number already in use",
    413: "Request body over MAX_REQUEST_BODY_BYTES (plain-text body)",
    429: "Over the rate limit; wait for Retry-After seconds",
    503: "Database unreachable",
}


def error_responses(*codes: int) -> dict[int | str, dict[str, Any]]:
    """
    The `responses=` entry for a route that can answer `codes`.

    Example:
        @router.patch("/me", responses=error_responses(403, 409))
    """
    out: dict[int | str, dict[str, Any]] = {}
    for code in codes:
        entry: dict[str, Any] = {"description": _DESCRIPTIONS[code]}
        if code == 413:
            # Starlette's RequestBodyLimitMiddleware answers before the app:
            # plain text, not the JSON envelope.
            entry["content"] = {"text/plain": {"schema": {"type": "string"}}}
        else:
            entry["model"] = ErrorDetail
        out[code] = entry
    return out
