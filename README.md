# basic-api

A simple FastAPI application for lead generation workflows with OAuth2 + JWT authentication.

## Features
- REST API endpoints for lead pipeline workflows
- OAuth2 + JWT authentication (single admin user)
- Modular structure (routers, dependencies)
- Environment-based configuration

## Project Structure
```
basic_api/
  src/basic_api/
    main.py         # FastAPI app entrypoint
    auth.py         # Auth logic
    dependencies.py # Dependency injection
    schemas.py      # Pydantic schemas
    routers/        # API routers
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

### 5. API Endpoints
- Health check: `GET /back/health`
- Auth token: `POST /back/token` (with username/password)
- Protected example: `GET /back/protected-example` (with Bearer token)

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
