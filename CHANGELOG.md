# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow
`pyproject.toml`.

## [Unreleased]

### Added
- `pip-audit` in the dev group and in the CI `lint` job, so a published
  vulnerability in any installed dependency fails a pull request; Dependabot
  configuration for weekly, grouped dependency and GitHub Actions updates (#9).

### Security
- JWTs are signed and verified with PyJWT 2.15 instead of python-jose 3.5.
  `pip-audit` reported python-jose with an unfixed algorithm-confusion
  advisory (CVE-2026-85394; this API already restricted algorithms and was not
  exposed) and its dependency ecdsa with an unfixed timing attack
  (PYSEC-2026-1325; ECDSA signing is not used). python-jose's last release was
  May 2025. The swap also removes cryptography, ecdsa, rsa, pyasn1, cffi and
  pycparser from the dependency tree; HS256 needs none of them (#9).

### Dependencies
- Every dependency moved to its current release and the ranges in
  `pyproject.toml` opened to the next major (`poetry.lock` is the pin):
  FastAPI 0.121 to 0.142, Starlette 0.49 to 1.7, uvicorn 0.38 to 0.54,
  pydantic 2.12 to 2.13, SQLModel 0.0.27 to 0.0.48, asyncpg 0.31 to 0.32,
  python-multipart 0.0.20 to 0.0.32, python-dotenv 1.2.1 to 1.2.4, plus the
  dev tools. SQLAlchemy is held at 2.0.x (`<2.1`) until 2.1 ships wheels (#7).
- `cryptography` 46.0.3 to 50.0.2, closing seven published advisories (#7).

### Added
- Response models for `/`, `/health`, `/token` and `/protected-example`, so the
  OpenAPI document has a schema for every response (the token response had
  none) and FastAPI 0.130+ serialises them with pydantic-core; every status a
  route can answer is declared (`schemas/errors.py`), so generated clients see
  401, 403, 409, 413, 429 and 503 (#13).
- `MAX_REQUEST_BODY_BYTES` (default 1 MiB): Starlette 1.6's
  `RequestBodyLimitMiddleware` answers 413 before any route runs (#13).

### Changed
- Users are identified by UUIDv7 (`uuid.uuid7()`, new in Python 3.14) instead
  of an auto-increment integer: `id` in every response and the token subject is
  now a UUID string. Ids no longer reveal how many accounts exist, and uuid7 is
  time-ordered so the primary-key index stays append-friendly. **Breaking for an
  existing database**: the `users.id` column type changes and `create_all` does
  not convert columns; migrate before upgrading a deployment with data (#12).
- Python 3.14: `.python-version` says `3.14`, `requires-python` is
  `>=3.14,<4.0`, Black targets `py314` and mypy checks against 3.14. Every
  dependency in the lock ships a 3.14 wheel or is pure Python, so no package is
  built from source (#8).
- Timestamps are aware UTC end to end. SQLModel 0.0.45+ maps `datetime`
  columns to `TIMESTAMP WITH TIME ZONE` and refuses naive values, so
  `utc_now()` now returns an aware datetime and responses end in `Z`. A database created before this change keeps `TIMESTAMP WITHOUT TIME
  ZONE` columns (`create_all` never alters them); migrate them before
  upgrading an existing deployment (#7).
- FastAPI 0.132+ rejects JSON requests whose `Content-Type` is not a JSON
  media type; clients must send `application/json` (#7).

Five pull requests bringing the starter up to what a production API built on it
(KorvynApi) learned.

### Added
- Dev tooling (black, flake8, mypy, pytest) with configuration; GitHub Actions
  `lint` and `test` jobs against PostgreSQL 17; the Poetry and Python versions
  derived from `poetry.lock` and `.python-version` (#1).
- Test suite: fixtures for a throwaway test database, pure and database-backed
  tests for every route (#1, #2, #3, #4).
- `config.py`: every environment variable read and validated at startup;
  `ENVIRONMENT`, `ENABLE_DOCS`, `APP_VERSION`, `ROOT_PATH`, `CORS_*`,
  `DATABASE_ECHO`, `JWT_MAX_ACCESS_TOKEN_EXPIRE_MINUTES`, `BCRYPT_ROUNDS`,
  `RATE_LIMIT_LOGIN`, `RATE_LIMIT_REGISTER` (#2, #3).
- Rate limits on `POST /token` and `POST /api/users/` with a `Retry-After` 429 (#3).
- `/health` checks the database and answers 503 when it is down (#3).
- `?expires_delta=` on login, capped by the server; `expires_in` in the token
  response (#2).
- User self-service: `GET`/`PATCH`/`DELETE /api/users/me`,
  `POST /api/users/me/change-password`; a service layer with domain
  exceptions (#4).
- `AGENTS.md`, `docs/known_issues.md`, this changelog (#5).

### Changed
- The token subject is the user id and the user is loaded on every request:
  deletion and deactivation take effect at once (#2).
- Login is constant-time; unknown account and wrong password share one 401
  body; a disabled account is 403 after the password checks out (#2).
- The API key is a declared `APIKeyHeader` scheme, compared in constant time,
  applied to `/api` routes and `/protected-example` only; `/`, `/health` and
  `/token` are public (#2).
- `username`, `email` and `phone_number` are unique; `username` is required;
  every free-text field has a maximum length; `profile_picture_url` must be an
  http(s) URL (#2).
- Registration answers 409 naming the taken field and never returns database
  error text (#2).
- Token lifetime comes from `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (it was a
  hard-coded 15 minutes); decode failures answer one fixed message (#2).
- Startup refuses a secret under 32 bytes, an algorithm outside the HMAC
  family, or fewer than 12 bcrypt rounds (#2).
- `/api/auth/me` returns the stored user instead of a fabricated email and role (#2).
- Engine: `echo` from config, one session factory, `pool_pre_ping`, disposed at
  shutdown (#3).
- `requires-python` bounded to `>=3.13,<4.0` (#3).
- Docs rewritten against the code; the JSON login they described never
  existed (#5).

### Removed
- `bluetooth_address`, `wifi_mac_address`, `User.is_deleted`, `UserLoginSchema`,
  `BaseSchema`, `ErrorResponse`, `get_current_user_from_cookie` (#2).
- The `leads-frontend-api` health check name (#3).

### Security
- Error responses no longer include SQL statements and parameters from
  `IntegrityError` (#2).
- A deleted or disabled account's tokens stop working immediately (#2).
