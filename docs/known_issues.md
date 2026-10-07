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
| Data | [Schema is created at startup, not migrated](#schema-is-created-at-startup-not-migrated) | High |
| Operations | [Rate limits are per IP and per process](#rate-limits-are-per-ip-and-per-process) | Low |
| Operations | [No logging configuration or observability](#no-logging-configuration-or-observability) | Medium |
| Operations | [CI has no coverage, dependency audit or secret scan](#ci-has-no-coverage-dependency-audit-or-secret-scan) | Low |
| Code | [The demo route ships](#the-demo-route-ships) | Low |

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

---

## Code

### The demo route ships

**Where:** `src/basic_api/main.py` (`protected_example`).

`GET /protected-example` exists to show how to require both credentials. It is
live in every deployment of the starter.

**Fix:** delete it once a real protected route exists to point at.
