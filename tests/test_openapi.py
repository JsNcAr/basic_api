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
