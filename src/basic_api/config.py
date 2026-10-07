"""
Runtime configuration, read from the environment once at import.

Every variable the app reads lives here with its default and its validation, so
a bad value stops the process at startup instead of failing the first request
that touches it. Other modules import the names they need from here; nothing
else calls os.getenv or load_dotenv.

Adapting this starter: add a new variable here and in .env.example, and keep
the two in step. The distribution name in _package_version() must match the
`name` in pyproject.toml.
"""

import os
import sys
from importlib.metadata import PackageNotFoundError, version

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"{name} environment variable is required. "
            "Copy .env.example to .env and fill it in."
        )
    return value


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise RuntimeError(f"{name}={raw!r} is not an integer")


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def csv_list(raw: str) -> list[str]:
    """Split a comma-separated setting into trimmed, non-empty items."""
    return [item.strip() for item in raw.split(",") if item.strip()]


def docs_enabled(environment: str, enable_docs: str | None) -> bool:
    """
    Whether /docs, /redoc and /openapi.json are served.

    On everywhere except production by default; ENABLE_DOCS overrides either
    way, so a production deployment can opt in and a staging one can opt out.

    Args:
        environment: Value of ENVIRONMENT, already lower-cased.
        enable_docs: Raw value of ENABLE_DOCS, or None when unset.

    Returns:
        True when the interactive documentation should be served.
    """
    if enable_docs is None or enable_docs.strip() == "":
        return environment != "production"
    return enable_docs.strip().lower() in ("1", "true", "yes", "on")


# --- Application -------------------------------------------------------------

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()
ENABLE_DOCS = docs_enabled(ENVIRONMENT, os.getenv("ENABLE_DOCS"))


def _package_version() -> str:
    """The version in pyproject.toml, as installed; one source for every place."""
    try:
        return version("basic-api")
    except PackageNotFoundError:
        return "0.0.0"


# APP_VERSION overrides for deployments that stamp a build number.
APP_VERSION = os.getenv("APP_VERSION") or _package_version()
# Set when served under a path prefix by a reverse proxy, e.g. "/api-name".
ROOT_PATH = os.getenv("ROOT_PATH", "")

# "*" is right for a public API consumed by native apps; a browser frontend
# should list its origins so that other sites cannot call the API with the
# user's credentials.
CORS_ORIGINS = csv_list(os.getenv("CORS_ORIGINS", "*"))
CORS_METHODS = csv_list(os.getenv("CORS_METHODS", "*"))
CORS_HEADERS = csv_list(os.getenv("CORS_HEADERS", "*"))

# --- Database ----------------------------------------------------------------

_TESTING = "pytest" in sys.modules


def _test_database_url() -> str:
    """The URL tests/conftest.py builds, so the app and the tests share a database."""
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("TEST_DB_NAME", "basic_api_test_db")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


_database_url = os.getenv("DATABASE_URL")
if not _database_url:
    if _TESTING:
        _database_url = _test_database_url()
    else:
        raise RuntimeError(
            "DATABASE_URL environment variable is required "
            "(postgresql+asyncpg://user:password@host:5432/dbname). "
            "Copy .env.example to .env and fill it in."
        )
DATABASE_URL: str = _database_url
# Logs every SQL statement; development only.
DATABASE_ECHO = _flag("DATABASE_ECHO", False)

# --- Security ----------------------------------------------------------------

# The client API key (see security.py for what it is and is not).
API_KEY: str = _required("API_KEY")

# 32 bytes is the HMAC key size the HS256 family is specified for; a shorter
# secret weakens every token at once.
_MIN_SECRET_BYTES = 32
_ALLOWED_ALGORITHMS = ("HS256", "HS384", "HS512")
_MIN_BCRYPT_ROUNDS = 12

JWT_SECRET_KEY: str = _required("JWT_SECRET_KEY")
if len(JWT_SECRET_KEY.encode("utf-8")) < _MIN_SECRET_BYTES:
    raise RuntimeError(
        f"JWT_SECRET_KEY must be at least {_MIN_SECRET_BYTES} bytes. Generate one "
        "with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    )

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM") or "HS256"
if JWT_ALGORITHM not in _ALLOWED_ALGORITHMS:
    raise RuntimeError(
        f"JWT_ALGORITHM={JWT_ALGORITHM!r} is not one of "
        + ", ".join(_ALLOWED_ALGORITHMS)
    )

JWT_ACCESS_TOKEN_EXPIRE_MINUTES = _int("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30)
# Longest lifetime a client may request at login (default 7 days).
JWT_MAX_ACCESS_TOKEN_EXPIRE_MINUTES = _int(
    "JWT_MAX_ACCESS_TOKEN_EXPIRE_MINUTES", 7 * 24 * 60
)
if JWT_MAX_ACCESS_TOKEN_EXPIRE_MINUTES < JWT_ACCESS_TOKEN_EXPIRE_MINUTES:
    raise RuntimeError(
        "JWT_MAX_ACCESS_TOKEN_EXPIRE_MINUTES must be at least "
        "JWT_ACCESS_TOKEN_EXPIRE_MINUTES."
    )

BCRYPT_ROUNDS = _int("BCRYPT_ROUNDS", _MIN_BCRYPT_ROUNDS)
if BCRYPT_ROUNDS < _MIN_BCRYPT_ROUNDS:
    raise RuntimeError(
        f"BCRYPT_ROUNDS={BCRYPT_ROUNDS} is below the minimum of {_MIN_BCRYPT_ROUNDS}."
    )

# --- Rate limits -------------------------------------------------------------
# slowapi/limits syntax, e.g. "10/minute", "100/hour"; validated in limiter.py.
# Per client IP and per process (each uvicorn worker keeps its own count).
RATE_LIMIT_LOGIN = os.getenv("RATE_LIMIT_LOGIN", "60/minute")
RATE_LIMIT_REGISTER = os.getenv("RATE_LIMIT_REGISTER", "10/minute")
