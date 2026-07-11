"""
Pydantic schemas for the universal auth module.
"""
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Token(BaseModel):
    """Token pair returned after login."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Request body for refreshing an access token."""

    refresh_token: str


class TokenData(BaseModel):
    """Payload extracted from a verified access token."""

    email: Optional[str] = None
    role: Optional[str] = None


class UserBase(BaseModel):
    """Common user fields."""

    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Request body for user registration."""

    password: str = Field(..., min_length=8)
    role: Optional[str] = "user"


class UserLogin(BaseModel):
    """Request body for email/password login (non-OAuth2 form)."""

    email: EmailStr
    password: str


class UserResponse(UserBase):
    """Public user response."""

    id: str
    is_active: Optional[bool] = True
    is_verified: Optional[bool] = False
    role: Optional[str] = "user"

    @field_validator("id", mode="before")
    @classmethod
    def _id_to_str(cls, v: Any) -> str:
        return str(v) if not isinstance(v, str) else v

    model_config = ConfigDict(from_attributes=True)


class PasswordResetRequest(BaseModel):
    """Request body for initiating a password reset."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Request body for confirming a password reset."""

    token: str
    new_password: str = Field(..., min_length=8)


class EmailVerification(BaseModel):
    """Request body for verifying an email address."""

    token: str
