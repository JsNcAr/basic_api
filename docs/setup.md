# Setup

## Prerequisites

- Python 3.14 (`.python-version` pins the minor for pyenv, uv and CI; the newest patch release is used)
- [Poetry](https://python-poetry.org/) 2.x
- PostgreSQL (any supported version; CI tests against 17)

## Install

```bash
git clone <repository-url>
cd basic_api
poetry install
```

`poetry install` also installs the development tools (pytest, black, flake8,
mypy) and the project itself, which is where `APP_VERSION` defaults from.

## Environment variables

```bash
cp .env.example .env
```

Every variable is read and validated once, at startup, in
`src/basic_api/config.py`; an invalid or missing required value stops the
process with a message naming the variable. `.env.example` has every variable
with a comment; the table below is the summary.

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | yes | | `postgresql+asyncpg://user:password@host:5432/dbname` |
| `API_KEY` | yes | | Client API key sent as `X-API-Key` on `/api` routes |
| `JWT_SECRET_KEY` | yes | | At least 32 bytes. `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `JWT_ALGORITHM` | | `HS256` | One of `HS256`, `HS384`, `HS512` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | | `30` | Default token lifetime |
| `JWT_MAX_ACCESS_TOKEN_EXPIRE_MINUTES` | | `10080` (7 days) | Longest lifetime a client may request with `?expires_delta=`; must be at least the default |
| `BCRYPT_ROUNDS` | | `12` | bcrypt cost; 12 is the minimum accepted |
| `ENVIRONMENT` | | `development` | `production` turns the interactive docs off by default |
| `ENABLE_DOCS` | | by `ENVIRONMENT` | `true`/`false` to force `/docs`, `/redoc`, `/openapi.json` on or off |
| `APP_VERSION` | | the installed package version | Reported by `GET /` and the OpenAPI document |
| `ROOT_PATH` | | empty | Path prefix when served behind a reverse proxy |
| `CORS_ORIGINS`, `CORS_METHODS`, `CORS_HEADERS` | | `*` | Comma-separated; a browser frontend should list its origins |
| `DATABASE_ECHO` | | `false` | Log every SQL statement (development only) |
| `RATE_LIMIT_LOGIN` | | `60/minute` | Per client IP on `POST /token` |
| `RATE_LIMIT_REGISTER` | | `10/minute` | Per client IP on `POST /api/users/` |
| `MAX_REQUEST_BODY_BYTES` | | `1048576` | Largest request body; larger ones get `413` before any route runs |
| `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `TEST_DB_NAME` | tests only | `postgres`, `postgres`, `localhost`, `5432`, `basic_api_test_db` | The test database (see Testing) |

## Running

```bash
# development, with reload
poetry run uvicorn basic_api.main:app --reload --app-dir src --port 8000

# production
poetry run uvicorn basic_api.main:app --host 0.0.0.0 --port 8000 --app-dir src
```

Tables are created at startup with SQLModel's `create_all`, which adds missing
tables and never alters existing ones. That is right for a starter; once the
schema changes under live data, replace it with Alembic migrations run as a
deploy step (see [Known Issues](known_issues.md#schema-is-created-at-startup-not-migrated)).

Behind a reverse proxy under a path prefix, set `ROOT_PATH`. uvicorn trusts
`X-Forwarded-For` from `127.0.0.1` by default; if the proxy runs elsewhere, add
`--forwarded-allow-ips <proxy-ip>`, or every client shares one rate-limit bucket.

## Testing

Database-backed tests need a PostgreSQL database the test user can create tables
in. Create it once:

```sql
CREATE DATABASE basic_api_test_db;
```

and point the `DB_*` variables at it (they default to `postgres`/`postgres` on
`localhost`). The suite creates the tables at the start of the run, deletes every
row between tests, and drops the tables at the end. The app's own engine uses the
same database when imported by pytest (`config.TESTING`), so the health check
works in tests.

```bash
poetry run pytest
```

Tests that need no database can run anywhere:

```bash
poetry run pytest --noconftest tests/test_auth_units.py tests/test_user_schemas.py \
    tests/test_openapi.py tests/test_config.py tests/test_limiter.py
```

Deprecation warnings are not silenced; a new one in the summary is information,
not noise.

## Code quality

```bash
poetry run black --check src tests   # formatting, line length 88
poetry run flake8 src tests          # lint (.flake8 matches Black)
poetry run mypy                      # types, [tool.mypy] in pyproject.toml
```

```bash
poetry run pip-audit                 # known vulnerabilities in the installed dependencies
```

CI (`.github/workflows/ci.yml`) runs all four in `lint` and the suite in `test`
against a `postgres:17` service, on every push to `main` and every pull
request. Dependabot (`.github/dependabot.yml`) opens weekly pull requests for
dependency and action updates, grouped by minor and patch; the same CI checks
them. It installs the Poetry version named in `poetry.lock`'s header and the
Python version in `.python-version`, so neither is pinned twice.

## Adapting this starter

Everything a new project renames or changes, in one list:

1. **Package**: rename `src/basic_api/` and the `packages` entry in
   `pyproject.toml`; `name` in `pyproject.toml` must also match the distribution
   name in `config._package_version()`.
2. **Imports in tests**: the `from basic_api ...` lines at the top of
   `tests/conftest.py` and the test modules.
3. **CI**: the `env` block and the `postgres` matrix entry at the top of
   `.github/workflows/ci.yml`; nothing in the jobs refers to the project by
   name.
4. **Names shown to clients**: `title` and `description` in `main.py`, and
   `SERVICE_NAME` returned by `/health`.
5. **Configuration**: add a variable in `config.py` and `.env.example` together.
6. **Docs**: this folder and the README.
