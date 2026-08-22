# API Reference

This document outlines the available API endpoints.

## Base URL

The API is served from the server root — `http://localhost:8000` in development.

Top-level routes (`/`, `/health`, `/token`, `/protected-example`) are declared on
the application itself. Router endpoints are mounted under `/api`, so the auth
and user routes below are reached at `/api/auth/...` and `/api/users/...`.

If you deploy behind a reverse proxy that serves the app under a subpath, set
`root_path` on the `FastAPI()` call in `main.py`, or pass
`uvicorn --root-path /your-prefix`, and prepend that prefix to every path here.

## Authentication Endpoints

### Get Current User
-   **URL**: `/auth/me`
-   **Method**: `GET`
-   **Description**: Retrieves information about the currently authenticated user.
-   **Headers**: `Authorization: Bearer <token>`
-   **Response**: `SuccessResponse[dict]`

### Logout
-   **URL**: `/auth/logout`
-   **Method**: `POST`
-   **Description**: Logs out the user (client-side token deletion).
-   **Headers**: `Authorization: Bearer <token>`
-   **Response**: `SuccessResponse[None]`

### Get Token
-   **URL**: `/token`
-   **Method**: `POST`
-   **Description**: Obtains an access token using username and password.
-   **Body**: `OAuth2PasswordRequestForm` (username, password)
-   **Response**: JSON with `access_token` and `token_type`.

## User Endpoints

### Create User
-   **URL**: `/users/`
-   **Method**: `POST`
-   **Description**: Creates a new user.
-   **Body**: `UserCreateSchema`
-   **Response**: `SuccessResponse[dict]`

## Health Check

-   **URL**: `/health`
-   **Method**: `GET`
-   **Description**: Checks the health status of the API.

## Protected Example

-   **URL**: `/protected-example`
-   **Method**: `GET`
-   **Description**: An example endpoint requiring authentication.
-   **Headers**: `Authorization: Bearer <token>`
