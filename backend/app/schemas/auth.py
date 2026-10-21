from datetime import datetime
from typing import Optional, Any, Dict
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.user import UserRole


class UserSignupRequest(BaseModel):
    restaurant_id: UUID
    display_name: str = Field(..., min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)
    preferred_language: str = Field("en", pattern="^(en|ur)$")
    role: Optional[UserRole] = UserRole.CUSTOMER


class UserLoginPasswordRequest(BaseModel):
    restaurant_id: UUID
    username: str = Field(..., description="Email address or phone number")
    password: str = Field(..., min_length=4)


class OTPRequest(BaseModel):
    destination: str = Field(..., description="Phone number or email to receive the OTP code")


class OTPVerifyLoginRequest(BaseModel):
    restaurant_id: UUID
    destination: str = Field(..., description="Phone number or email")
    code: str = Field(..., min_length=6, max_length=6, pattern="^[0-9]{6}$")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    restaurant_id: UUID
    user_id: UUID
    display_name: Optional[str] = None
    preferred_language: str = "en"


class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=2, max_length=100)
    preferred_language: Optional[str] = Field(None, pattern="^(en|ur)$")
    push_notifications_enabled: Optional[bool] = None


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    preferred_language: str
    push_notifications_enabled: bool


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    restaurant_id: UUID
    email: Optional[str] = None
    phone_number: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    profile: Optional[UserProfileResponse] = None


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    restaurant_id: UUID
    user_id: Optional[UUID] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime
