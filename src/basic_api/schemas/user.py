from datetime import datetime
from typing import Optional

from pydantic import EmailStr, HttpUrl, TypeAdapter, ValidationError, field_validator
from sqlmodel import Field, SQLModel

from ..utils import utc_now

# Upper bounds on the free-text identity fields. Without them the columns are
# unlimited VARCHAR and a client can store megabytes per field. An email address
# is at most 254 characters (RFC 5321); the URL bound is pydantic's HttpUrl's.
USERNAME_MAX_LENGTH = 64
EMAIL_MAX_LENGTH = 254
PHONE_NUMBER_MAX_LENGTH = 32
URL_MAX_LENGTH = 2083

_HTTP_URL = TypeAdapter(HttpUrl)


def validate_http_url(value: Optional[str]) -> Optional[str]:
    """
    An http(s) URL as a string, or null.

    Applied at registration so that a javascript: or data: URL cannot be stored
    and later rendered as a link by a web client.

    Args:
        value: The URL as sent, or None.

    Returns:
        The URL as a normalised string, or None.

    Raises:
        ValueError: If the value is not an http or https URL.
    """
    if value is None:
        return None
    try:
        return str(_HTTP_URL.validate_python(value))
    except ValidationError:
        raise ValueError("profile_picture_url must be an http(s) URL")


# 1. Base model: fields shared by the table and the API schemas.
class UserBase(SQLModel):
    # Required and unique: it is what the user logs in with by default. Tokens
    # carry the user id, never this, so it can be changed later.
    username: str = Field(
        index=True,
        unique=True,
        max_length=USERNAME_MAX_LENGTH,
        description="Unique username",
    )
    email: Optional[EmailStr] = Field(
        default=None,
        index=True,
        unique=True,
        max_length=EMAIL_MAX_LENGTH,
        description="Email address; also accepted as the login identifier",
    )
    phone_number: Optional[str] = Field(
        default=None,
        index=True,
        unique=True,
        max_length=PHONE_NUMBER_MAX_LENGTH,
        description="Phone number; also accepted as the login identifier",
    )
    profile_picture_url: Optional[str] = Field(
        default=None,
        max_length=URL_MAX_LENGTH,
        description="http(s) URL of the profile picture",
    )
    is_active: bool = Field(
        default=True,
        description="A disabled account cannot log in or use its tokens",
    )


# 2. Table model.
class User(UserBase, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str = Field(description="bcrypt hash of the SHA-256 pre-hash")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: Optional[datetime] = Field(
        default=None, sa_column_kwargs={"onupdate": utc_now}
    )


# 3. Registration input.
class UserCreateSchema(UserBase):
    password: str = Field(..., min_length=8, description="At least 8 characters")

    _check_profile_picture_url = field_validator("profile_picture_url")(
        validate_http_url
    )


# 4. Profile update input (an endpoint for it arrives with user self-service).
class UserUpdateSchema(SQLModel):
    email: Optional[EmailStr] = Field(default=None, max_length=EMAIL_MAX_LENGTH)
    phone_number: Optional[str] = Field(
        default=None, max_length=PHONE_NUMBER_MAX_LENGTH
    )
    profile_picture_url: Optional[HttpUrl] = Field(default=None)


# 5. User as returned by the API: never the hash.
class UserResponseSchema(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
