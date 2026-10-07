# Known Issues

What the starter deliberately leaves for a real project to decide, and the
limits of what it ships. Each entry says what happens, where, and what a fix
looks like. Remove an entry in the same change that fixes it.

## Summary

| Area | Issue | Priority |
|------|-------|----------|
| Security | [Tokens cannot be revoked](#tokens-cannot-be-revoked) | Medium |
| Security | [No per-account login throttle](#no-per-account-login-throttle) | Medium |
| Security | [Identifiers are not normalised or verified](#identifiers-are-not-normalised-or-verified) | Medium |
| Security | [The API key is a client identifier, not a security layer](#the-api-key-is-a-client-identifier-not-a-security-layer) | Low |
| Security | [CORS allows every origin by default](#cors-allows-every-origin-by-default) | Low |
| Security | [Login identifiers can collide across columns](#login-identifiers-can-collide-across-columns) | Medium |
| Security | [Password policy is length only](#password-policy-is-length-only) | Low |
| Data | [Schema is created at startup, not migrated](#schema-is-created-at-startup-not-migrated) | High |
| Operations | [Rate limits are per IP and per process](#rate-limits-are-per-ip-and-per-process) | Low |
| Operations | [No logging configuration or observability](#no-logging-configuration-or-observability) | Medium |
| Operations | [CI has no coverage, dependency audit or secret scan](#ci-has-no-coverage-dependency-audit-or-secret-scan) | Low |
| Operations | [No deployment story](#no-deployment-story) | Low |
| Code | [The demo route ships](#the-demo-route-ships) | Low |
| Code | [The OpenAPI document under-describes responses](#the-openapi-document-under-describes-responses) | Medium |
| Code | [Startup validation and the login limit are untested](#startup-validation-and-the-login-limit-are-untested) | Low |
| Code | [Application code detects the test runner](#application-code-detects-the-test-runner) | Low |
| Code | [The root banner reports healthy without checking](#the-root-banner-reports-healthy-without-checking) | Low |

---

## Security

### Tokens cannot be revoked

**Where:** `src/basic_api/auth.py`, `src/basic_api/routers/auth.py` (`logout`), `src/basic_api/services/users.py` (`change_user_password`).

Tokens are stateless: a request is accepted if the signature and expiry check
out and the user still exists and is active. Logout and a password change do
not invalidate tokens already issued; they live until `exp`, up to
`JWT_MAX_ACCESS_TOKEN_EXPIRE_MINUTES` (7 days by default) if the client asked
for that. Deletion and deactivation do take effect at once, because the user
is loaded on every request.

**Fix:** a per-user `token_version` (or `tokens_valid_after` timestamp) stored
on the account, put into the token and compared in `get_current_user`; bump it
on password change and on an explicit "log out everywhere". Short access tokens
with refresh tokens are the fuller version.

**Until fixed:** keep `JWT_MAX_ACCESS_TOKEN_EXPIRE_MINUTES` as low as the
clients tolerate.

### No per-account login throttle

**Where:** `src/basic_api/main.py` (`login`), `src/basic_api/limiter.py`.

Login is limited per client IP (`RATE_LIMIT_LOGIN`). Nothing is counted per
account, so guesses against one username spread over many addresses are
unbounded, and one address still gets 86,400 a day. Constant-time verification
hides whether the account exists; it does not slow a guess at the password.

**Fix:** a second counter keyed by the submitted identifier, with a delay that
grows with consecutive failures rather than a hard lockout, so an attacker
cannot lock the owner out.

### Identifiers are not normalised or verified

**Where:** `src/basic_api/schemas/user.py`, `src/basic_api/services/users.py`.

Emails are compared as typed (`A@x.com` and `a@x.com` are two accounts and
login is case-sensitive); phone numbers have no format rule; neither is ever
verified, so an account can claim someone else's address.

**Fix:** lower-case emails before storing and comparing, normalise phone numbers
(E.164), and add verification before either is used for anything that matters,
such as password recovery.

### The API key is a client identifier, not a security layer

**Where:** `src/basic_api/security.py`.

A key shipped inside a mobile or browser application can be extracted from it.
It tells your own clients from random traffic; it keeps nobody out. The code
and docs say so; this entry is here so nobody designs as if it did.

**Fix:** none needed; protection comes from per-user tokens and rate limits.

### CORS allows every origin by default

**Where:** `src/basic_api/config.py` (`CORS_ORIGINS`), `.env.example`.

`CORS_ORIGINS=*` suits an API consumed by native apps. A browser frontend that
stores the token must list its origins, or any site can call the API with the
visitor's credentials.

**Fix:** set `CORS_ORIGINS` to the frontend's origins in every deployment that
has one.

### Login identifiers can collide across columns

**Where:** `src/basic_api/auth.py` (`authenticate_user`), `src/basic_api/schemas/user.py` (`UserBase.username`).

Login matches the submitted identifier against `username`, `email` and
`phone_number` together and takes `.first()`. Each column is unique on its own,
but nothing stops one account's username from equalling another account's email
or phone number: `username` has no format rule. When two rows match, the
database picks one, and the other owner cannot log in with that identifier.

**Fix:** forbid usernames that look like an email address or a phone number
(a pattern on `username`), and check a new email or phone against the
`username` column too. Alternatively let the client say which kind of
identifier it sends.

### Password policy is length only

**Where:** `src/basic_api/schemas/user.py` (`UserCreateSchema.password`, `PasswordChangeSchema.new_password`).

Eight characters is the only rule. No maximum (harmless thanks to the SHA-256
pre-hash, but unbounded input nonetheless), no check against lists of breached
passwords, no rejection of the username or email as the password.

**Fix:** a maximum length, a breached-password check (the k-anonymity range API
of Have I Been Pwned, or a local list), and refusing passwords equal to the
account's identifiers.

---

## Data

### Schema is created at startup, not migrated

**Where:** `src/basic_api/database.py` (`init_db`).

`SQLModel.metadata.create_all` runs at every startup. It creates missing tables
and never alters an existing one: a new column, a changed type or a new
constraint on a table with data is silently not applied, and the code and the
database disagree from then on.

**Fix:** Alembic. Generate a baseline from the current models, run migrations as
a deploy step (not at app startup), and have the tests apply the same
migrations. Do it before the first schema change that follows real data.

---

## Operations

### Rate limits are per IP and per process

**Where:** `src/basic_api/limiter.py`.

Counts live in each process's memory. Several uvicorn workers multiply the
effective limit; a restart resets it. Behind a reverse proxy on another host,
uvicorn must be told to trust its forwarded headers (`--forwarded-allow-ips`),
or every client shares one bucket.

**Fix:** shared storage for the counts (slowapi supports Redis) when running
more than one worker.

### No logging configuration or observability

**Where:** application-wide.

Modules call `logging.getLogger(__name__)` but nothing configures logging;
output and level are whatever uvicorn sets. No request ids, no structured logs,
no metrics, no error tracking.

**Fix:** configure logging at startup (JSON in production), a request-id
middleware, and an error tracker.

### CI has no coverage, dependency audit or secret scan

**Where:** `.github/workflows/ci.yml`.

The pipeline formats, lints, type-checks and tests. It does not measure
coverage, check dependencies against known vulnerabilities, or scan for
committed secrets.

**Fix:** `pip-audit` and a secret scanner in `lint`; `pytest-cov` with a
threshold in `test`; Dependabot or Renovate for updates.

### No deployment story

**Where:** repository root, `docs/`.

The README calls the project production-shaped, but nothing says how to run it
in production: no container image, no service unit, no reverse-proxy example,
no request body size limit, no security headers, no HTTPS note. uvicorn alone
caps none of these. The documentation left deployment out of scope on purpose;
this entry records that so the claim and the contents agree.

**Fix:** a short deployment guide with a reverse proxy that terminates TLS,
sets security headers and caps request bodies, a process manager, and the
`ROOT_PATH` and forwarded-headers settings; a Dockerfile if the project will be
containerised.

---

## Code

### The demo route ships

**Where:** `src/basic_api/main.py` (`protected_example`).

`GET /protected-example` exists to show how to require both credentials. It is
live in every deployment of the starter.

**Fix:** delete it once a real protected route exists to point at.

### The OpenAPI document under-describes responses

**Where:** every route in `src/basic_api/main.py` and `src/basic_api/routers/`.

No route declares `responses=`, so the generated document lists only `200`,
`201` and `422`; the `401`, `403`, `409`, `429` and `503` paths described in
`docs/api.md` are absent from the spec and from any client generated from it.
`/token`, `/` and `/health` have no `response_model`, so the token response has
no schema at all.

**Fix:** a shared `responses` dictionary per auth level (API key only, API key
plus token) passed to the decorators, and small response models for the three
plain routes.

### Startup validation and the login limit are untested

**Where:** `src/basic_api/config.py`, `src/basic_api/limiter.py`, `tests/`.

The checks that refuse to start (required variables, secret length, algorithm
allow-list, bcrypt minimum, rate-limit syntax) run at import, and no test
exercises any of them. `RATE_LIMIT_LOGIN` is applied but only the registration
limit has a test.

**Fix:** move the checks into a `load_settings()` function that the module
calls once, and test the function; add a login-limit test alongside the
registration one.

### Application code detects the test runner

**Where:** `src/basic_api/config.py` (`TESTING`), `src/basic_api/database.py`.

`config.py` checks for `pytest` in `sys.modules` to build the database URL from
the `DB_*` variables and to disable connection pooling. It works, and the
reason for the pool change is real (each test owns an event loop), but
production code branching on the test runner is a smell: a future change can be
reached only by one of the two paths.

**Fix:** have the tests set `DATABASE_URL` explicitly and introduce a
`DATABASE_POOL` setting (`default` or `none`) that the fixtures set, so the
application reads configuration only.

### The root banner reports healthy without checking

**Where:** `src/basic_api/main.py` (`root`).

`GET /` returns `"status": "healthy"` as a literal, while `/health` now checks
the database and can answer `503`. A monitor pointed at `/` by mistake sees a
healthy service with its database down.

**Fix:** drop the `status` field from the banner, or have it call the same
`ping()` as `/health`.
