# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow
`pyproject.toml`. Add entries under **Unreleased** in the same pull request as
the change; `scripts/release.py` turns that section into the next release's
notes (see [docs/releasing.md](docs/releasing.md)).

## [Unreleased]

### Added
- `pip-audit` in the dev group and in the CI `lint` job, so a published
  vulnerability in any installed dependency fails a pull request; Dependabot
  configuration for weekly, grouped dependency and GitHub Actions updates (#9).

### Security
- `API_KEY` and `JWT_SECRET_KEY` are pydantic `SecretStr` values in
  `config.py`: their repr is `**********`, so a traceback or a log line that
  reaches a config value never shows them (#16).
- JWTs are signed and verified with PyJWT 2.15 instead of python-jose 3.5.
  `pip-audit` reported python-jose with an unfixed algorithm-confusion
  advisory (CVE-2026-85394; this API already restricted algorithms and was not
  exposed) and its dependency ecdsa with an unfixed timing attack
  (PYSEC-2026-1325; ECDSA signing is not used). python-jose's last release was
  May 2025. The swap also removes cryptography, ecdsa, rsa, pyasn1, cffi and
  pycparser from the dependency tree; HS256 needs none of them (#9).

### Dependencies
- SQLAlchemy 2.0.54 to 2.1.4, declared as `sqlalchemy[asyncio]` because 2.1
  installs greenlet, which the asyncio extension needs, only through that
  extra. 2.1 ships a Python 3.15 wheel, so the Cython speedups are back on
  3.15. Of the 2.1 behaviour changes, none reaches this code: the database
  URL names `asyncpg` explicitly (2.1 defaults `postgresql://` to psycopg 3),
  there are no PostgreSQL named types, and autoflush now also runs before
  Core statements such as the health check's `SELECT 1`, which never has
  pending changes. The suite passes with every SQLAlchemy warning as an error.
  SQLModel 0.0.48 added 2.1 support (#21).
- Refresh before the move to Python 3.15: pydantic 2.13.5 to 2.14.1 with
  pydantic-core 2.50.1, the first release with Python 3.15 wheels; FastAPI
  0.142.2 to 0.143.1; Starlette 1.7.0 to 1.8.0; Black 26.10.0 to 26.10.1 and
  the transitive updates Poetry resolved. FastAPI 0.143 makes its automatic
  OpenTelemetry exporter setup opt-in, which changes nothing here because the
  starter configures no telemetry. SQLAlchemy stays on 2.0.x by choice, see
  the comment in `pyproject.toml` (#19).
- Every dependency moved to its current release and the ranges in
  `pyproject.toml` opened to the next major (`poetry.lock` is the pin):
  FastAPI 0.121 to 0.142, Starlette 0.49 to 1.7, uvicorn 0.38 to 0.54,
  pydantic 2.12 to 2.13, SQLModel 0.0.27 to 0.0.48, asyncpg 0.31 to 0.32,
  python-multipart 0.0.20 to 0.0.32, python-dotenv 1.2.1 to 1.2.4, plus the
  dev tools. SQLAlchemy is held at 2.0.x (`<2.1`) until 2.1 ships wheels (#7).
- `cryptography` 46.0.3 to 50.0.2, closing seven published advisories (#7).

### Added
- `.gitlab-ci.yml`: the same lint and test jobs as the GitHub workflow for a
  GitLab instance (test results in the merge request widget), plus the release
  jobs on a `v*` tag: verify, build, and a GitLab release created with `glab`
  with the wheel and sdist in the generic package registry. The release script
  prints the pipeline URL for GitHub or GitLab remotes (#18).
- Release tooling: `scripts/release.py prepare patch|minor|major|X.Y.Z` runs
  the suite, bumps `pyproject.toml`, turns Unreleased into the version's
  section, commits, tags and pushes atomically; `.github/workflows/release.yml`
  verifies the tag, reruns CI, builds the wheel and sdist and publishes the
  GitHub release with that section as notes. The starter itself stays
  unreleased behind `[tool.release] starter = true`; a clone flips it (#17).
- Logging configuration (`logging_config.py`): `LOG_LEVEL`, `LOG_FORMAT`
  (`json` lines in production by default, `text` elsewhere), and a
  QueueHandler/QueueListener pipeline from the standard library so that
  writing a line never blocks the event loop; the listener runs as a context
  manager (Python 3.14) for the app's lifetime. `X-Request-ID` on every
  response (`request_id.py`; a supplied id is kept when it is safe, otherwise
  a UUIDv7 is generated) and on every log line of that request (#16).
- `X-RateLimit-Limit`, `X-RateLimit-Remaining` and `X-RateLimit-Reset` on the
  responses of the two rate-limited routes (slowapi `headers_enabled`), so a
  client can pace itself before the `429` (#16).
- Response models for `/`, `/health`, `/token` and `/protected-example`, so the
  OpenAPI document has a schema for every response (the token response had
  none) and FastAPI 0.130+ serialises them with pydantic-core; every status a
  route can answer is declared (`schemas/errors.py`), so generated clients see
  401, 403, 409, 413, 429 and 503 (#13).
- `MAX_REQUEST_BODY_BYTES` (default 1 MiB): Starlette 1.6's
  `RequestBodyLimitMiddleware` answers 413 before any route runs (#13).

### Changed
- Python 3.15 idioms. Read-only module constants are `frozendict`
  (`_SECRET_MINIMUM_BYTES`, `_TAKEN_MESSAGES`, `_DESCRIPTIONS`, the release
  script's `SECTIONS`); generic aliases come from `collections.abc` with the
  single parameter 3.13+ allows; `scripts/release.py` uses `re.prefixmatch`
  (3.15's explicit name for the soft-deprecated `match`), drops `from
  __future__ import annotations` and names `encoding="utf-8"` on every file
  and subprocess read, PEP 686's advice now that UTF-8 is the default, so
  `-X warn_default_encoding` is clean. The setup guide adds the 3.15 sampling
  profiler (`profiling.sampling`) next to the asyncio commands. Evaluated and
  left unused, so the question need not be reopened: lazy imports (PEP 810;
  the server imports everything at startup and the release script starts in
  milliseconds), `sentinel` (no sentinel pattern), unpacking in comprehensions
  (nothing to flatten), `TaskGroup.cancel` (no task groups), TypedDict
  `closed` and `TypeForm` (no TypedDicts), free-threading and the JIT (nothing
  CPU-bound) (#23).
- The rate limiter is built directly on `limits` (fixed window, in-process
  memory) instead of slowapi, whose `asyncio.iscoroutinefunction` call is
  removed in Python 3.16 and unfixed upstream. A limited route now declares
  `Depends(limiter.limit(...))` instead of a decorator plus `request` and
  `response` parameters it never used. Same limits, same per-IP and per-route
  counting, same `429` body and `Retry-After`; the `429` now also carries the
  `X-RateLimit` headers, and `X-RateLimit-Reset` is a whole number of seconds.
  The `pytest.ini` warning filter for slowapi is gone, so the suite runs with
  no filtered warnings (#22).
- Python 3.15: `.python-version` says `3.15`, `requires-python` is
  `>=3.15,<4.0`, Black targets `py315`, mypy checks against 3.15 and the GitLab
  pipeline runs on `python:3.15-slim`. Every dependency ships a 3.15 wheel or is
  pure Python; SQLAlchemy 2.0.x installs as pure Python on 3.15 (Known Issues).
  uvicorn 0.54.0 and FastAPI 0.143.1 pass the suite on 3.15, although uvicorn's
  3.15 support is merged and unreleased and FastAPI's CI matrix still ends at
  3.14 (#20).
- Annotations use the current syntax: `X | None` instead of `Optional[X]`,
  `SuccessResponse` is a PEP 695 generic (`class SuccessResponse[T]`), and
  every route dependency is `Annotated`, through the `SessionDep` and
  `CurrentUserDep` aliases in `dependencies.py`. No behaviour change; the
  OpenAPI document differs only in the envelope example's id, now a UUID (#15).
- `JWT_SECRET_KEY` minimum follows the algorithm: 32 bytes for HS256, 48 for
  HS384, 64 for HS512 (RFC 7518 section 3.2), checked at startup by the tested
  `config.minimum_secret_bytes()`; `decode_access_token` also passes PyJWT's
  `enforce_minimum_key_length`, so the library's own check is an error, not a
  warning (#14).
- Domain exceptions are mapped to status codes once, by app-level exception
  handlers, instead of a try/except in every route; same codes and bodies (#14).
- `utc_now()` uses `datetime.UTC`; `UserResponseSchema` declares `created_at`
  and `updated_at` as `AwareDatetime`, the contract SQLModel's `UTCDateTime`
  fulfils (#14).
- Python 3.14 features evaluated for this code base and left unused, so the
  question need not be reopened: template strings (no templating), deferred
  annotations (no forward references to simplify), multiple interpreters and
  free-threading (nothing CPU-bound), `compression.zstd`, `functools.Placeholder`.
  Adopted: `uuid.uuid7()` (#12), PEP 758 `except A, B:` via Black, the asyncio
  introspection commands in the setup guide (#14).
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
