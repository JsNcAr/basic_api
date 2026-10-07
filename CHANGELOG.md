# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow
`pyproject.toml`.

## [Unreleased]

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
