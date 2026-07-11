"""
FastAPI dependencies for the universal auth module.
"""
import inspect
from typing import Callable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from . import security
from .schemas import TokenData


def get_token_payload(
    token: str, secret_key: str, algorithm: str = "HS256"
) -> TokenData:
    """Decode an access token and return its payload."""
    payload = security.decode_access_token(token, secret_key, algorithm=algorithm)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email: Optional[str] = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenData(email=email, role=payload.get("role"))


def get_current_user_factory(
    get_user_by_email: Callable,
    secret_key: str,
    algorithm: str = "HS256",
    token_url: str = "/auth/login",
    required_roles: Optional[list[str]] = None,
):
    """
    Returns a FastAPI dependency that verifies the JWT token and fetches the user.

    Parameters
    ----------
    get_user_by_email:
        Callable that takes an email string and returns a User object (sync or async).
    secret_key:
        JWT secret key.
    algorithm:
        JWT algorithm (default HS256).
    token_url:
        URL used by OAuth2PasswordBearer to request a token.
    required_roles:
        Optional list of roles allowed to access the endpoint. If None, any authenticated user is allowed.
    """
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl=token_url)

    async def current_user(token: str = Depends(oauth2_scheme)):
        token_data = get_token_payload(token, secret_key, algorithm=algorithm)

        user_result = get_user_by_email(token_data.email)
        if inspect.isawaitable(user_result):
            user = await user_result
        else:
            user = user_result

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if getattr(user, "is_active", True) is False:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user",
            )

        if required_roles:
            user_role = getattr(user, "role", None) or token_data.role
            if user_role not in required_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )

        return user

    return current_user
