"""
What the generated OpenAPI document says about security. No database.
"""

from basic_api.main import app


def test_both_security_schemes_are_declared():
    schemes = app.openapi()["components"]["securitySchemes"]
    assert set(schemes) == {"OAuth2PasswordBearer", "APIKeyHeader"}
    assert schemes["APIKeyHeader"]["name"] == "X-API-Key"


def test_public_routes_declare_no_security():
    paths = app.openapi()["paths"]
    for path, method in (("/", "get"), ("/health", "get"), ("/token", "post")):
        assert "security" not in paths[path][method], path


def test_api_routes_require_the_key_and_the_token():
    me = app.openapi()["paths"]["/api/auth/me"]["get"]["security"]
    assert {"APIKeyHeader": []} in me and {"OAuth2PasswordBearer": []} in me


def test_plain_routes_have_response_schemas():
    schemas = app.openapi()["components"]["schemas"]
    for name in (
        "BannerResponse",
        "HealthResponse",
        "TokenResponse",
        "GreetingResponse",
    ):
        assert name in schemas, name


# Every status docs/api.md lists for a route, by (method, path). 200/201 and the
# automatic 422 are not listed here; the test adds them where FastAPI does.
DOCUMENTED = {
    ("get", "/health"): {503},
    ("post", "/token"): {401, 403, 413, 429},
    ("get", "/protected-example"): {401, 403},
    ("get", "/api/auth/me"): {401, 403},
    ("post", "/api/auth/logout"): {401, 403},
    ("post", "/api/users/"): {401, 409, 413, 429},
    ("get", "/api/users/me"): {401, 403},
    ("patch", "/api/users/me"): {401, 403, 409, 413},
    ("post", "/api/users/me/change-password"): {400, 401, 403, 413},
    ("delete", "/api/users/me"): {400, 401, 403, 413},
}


def test_every_documented_error_status_is_declared():
    paths = app.openapi()["paths"]
    for (method, path), codes in DOCUMENTED.items():
        declared = {int(c) for c in paths[path][method]["responses"] if c.isdigit()}
        missing = codes - declared
        assert not missing, f"{method.upper()} {path} lacks {sorted(missing)}"
