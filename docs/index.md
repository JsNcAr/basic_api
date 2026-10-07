# basic-api documentation

A FastAPI starter with OAuth2 + JWT authentication over async PostgreSQL, a
client API key, rate limits, user self-service, tests and CI.

## Key points

- **Two credentials.** Every `/api` route needs the client API key in
  `X-API-Key`; routes about a user also need a bearer token. `/`, `/health` and
  `/token` need neither.
- **Tokens carry the user id** and the user is loaded on every request, so a
  deleted or disabled account loses access immediately.
- **Login is constant-time** and answers one message for an unknown account and
  a wrong password.
- **Configuration is one module** (`config.py`) that refuses to start on a
  missing or invalid value.
- **Rate limits** on login and registration; **health** checks the database.

## Navigation

- [Setup](setup.md): install, environment variables, run, test, code quality,
  adapting the starter to a new project.
- [Authentication](authentication.md): the API key, the login flow, token
  lifetime, what invalidates a token, rate limits, every error.
- [API Reference](api.md): every endpoint with status codes, the response
  envelope and the error shape.
- [Schemas](schemas.md): request and response models with their limits.
- [Known Issues](known_issues.md): what the starter deliberately leaves for a
  real project to decide.
- [Changelog](../CHANGELOG.md).
