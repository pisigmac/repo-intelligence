"""
Universal JWT authentication module for FastAPI applications.

Provides:
- Password hashing and verification (bcrypt)
- JWT access / refresh / verification / reset tokens
- Pluggable FastAPI dependencies (`get_current_user_factory`)
- Pluggable auth router (`AuthRouter`) with register / login / refresh endpoints
- Optional email verification and password reset token helpers
- GitHub OAuth Authentication
"""

from .core import GitHubAuthenticator
from .dependencies import get_current_user_factory
from .router import AuthRouter
from .schemas import (
    Token,
    TokenRefresh,
    TokenData,
    UserCreate,
    UserLogin,
    UserResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
    EmailVerification,
)
from .security import (
    create_access_token,
    create_refresh_token,
    create_verification_token,
    create_password_reset_token,
    decode_access_token,
    decode_refresh_token,
    decode_verification_token,
    decode_password_reset_token,
    get_password_hash,
    verify_password,
)

__all__ = [
    "GitHubAuthenticator",
    "AuthRouter",
    "get_current_user_factory",
    "Token",
    "TokenRefresh",
    "TokenData",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "EmailVerification",
    "create_access_token",
    "create_refresh_token",
    "create_verification_token",
    "create_password_reset_token",
    "decode_access_token",
    "decode_refresh_token",
    "decode_verification_token",
    "decode_password_reset_token",
    "get_password_hash",
    "verify_password",
]
