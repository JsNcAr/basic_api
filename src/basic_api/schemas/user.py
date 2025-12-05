from typing import Optional, Literal
from datetime import datetime
from sqlmodel import SQLModel, Field
from pydantic import EmailStr, HttpUrl, model_validator, ConfigDict

# 1. Base Model: Shared fields for both DB and API
class UserBase(SQLModel):
    username: Optional[str] = Field(default=None, index=True, description="The unique username of the user")
    email: Optional[EmailStr] = Field(default=None, index=True, description="The email address of the user")
    phone_number: Optional[str] = Field(default=None, index=True, description="The phone number of the user")
    profile_picture_url: Optional[HttpUrl] = Field(default=None, description="URL to the user's profile picture")
    is_active: bool = Field(default=True, description="Indicates whether the user is active")
    bluetooth_address: Optional[str] = Field(default=None, description="The Bluetooth address of the user")
    wifi_mac_address: Optional[str] = Field(default=None, description="The WiFi MAC address of the user")

    model_config = ConfigDict(from_attributes=True)

# 2. Table Model: The actual Database Table
class User(UserBase, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str = Field(description="Hashed password stored in DB")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None, sa_column_kwargs={"onupdate": datetime.utcnow})
    is_deleted: bool = Field(default=False)

# 3. Create Schema: Input for creating a user
class UserCreateSchema(UserBase):
    password: str = Field(..., min_length=8, description="The password for the user account (min 8 chars)")

    @model_validator(mode="after")
    def check_identifiers(cls, values):
        if not (values.username or values.email or values.phone_number):
            raise ValueError("At least one of username, email, or phone_number must be provided.")
        return values

# 4. Update Schema: Input for updating a user
class UserUpdateSchema(SQLModel):
    email: Optional[EmailStr] = Field(default=None, description="The email address of the user")
    phone_number: Optional[str] = Field(default=None, description="The phone number of the user")
    profile_picture_url: Optional[HttpUrl] = Field(default=None, description="URL to the user's profile picture")
    is_active: Optional[bool] = Field(default=None, description="Indicates whether the user is active")
    password: Optional[str] = Field(default=None, min_length=8, description="The password for the user account (min 8 chars)")

# 5. Response Schema: Output for reading a user
class UserResponseSchema(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_deleted: bool = False

# 6. Login Schema: API specific
class UserLoginSchema(SQLModel):
    identifier: str = Field(..., description="Username, email, or phone number")
    type: Literal["username", "email", "phone_number"] = Field(..., description="Type of identifier provided")
    password: str = Field(..., description="The password for the user account")
