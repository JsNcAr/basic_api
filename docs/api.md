# API Reference

This document outlines the available API endpoints.

## Base URL

The API is served at the root path defined in the application (default: `/korvyn` or `/back` depending on configuration, check `main.py` and `README.md`). Based on `main.py`, the `root_path` is set to `/korvyn`. However, the README mentions `/back`. Please verify your deployment configuration.

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
-   **URL**: `/token` (or `/back/token` as per README)
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

-   **URL**: `/health` (or `/back/health`)
-   **Method**: `GET`
-   **Description**: Checks the health status of the API.

## Protected Example

-   **URL**: `/protected-example` (or `/back/protected-example`)
-   **Method**: `GET`
-   **Description**: An example endpoint requiring authentication.
-   **Headers**: `Authorization: Bearer <token>`
