# basic-api

A small, production-shaped **FastAPI** starter with OAuth2 + JWT authentication,
async PostgreSQL, and a modular layout you can build on.

It exists to solve a specific annoyance: every new API project starts with the
same two days of work — wiring auth, deciding where schemas live, getting
dependency injection right. This is that work, already done, with documentation.

The one non-obvious feature is **flexible login**: users authenticate with a
username, an email, or a phone number against the same endpoint.

## Features

- OAuth2 password flow with JWT bearer tokens
- Flexible login — authenticate by username, email, or phone number
- Async PostgreSQL — SQLModel over async SQLAlchemy, with the asyncpg driver
- Passwords hashed with bcrypt; JWTs signed via python-jose
- API-key gate applied application-wide, on top of per-route JWT auth
- Modular structure: routers, dependencies, schemas, security
- Environment-based configuration with a documented `.env.example`
- Consistent success/error response envelopes

## Documentation

Full docs live in [`docs/`](docs):

| Document | Contents |
|---|---|
| [Index](docs/index.md) | Overview and navigation |
| [Setup](docs/setup.md) | Prerequisites, install, environment, first run |
| [Authentication](docs/authentication.md) | Token flow, the multi-field login, protecting routes |
| [API Reference](docs/api.md) | Every endpoint, with requests and responses |
| [Schemas](docs/schemas.md) | Pydantic models and the response envelope |

## Project structure

```text
basic_api/
  src/basic_api/
    main.py           # FastAPI app entrypoint
    auth.py           # Authentication logic
    security.py       # Password hashing, token signing
    database.py       # Async engine and session management
    dependencies.py   # Shared dependency injection
    routers/
      auth.py         # Token issuance
      users.py        # User management
    schemas/
      base.py         # Shared base schema
      user.py         # User schemas
      response.py     # Success & error envelopes
  docs/               # Written documentation
  tests/              # Test package (see Testing below)
pyproject.toml        # Poetry configuration
.env.example          # Environment variable template
```

## Getting started

### 1. Install Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. Install dependencies

```bash
poetry install
```

### 3. Configure the environment

```bash
cp .env.example .env
```

Then edit `.env`. At minimum set `DATABASE_URL` and generate a real
`JWT_SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Async PostgreSQL DSN (`postgresql+asyncpg://...`) |
| `JWT_SECRET_KEY` | Secret used to sign JWTs — never commit the real value |
| `JWT_ALGORITHM` | Signing algorithm (default `HS256`) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime (default `30`) |
| `API_KEY` | Shared API key for service-to-service calls |

### 4. Run it

```bash
poetry run uvicorn basic_api.main:app --reload --app-dir src --port 8000
```

Interactive docs are then at http://localhost:8000/docs.

## Endpoints

Top-level routes are declared on the app; the routers mount under `/api`.
**Every route requires an API key** — `verify_api_key` is registered as an
application-wide dependency, so send your `API_KEY` alongside any bearer token.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Service banner — name, version, status |
| `GET` | `/health` | Health check |
| `POST` | `/token` | Exchange credentials for a JWT |
| `GET` | `/protected-example` | Example route requiring a bearer token |
| `GET` | `/api/auth/me` | Current user info |
| `POST` | `/api/auth/logout` | Invalidate the session |
| `POST` | `/api/users/` | Create a user |

Deploying behind a reverse proxy under a subpath? Set `root_path` on the
`FastAPI()` call in `main.py`, or pass `uvicorn --root-path /your-prefix`.

### Multi-field login

`POST /token` accepts an identifier plus the kind of identifier it is:

```json
{
  "identifier": "user@example.com",
  "type": "email",
  "password": "yourpassword"
}
```

`type` is one of `username`, `email`, or `phone_number`. The backend resolves
the user against the matching column.

Use the returned token on subsequent requests:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/protected-example
```

## Testing

> **The test suite is not written yet.** `tests/` is currently an empty package —
> the scaffolding is in place but there are no cases in it.

Once you add tests:

```bash
poetry run pytest
```

## Troubleshooting

**`ModuleNotFoundError: No module named 'basic_api'`**
Sources live under `src/`, so uvicorn needs to be told. Use `--app-dir src`, or
set `PYTHONPATH=src`.

**`SyntaxError` originating in `jose`**
You have the abandoned `jose` package rather than the maintained fork:

```bash
poetry remove jose
poetry add "python-jose[cryptography]"
```

## License

MIT — see [`LICENSE`](LICENSE).
