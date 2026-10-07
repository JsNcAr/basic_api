# AGENTS Guidelines for basic-api

FastAPI starter: OAuth2 + JWT, async PostgreSQL, client API key, rate limits.
Poetry-managed.

## Development Rules
* **Environment**: the app refuses to start without `DATABASE_URL`, `API_KEY`
  and a 32+ byte `JWT_SECRET_KEY` (`src/basic_api/config.py`); copy
  `.env.example` to `.env`. A dev machine may have no PostgreSQL: database
  tests then run only in CI.
* **Configuration**: add a variable in `config.py` and `.env.example` together;
  nothing else reads the environment.
* **Errors**: routers translate domain exceptions (`exceptions.py`) to status
  codes; services never import HTTP. Never put database error text in a
  response; log it with `logger.exception` and answer a generic message.
* **Docstrings**: Google style (`Args`, `Returns`, `Raises`, `Example`); route
  docstrings render in Swagger, keep the curl examples current.
* **Known issues**: `docs/known_issues.md` is the single list; remove an entry
  in the change that fixes it.
* **Style**: no emojis or em-dashes in code or docs; do not guess APIs,
  versions, flags or package names, verify in code or docs.

## Project Structure
```
src/basic_api/
  main.py          # app, /, /health, /token, /protected-example
  config.py        # every environment variable, read and validated once
  auth.py          # hashing, JWT, constant-time login
  security.py      # client API key (APIKeyHeader)
  dependencies.py  # get_current_user (token -> User from the database)
  database.py      # engine, session factory, create_all, ping
  limiter.py       # shared rate limiter and 429 response
  exceptions.py    # domain exceptions
  utils.py         # utc_now
  routers/         # auth (/api/auth), users (/api/users)
  schemas/         # user models and schemas, SuccessResponse
  services/        # business rules (users)
tests/             # conftest (test database), database-backed and pure tests
docs/              # setup, authentication, api, schemas, known_issues
```

## Common Commands
* **Start dev server**: `poetry run uvicorn basic_api.main:app --reload --app-dir src`
* **Test**: `poetry run pytest` (needs PostgreSQL; `--noconftest` plus the pure
  test files runs without one)
* **Format & lint**: `poetry run black src tests && poetry run flake8 src tests`
* **Type check**: `poetry run mypy`
* **Dependency audit**: `poetry run pip-audit` (CI runs it in `lint`)
* **Dependencies**: `poetry add <pkg>` (dev tools: `--group dev`), then `poetry install`.
  Ranges in `pyproject.toml` are open to the next major; `poetry.lock` is the pin.
  Update with `poetry update` (or `poetry lock --regenerate` for every transitive
  package) and run the suite. SQLAlchemy is held below 2.1 until it ships wheels.
* **Test database**: `createdb basic_api_test_db` and the `DB_*` variables
