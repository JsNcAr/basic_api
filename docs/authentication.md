# Authentication

The Basic API uses OAuth2 with Password Flow and JWT (JSON Web Tokens) for authentication.

## Overview

1.  **Login**: The client sends credentials (username/email/phone and password) to the token endpoint.
2.  **Token Generation**: If credentials are valid, the server generates a signed JWT containing user claims (e.g., username) and an expiration time.
3.  **Access**: The client includes this token in the `Authorization` header of subsequent requests to protected endpoints.
    ```text
    Authorization: Bearer <token>
    ```
4.  **Validation**: The server validates the token signature and expiration on each request.

## Multi-field Login

The system supports logging in with different identifiers. The login request payload structure is:

```json
{
  "identifier": "user@example.com",
  "type": "email",
  "password": "yourpassword"
}
```

-   `identifier`: The actual value (username, email, or phone number).
-   `type`: One of `"username"`, `"email"`, or `"phone_number"`.
-   `password`: The user's password.

## Security Implementation

-   **Password Hashing**: Passwords are hashed using `bcrypt`. To support long passwords, they are pre-hashed with SHA-256 before being passed to bcrypt.
-   **JWT Signing**: Tokens are signed using a secret key (`JWT_SECRET_KEY`) and an algorithm (default `HS256`).
-   **Stateless**: The server does not store active sessions. Logout is handled client-side by discarding the token.

## Configuration

Authentication settings are managed via environment variables:

-   `JWT_SECRET_KEY`: Critical for security. Must be kept secret.
-   `JWT_ALGORITHM`: Algorithm for signing tokens.
-   `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: Duration for which the token is valid.
