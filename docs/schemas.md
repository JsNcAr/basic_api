# Schemas

This section describes the data models used in the API.

## User Schemas

### UserSchema
Base schema for user data.

| Field | Type | Description |
| :--- | :--- | :--- |
| `username` | `str` | Unique username (optional) |
| `email` | `EmailStr` | Email address (optional) |
| `phone_number` | `str` | Phone number (optional) |
| `profile_picture_url` | `HttpUrl` | URL to profile picture (optional) |
| `is_active` | `bool` | Indicates if user is active |
| `bluetooth_address` | `str` | Bluetooth address (optional) |
| `wifi_mac_address` | `str` | WiFi MAC address (optional) |

### UserCreateSchema
Schema for creating a new user. Inherits from `UserSchema`.

-   **Additional Fields**:
    -   `password`: `str` (min length 8)
-   **Validation**: Requires at least one of `username`, `email`, or `phone_number`.

### UserUpdateSchema
Schema for updating user details.

| Field | Type | Description |
| :--- | :--- | :--- |
| `email` | `EmailStr` | Email address (optional) |
| `phone_number` | `str` | Phone number (optional) |
| `profile_picture_url` | `HttpUrl` | URL to profile picture (optional) |
| `is_active` | `bool` | Indicates if user is active (optional) |
| `password` | `str` | New password (optional, min length 8) |

### UserLoginSchema
Schema for login requests.

| Field | Type | Description |
| :--- | :--- | :--- |
| `identifier` | `str` | Username, email, or phone number |
| `type` | `str` | "username", "email", or "phone_number" |
| `password` | `str` | User password |

## Response Schemas

### SuccessResponse
Generic wrapper for successful API responses.

| Field | Type | Description |
| :--- | :--- | :--- |
| `success` | `bool` | Always `true` for success |
| `message` | `str` | Human-readable message |
| `data` | `T` | The actual response data (generic type) |
