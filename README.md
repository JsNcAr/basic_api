# basic-api

A simple FastAPI application for lead generation workflows with OAuth2 + JWT authentication.

## Features

- REST API endpoints for lead pipeline workflows
- OAuth2 + JWT authentication (single admin user)
- Modular structure (routers, dependencies, schemas)
- Environment-based configuration
- Flexible login: users can log in with username, email, or phone number

## Project Structure

```text
basic_api/
  src/basic_api/
    main.py         # FastAPI app entrypoint
    auth.py         # Auth logic
    dependencies.py # Dependency injection
    routers/
      auth.py       # Auth endpoints
      users.py      # User endpoints
    schemas/
      __init__.py   # Schema package exports
      base.py       # Shared base schema
      user.py       # User schemas
      response.py   # Success & error response schemas
  tests/            # Unit tests
pyproject.toml      # Poetry config
.env.example        # Environment variable template
```

## Getting Started

### 1. Install Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. Install dependencies

```bash
poetry install
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and fill in secrets:

```bash
cp .env.example .env
# Edit .env and set JWT_SECRET_KEY, etc.
```

### 4. Run the API (dev mode)

```bash
PYTHONPATH=src poetry run uvicorn basic_api.main:app --reload --host 0.0.0.0 --port 8000
```
Or use the `--app-dir src` flag:

```bash
poetry run uvicorn basic_api.main:app --reload --host 0.0.0.0 --port 8000 --app-dir src
```

## API Endpoints

- Health check: `GET /back/health`
- Auth token: `POST /back/token` (with identifier/password)
- Protected example: `GET /back/protected-example` (with Bearer token)
- User management: see `/back/api/users` endpoints

## Multi-field Login

Users can log in using their username, email, or phone number. The login request should include:

```json
{
  "identifier": "user@example.com", // or username or phone number
  "type": "email",                  // "username", "email", or "phone_number"
  "password": "yourpassword"
}
```

The backend will authenticate based on the provided type and identifier.

## Environment Variables

See `.env.example` for all required variables:

- `JWT_SECRET_KEY`: Secret for signing JWTs
- `JWT_ALGORITHM`: JWT algorithm (default: HS256)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: Token lifetime
- `ADMIN_USERNAME`: Admin login username

## Troubleshooting

- If you see `ModuleNotFoundError: No module named 'basic_api'`, use `PYTHONPATH=src` or `--app-dir src` with uvicorn.
- If you see `SyntaxError` from `jose`, ensure you have `python-jose[cryptography]` installed, not the legacy `jose` package:

  ```bash
  poetry remove jose
  poetry add "python-jose[cryptography]"
  ```

## Testing

Add your tests in the `tests/` folder and run with pytest:

```bash
poetry run pytest
```

## License
MIT
