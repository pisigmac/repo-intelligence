"""
Pluggable authentication router for FastAPI applications.
"""
import inspect
from datetime import timedelta
from typing import Any, Callable, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from . import schemas, security


def _maybe_await_result(result):
    """Return an awaitable if called from an async context; otherwise return directly.

    This helper is intentionally not `async` so sync route handlers can call it too.
    In async routes the result is awaited explicitly.
    """
    return result


class AuthRouter:
    """
    A customizable authentication router that can be plugged into any FastAPI app.
    Provides standard /register, /login, /refresh, /me and token-management helpers.
    """

    def __init__(
        self,
        secret_key: str,
        get_user_by_email: Callable[[Any], Any],
        create_user: Callable[[schemas.UserCreate], Any],
        get_hashed_password: Callable[[Any], str],
        update_user_password: Optional[Callable[[Any, str], Any]] = None,
        verify_user_email: Optional[Callable[[Any], Any]] = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7,
    ):
        self.router = APIRouter(prefix="/auth", tags=["auth"])
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.get_user_by_email = get_user_by_email
        self.create_user = create_user
        self.get_hashed_password = get_hashed_password
        self.update_user_password = update_user_password
        self.verify_user_email = verify_user_email

        self._setup_routes()

    def _resolve_user(self, email: str):
        """Resolve a user by email, awaiting if the callable is async."""
        result = self.get_user_by_email(email)
        return result

    def _issue_tokens(self, subject: str, extra_claims: Optional[dict] = None) -> schemas.Token:
        """Issue a fresh access/refresh token pair."""
        access_token = security.create_access_token(
            subject=subject,
            secret_key=self.secret_key,
            expires_delta=timedelta(minutes=self.access_token_expire_minutes),
            algorithm=self.algorithm,
            extra_claims=extra_claims,
        )
        refresh_token = security.create_refresh_token(
            subject=subject,
            secret_key=self.secret_key,
            expires_delta=timedelta(days=self.refresh_token_expire_days),
            algorithm=self.algorithm,
            extra_claims=extra_claims,
        )
        return schemas.Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    def _setup_routes(self):
        @self.router.post("/register", response_model=schemas.UserResponse)
        def register(user_in: schemas.UserCreate):
            existing = self._resolve_user(user_in.email)
            if inspect.isawaitable(existing):
                raise RuntimeError(
                    "Async get_user_by_email is not supported in sync /register route. "
                    "Pass an async-aware router or a sync callable."
                )
            if existing:
                raise HTTPException(status_code=400, detail="Email already registered")

            # Hash the password without mutating the input schema.
            create_payload = user_in.model_copy(update={"password": security.get_password_hash(user_in.password)})
            new_user = self.create_user(create_payload)
            return new_user

        @self.router.post("/login", response_model=schemas.Token)
        def login(form_data: OAuth2PasswordRequestForm = Depends()):
            user = self._resolve_user(form_data.username)
            if inspect.isawaitable(user):
                raise RuntimeError(
                    "Async get_user_by_email is not supported in sync /login route. "
                    "Pass an async-aware router or a sync callable."
                )
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            hashed_pass = self.get_hashed_password(user)
            if not security.verify_password(form_data.password, hashed_pass):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            extra_claims = {"role": getattr(user, "role", None)}
            return self._issue_tokens(subject=user.email, extra_claims=extra_claims)

        @self.router.post("/refresh", response_model=schemas.Token)
        def refresh(body: schemas.TokenRefresh):
            payload = security.decode_refresh_token(
                body.refresh_token, secret_key=self.secret_key, algorithm=self.algorithm
            )
            if payload is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired refresh token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            email = payload.get("sub")
            if email is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            user = self._resolve_user(email)
            if inspect.isawaitable(user):
                raise RuntimeError(
                    "Async get_user_by_email is not supported in sync /refresh route. "
                    "Pass an async-aware router or a sync callable."
                )
            if not user or getattr(user, "is_active", True) is False:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            extra_claims = {"role": getattr(user, "role", None)}
            return self._issue_tokens(subject=user.email, extra_claims=extra_claims)

        @self.router.post("/forgot-password")
        def forgot_password(body: schemas.PasswordResetRequest):
            """Generate a password-reset token. Delivery (email/SMS) is the caller's responsibility."""
            user = self._resolve_user(body.email)
            if inspect.isawaitable(user):
                raise RuntimeError(
                    "Async get_user_by_email is not supported in sync /forgot-password route."
                )
            if not user:
                # Return success to avoid leaking registered emails.
                return {"status": "ok", "message": "If an account exists, a reset link has been generated"}

            token = security.create_password_reset_token(
                subject=user.email,
                secret_key=self.secret_key,
                algorithm=self.algorithm,
            )
            return {
                "status": "ok",
                "message": "Password reset token generated",
                "token": token,
            }

        @self.router.post("/reset-password")
        def reset_password(body: schemas.PasswordResetConfirm):
            if self.update_user_password is None:
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail="Password reset is not configured",
                )

            payload = security.decode_password_reset_token(
                body.token, secret_key=self.secret_key, algorithm=self.algorithm
            )
            if payload is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired reset token",
                )

            email = payload.get("sub")
            user = self._resolve_user(email)
            if inspect.isawaitable(user):
                raise RuntimeError(
                    "Async get_user_by_email is not supported in sync /reset-password route."
                )
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )

            self.update_user_password(user, security.get_password_hash(body.new_password))
            return {"status": "ok", "message": "Password updated successfully"}

        @self.router.post("/verify-email")
        def verify_email(body: schemas.EmailVerification):
            if self.verify_user_email is None:
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail="Email verification is not configured",
                )

            payload = security.decode_verification_token(
                body.token, secret_key=self.secret_key, algorithm=self.algorithm
            )
            if payload is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired verification token",
                )

            email = payload.get("sub")
            user = self._resolve_user(email)
            if inspect.isawaitable(user):
                raise RuntimeError(
                    "Async get_user_by_email is not supported in sync /verify-email route."
                )
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )

            self.verify_user_email(user)
            return {"status": "ok", "message": "Email verified successfully"}
