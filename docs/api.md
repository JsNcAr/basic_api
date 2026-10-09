# API Reference

Base URL in development: `http://localhost:8000`. With `ROOT_PATH` set, prefix
every path with it.

## Conventions

**Success envelope**, on every `/api` route:

```json
{"success": true, "message": "...", "data": ...}
```

`/`, `/health` and `/token` return plain objects (the OAuth2 token response has
a fixed shape).

**Errors** are FastAPI's default body: `detail` holding a string, or a list of
validation errors for `422`. Every status a route can answer is declared in the
OpenAPI document (`/openapi.json`), so generated clients see them; the one
exception is `413`, which Starlette answers as plain text before the app runs.

```json
{"detail": "Not a valid request"}
```

**Request id**: every response carries `X-Request-ID`, generated (a UUIDv7)
unless the request supplied an acceptable one (1 to 128 characters of letters,
digits, `.`, `_` or `-`). The server's log lines for that request carry the
same id; quote it when reporting a problem.

**Rate limits**: `POST /token` and `POST /api/users/` answer with
`X-RateLimit-Limit`, `X-RateLimit-Remaining` and `X-RateLimit-Reset` (Unix
time at which the window resets); over the limit, a `429` with `Retry-After`.

**Auth** column: `key` is the `X-API-Key` header, `token` is
`Authorization: Bearer <jwt>`. See [Authentication](authentication.md) for the
error tables common to all protected routes.

## System

| Method | Path | Auth | Status | Response |
|---|---|---|---|---|
| `GET` | `/` | none | `200` | `{"message", "version", "status", "authentication"}` |
| `GET` | `/health` | none | `200` / `503` | `{"status": "healthy", "service": "basic-api", "database": "ok"}`; `503` with `"database": "unreachable"` when `SELECT 1` fails within 2 s |

## Authentication

| Method | Path | Auth | Status | Description |
|---|---|---|---|---|
| `POST` | `/token` | none, rate-limited | `200` | OAuth2 password form; returns `access_token`, `expires_in`, `token_type`. Optional `?expires_delta=` |
| `GET` | `/api/auth/me` | key + token | `200` | The authenticated user (`UserResponseSchema`) |
| `POST` | `/api/auth/logout` | key + token | `200` | Confirms; the client deletes its token. Nothing is invalidated server-side |

## Users

| Method | Path | Auth | Status | Description |
|---|---|---|---|---|
| `POST` | `/api/users/` | key, rate-limited | `201` | Register. `409` naming the taken field: `Username is already taken`, `Email address is already registered`, `Phone number is already associated with an account`; generic `409` if two registrations raced |
| `GET` | `/api/users/me` | key + token | `200` | Own profile |
| `PATCH` | `/api/users/me` | key + token | `200` | Change only the fields sent (`email`, `phone_number`, `profile_picture_url`); `null` clears, omitted leaves alone; `409` as above for a collision. `username`, `is_active` and `password` are ignored if sent |
| `POST` | `/api/users/me/change-password` | key + token | `200` | Body `{"current_password", "new_password"}`; `400 Incorrect current password`; `422` if the new one is under 8 characters |
| `DELETE` | `/api/users/me` | key + token | `200` | Body `{"password"}`; `400 Incorrect password`; `422` without it. Hard delete; tokens for the account are refused from the next request |

There is no user listing and no read-by-id.

## Example

| Method | Path | Auth | Status | Description |
|---|---|---|---|---|
| `GET` | `/protected-example` | key + token | `200` | Shows how to require both credentials; copy its signature for a new protected route |

## Status codes at a glance

| Code | When |
|---|---|
| `200` / `201` | Success; `201` only on registration |
| `400` | A confirmation password was wrong |
| `401` | Missing or invalid API key; missing, invalid or orphaned token; bad login |
| `403` | Account disabled |
| `409` | Username, email or phone number already in use |
| `413` | Request body over `MAX_REQUEST_BODY_BYTES` (1 MiB by default); plain-text body, answered before the route |
| `422` | Body or form fails validation (lengths, URL rule, required fields) |
| `429` | Rate limit; see `Retry-After` |
| `500` | Unexpected failure, logged server-side with a generic message |
| `503` | `/health` only: database unreachable |
