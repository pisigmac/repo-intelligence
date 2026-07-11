from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from typing import Any, Optional, Union

from jose import JWTError, jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEFAULT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 15
DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS = 7
DEFAULT_VERIFICATION_TOKEN_EXPIRE_HOURS = 24
DEFAULT_PASSWORD_RESET_TOKEN_EXPIRE_HOURS = 1


def _now() -> datetime:
    """Return a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a plain password with bcrypt."""
    return pwd_context.hash(password)


def _create_token(
    subject: Union[str, Any],
    secret_key: str,
    expires_delta: Optional[timedelta],
    algorithm: str,
    token_type: str,
    extra_claims: Optional[dict] = None,
) -> str:
    """Create a JWT with a token-type claim and optional extra claims."""
    expire = _now() + (expires_delta or timedelta(minutes=DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": token_type,
    }
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)


def _decode_token(token: str, secret_key: str, algorithm: str, expected_type: str) -> Optional[dict]:
    """Decode a JWT and validate its type and expiration."""
    try:
        decoded_token = jwt.decode(token, secret_key, algorithms=[algorithm])
    except JWTError:
        return None

    if decoded_token.get("type") != expected_type:
        return None

    exp = decoded_token.get("exp")
    if exp is None or exp < _now().timestamp():
        return None

    return decoded_token


def create_access_token(
    subject: Union[str, Any],
    secret_key: str,
    expires_delta: Optional[timedelta] = None,
    algorithm: str = DEFAULT_ALGORITHM,
    extra_claims: Optional[dict] = None,
) -> str:
    """Create a short-lived JWT access token."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token(
        subject, secret_key, expires_delta, algorithm, "access", extra_claims
    )


def create_refresh_token(
    subject: Union[str, Any],
    secret_key: str,
    expires_delta: Optional[timedelta] = None,
    algorithm: str = DEFAULT_ALGORITHM,
    extra_claims: Optional[dict] = None,
) -> str:
    """Create a longer-lived JWT refresh token."""
    if expires_delta is None:
        expires_delta = timedelta(days=DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS)
    return _create_token(
        subject, secret_key, expires_delta, algorithm, "refresh", extra_claims
    )


def create_verification_token(
    subject: Union[str, Any],
    secret_key: str,
    expires_delta: Optional[timedelta] = None,
    algorithm: str = DEFAULT_ALGORITHM,
) -> str:
    """Create an email-verification token."""
    if expires_delta is None:
        expires_delta = timedelta(hours=DEFAULT_VERIFICATION_TOKEN_EXPIRE_HOURS)
    extra = {"jti": token_urlsafe(16)}
    return _create_token(subject, secret_key, expires_delta, algorithm, "verification", extra)


def create_password_reset_token(
    subject: Union[str, Any],
    secret_key: str,
    expires_delta: Optional[timedelta] = None,
    algorithm: str = DEFAULT_ALGORITHM,
) -> str:
    """Create a password-reset token."""
    if expires_delta is None:
        expires_delta = timedelta(hours=DEFAULT_PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    extra = {"jti": token_urlsafe(16)}
    return _create_token(subject, secret_key, expires_delta, algorithm, "password_reset", extra)


def decode_access_token(
    token: str, secret_key: str, algorithm: str = DEFAULT_ALGORITHM
) -> Optional[dict]:
    """Decode and validate an access token."""
    return _decode_token(token, secret_key, algorithm, "access")


def decode_refresh_token(
    token: str, secret_key: str, algorithm: str = DEFAULT_ALGORITHM
) -> Optional[dict]:
    """Decode and validate a refresh token."""
    return _decode_token(token, secret_key, algorithm, "refresh")


def decode_verification_token(
    token: str, secret_key: str, algorithm: str = DEFAULT_ALGORITHM
) -> Optional[dict]:
    """Decode and validate an email-verification token."""
    return _decode_token(token, secret_key, algorithm, "verification")


def decode_password_reset_token(
    token: str, secret_key: str, algorithm: str = DEFAULT_ALGORITHM
) -> Optional[dict]:
    """Decode and validate a password-reset token."""
    return _decode_token(token, secret_key, algorithm, "password_reset")
