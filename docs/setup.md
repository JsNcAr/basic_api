# Setup Guide

This guide covers the steps to install, configure, and run the Basic API application.

## Prerequisites

- Python 3.13 or higher
- [Poetry](https://python-poetry.org/) for dependency management

## Installation

1.  **Install Poetry** (if not already installed):

    ```bash
    curl -sSL https://install.python-poetry.org | python3 -
    ```

2.  **Clone the repository**:

    ```bash
    git clone <repository-url>
    cd basic_api
    ```

3.  **Install dependencies**:

    ```bash
    poetry install
    ```

## Configuration

The application uses environment variables for configuration.

1.  **Create the `.env` file**:

    Copy the example configuration file:

    ```bash
    cp .env.example .env
    ```

2.  **Edit `.env`**:

    Open the `.env` file and set the following variables:

    -   `JWT_SECRET_KEY`: A secure random string for signing JWTs. You can generate one using:
        ```bash
        python -c "import secrets; print(secrets.token_urlsafe(32))"
        ```
    -   `JWT_ALGORITHM`: The algorithm used for JWT signing (default: `HS256`).
    -   `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: The lifetime of the access token in minutes (default: `30`).
    -   `ADMIN_USERNAME`: The username for the admin account.
    -   `ADMIN_PASSWORD_HASH`: The bcrypt hash of the admin password.

## Running the Application

### Development Mode

To run the API in development mode with hot-reloading:

```bash
PYTHONPATH=src poetry run uvicorn basic_api.main:app --reload --host 0.0.0.0 --port 8000
```

Or using the `--app-dir` flag:

```bash
poetry run uvicorn basic_api.main:app --reload --host 0.0.0.0 --port 8000 --app-dir src
```

### Production

For production deployment, omit the `--reload` flag:

```bash
poetry run uvicorn basic_api.main:app --host 0.0.0.0 --port 8000 --app-dir src
```

## Testing

To run the unit tests:

```bash
poetry run pytest
```
