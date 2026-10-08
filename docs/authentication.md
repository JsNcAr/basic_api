# Authentication

Two credentials, with different jobs.

1. **Client API key**, `X-API-Key` header, on every `/api` route and
   `/protected-example`. It identifies your own client application; it is not a
   user credential and, shipped inside a mobile or browser app, it can be
   extracted. Use it to tell your clients from random traffic, and rely on
   tokens and rate limits for protection.
2. **Bearer token**, `Authorization: Bearer <jwt>`, on routes about a user.

`/`, `/health` and `/token` need neither, so monitors need no credentials and
Swagger's Authorize dialog can log in.

## Login

`POST /token` is the standard OAuth2 password form (`application/x-www-form-urlencoded`),
not JSON. The `username` field accepts a username, an email address or a phone
number; the server matches it against all three columns.

```bash
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=your-password"
```

```json
{"access_token": "eyJ...", "expires_in": 1800, "token_type": "bearer"}
```

`expires_in` is the lifetime granted, in seconds.

### Token lifetime

The default is `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (30). A client may ask for a
different one with the `expires_delta` query parameter, in seconds or as an ISO
8601 duration:

```bash
curl -X POST "http://localhost:8000/token?expires_delta=P1D" ...
```

The server decides: above `JWT_MAX_ACCESS_TOKEN_EXPIRE_MINUTES` (7 days by
default) the request is capped; omitted, zero or negative gets the default.

### What is in the token

The subject (`sub`) is the **user's UUID**, plus `iat` and `exp`. On every request
`get_current_user` loads the user by id and checks `is_active`, so:

- a deleted account's tokens are refused on the next request (`401 User not found`);
- a disabled account's tokens are refused (`403 This account is currently disabled`);
- a username released by a deletion and taken by a new account can never make
  an old token resolve to the new user.

What does **not** invalidate a token: logout, and a password change. Tokens are
stateless and live until `exp` (see [Known Issues](known_issues.md#tokens-cannot-be-revoked)).

## Security implementation

- **Password hashing**: bcrypt at `BCRYPT_ROUNDS` (minimum 12) over a SHA-256
  pre-hash, so passwords of any length are hashed in full. Hashing runs in a
  worker thread, not on the event loop.
- **Constant-time login**: when the identifier matches no account, the password
  is verified against a sentinel hash anyway, so timing does not reveal which
  accounts exist, and both failures return the same body.
- **Startup validation**: a `JWT_SECRET_KEY` under 32 bytes, an algorithm
  outside `HS256`/`HS384`/`HS512`, or fewer than 12 bcrypt rounds refuse to
  start (`config.py`).
- **Fixed error messages**: a failed token decode answers one message; the
  reason (expired, bad signature) goes to the log.
- **API key comparison** is constant-time (`secrets.compare_digest`).

## Rate limits

Per client IP, in `limits` syntax (`10/minute`, `100/hour`), per process.

| Route | Variable | Default |
|---|---|---|
| `POST /token` | `RATE_LIMIT_LOGIN` | `60/minute` |
| `POST /api/users/` | `RATE_LIMIT_REGISTER` | `10/minute` |

Over the limit: `429` with `{"detail": "Too many requests. Try again in N seconds."}`
and a `Retry-After` header. Clients should wait and retry, never treat it as
rejected credentials.

## Errors

### `POST /token`

| Status | `detail` | Meaning |
|---|---|---|
| `401` | `Incorrect username or password` | Unknown identifier **or** wrong password; deliberately the same |
| `403` | `This account is currently disabled` | Credentials correct, `is_active` is false |
| `422` | validation array | Missing form field |
| `429` | `Too many requests. Try again in N seconds.` | Rate limit |

### Any route with a bearer token

| Status | `detail` | Meaning |
|---|---|---|
| `401` | `Not authenticated` | No `Authorization` header |
| `401` | `Could not validate credentials` | Malformed, expired, wrongly signed, or subject not an id |
| `401` | `User not found` | Valid token, account deleted |
| `403` | `This account is currently disabled` | Valid token, account disabled |

### Any `/api` route

| Status | `detail` | Meaning |
|---|---|---|
| `401` | `Invalid or missing API key` | `X-API-Key` absent or wrong |

## Swagger

The OpenAPI document declares both schemes, `APIKeyHeader` and
`OAuth2PasswordBearer`. In `/docs`, Authorize once with the API key and once
with username and password, and every route is callable from the page.
