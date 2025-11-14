from pydantic import BaseModel, Field, ConfigDict, EmailStr, HttpUrl
from typing import Optional
from .base import BaseSchema
from typing import Literal

class UserSchema(BaseSchema):
    username: str = Field(..., description="The unique username of the user")
    email: EmailStr = Field(..., description="The email address of the user")
    phone_number: Optional[str] = Field(None, description="The phone number of the user")
    profile_picture_url: Optional[HttpUrl] = Field(None, description="URL to the user's profile picture")
    is_active: bool = Field(..., description="Indicates whether the user is active")
    bluetooth_address: Optional[str] = Field(None, description="The Bluetooth address of the user")
    wifi_mac_address: Optional[str] = Field(None, description="The WiFi MAC address of the user")
    
class UserCreateSchema(UserSchema):
    password: str = Field(..., min_length=8, description="The password for the user account (min 8 chars)")
    
class UserUpdateSchema(BaseSchema):
    email: Optional[EmailStr] = Field(None, description="The email address of the user")
    phone_number: Optional[str] = Field(None, description="The phone number of the user")
    profile_picture_url: Optional[HttpUrl] = Field(None, description="URL to the user's profile picture")
    is_active: Optional[bool] = Field(None, description="Indicates whether the user is active")
    password: Optional[str] = Field(None, min_length=8, description="The password for the user account (min 8 chars)")
    
class UserResponseSchema(UserSchema):
    pass
    
    
class UserLoginSchema(BaseModel):
    identifier: str = Field(..., description="Username, email, or phone number")
    type: Literal["username", "email", "phone_number"] = Field(..., description="Type of identifier provided")
    password: str = Field(..., description="The password for the user account")