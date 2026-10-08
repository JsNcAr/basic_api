# basic-api

A small, production-shaped **FastAPI** starter: OAuth2 password flow with JWT
bearer tokens, async PostgreSQL, a client API key on the API routes, rate limits
on the public routes, a test suite against a real database, and CI that gates
every pull request.

It exists to skip the same two days every new API starts with: wiring auth,
deciding where schemas and business logic live, getting dependency injection and
configuration right. That work is done here, tested, and documented.

## Features

- OAuth2 password flow with JWT bearer tokens; the token subject is the user's UUIDv7,
  so a deleted or disabled account loses access on the next request
- Flexible login: the `username` form field accepts a username, an email address
  or a phone number
- Constant-time login: an unknown account and a wrong password take the same
  time and return the same body
- Passwords hashed with bcrypt over a SHA-256 pre-hash, off the event loop
- Client API key as a declared OpenAPI security scheme on every `/api` route
- Rate limits per client IP on login and registration (slowapi)
- User self-service: read, update, change password and delete the own account
- Async PostgreSQL through SQLModel and asyncpg; health check that pings it
- One `config.py` reads and validates every environment variable at startup
- black, flake8 and mypy clean; pytest suite; GitHub Actions lint and test jobs

## Documentation

| Document | Contents |
|---|---|
| [Index](docs/index.md) | Overview and navigation |
| [Setup](docs/setup.md) | Install, environment variables, running, tests, code quality, adapting the starter |
| [Authentication](docs/authentication.md) | API key, login flow, token lifetime, what invalidates a token, rate limits, errors |
| [API Reference](docs/api.md) | Every endpoint with status codes, response envelope and error shape |
| [Schemas](docs/schemas.md) | Request and response models with their limits |
| [Known Issues](docs/known_issues.md) | What the starter deliberately does not do yet |
| [Changelog](CHANGELOG.md) | What changed and when |

## Project structure

```text
basic_api/
  src/basic_api/
    main.py           # FastAPI app, /, /health, /token, /protected-example
    config.py         # Every environment variable, read and validated once
    auth.py           # Password hashing, JWT creation and validation, login
    security.py       # Client API key dependency (APIKeyHeader)
    dependencies.py   # get_current_user: token -> User, loaded from the database
    database.py       # Engine, session factory, create_all, health ping
    limiter.py        # Shared rate limiter and its 429 response
    exceptions.py     # Domain exceptions the routers map to status codes
    utils.py          # utc_now()
    routers/
      auth.py         # /api/auth/me, /api/auth/logout
      users.py        # /api/users/ (register), /api/users/me (self-service)
    schemas/
      user.py         # User table model and request/response schemas
      response.py     # SuccessResponse envelope
    services/
      users.py        # Business rules for users, independent of HTTP
  tests/              # pytest suite; database-backed and pure tests
  docs/               # Written documentation
  .github/workflows/ci.yml
pyproject.toml        # Poetry project, dev group, black and mypy config
.env.example          # Every variable, grouped, with its default
```

## Getting started

```bash
poetry install
cp .env.example .env
# set DATABASE_URL, API_KEY and a 32+ byte JWT_SECRET_KEY:
python -c "import secrets; print(secrets.token_urlsafe(32))"
poetry run uvicorn basic_api.main:app --reload --app-dir src
```

Interactive docs: http://localhost:8000/docs (served unless
`ENVIRONMENT=production`). The full variable list is in
[Setup](docs/setup.md#environment-variables).

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/` | none | Service banner with version |
| `GET` | `/health` | none | 200 when the database answers, 503 when not |
| `POST` | `/token` | none, rate-limited | Exchange credentials for a JWT |
| `GET` | `/protected-example` | API key + token | Example protected route |
| `GET` | `/api/auth/me` | API key + token | The authenticated user |
| `POST` | `/api/auth/logout` | API key + token | Confirms logout (client deletes the token) |
| `POST` | `/api/users/` | API key, rate-limited | Register |
| `GET` | `/api/users/me` | API key + token | Own profile |
| `PATCH` | `/api/users/me` | API key + token | Update own profile fields |
| `POST` | `/api/users/me/change-password` | API key + token | Change own password |
| `DELETE` | `/api/users/me` | API key + token | Delete own account (password in body) |

Login is the standard OAuth2 form, not JSON:

```bash
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=your-password"
```

Then, on `/api` routes, send both headers:

```bash
curl http://localhost:8000/api/users/me \
  -H "X-API-Key: your-api-key" \
  -H "Authorization: Bearer <token>"
```

## Testing and code quality

```bash
poetry run pytest                      # needs PostgreSQL; see docs/setup.md
poetry run pytest --noconftest tests/test_auth_units.py tests/test_user_schemas.py \
    tests/test_openapi.py tests/test_config.py tests/test_limiter.py   # no database
poetry run black --check src tests && poetry run flake8 src tests && poetry run mypy
```

CI runs the same three checks and the full suite against `postgres:17` on every
push and pull request.

## Adapting this starter

The rename points are listed in [Setup](docs/setup.md#adapting-this-starter).

## License

MIT, see [`LICENSE`](LICENSE).
