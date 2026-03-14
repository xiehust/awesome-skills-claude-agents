"""JWT authentication utilities."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
import bcrypt

from config import settings


class TokenPayload:
    """Token payload data."""

    def __init__(
        self,
        sub: str,
        exp: datetime,
        token_type: str = "access",
        iat: Optional[datetime] = None,
    ):
        self.sub = sub  # Subject (user_id)
        self.exp = exp  # Expiration time
        self.token_type = token_type  # "access" or "refresh"
        self.iat = iat or datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    # bcrypt has a 72-byte limit; truncate to be safe
    password_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    password_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))


def create_access_token(user_id: str, tenant_id: str = "", role: str = "member", expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token.

    Args:
        user_id: The user's unique identifier
        tenant_id: The tenant ID to embed in the token
        role: The user's role within the tenant
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT access token
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {
        "sub": user_id,
        "tid": tenant_id,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }

    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(user_id: str, tenant_id: str = "", role: str = "member", expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT refresh token.

    Args:
        user_id: The user's unique identifier
        tenant_id: The tenant ID to embed in the token
        role: The user's role within the tenant
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT refresh token
    """
    if expires_delta is None:
        expires_delta = timedelta(days=settings.refresh_token_expire_days)

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {
        "sub": user_id,
        "tid": tenant_id,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }

    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """Verify a JWT token and return the token data.

    Args:
        token: The JWT token to verify
        token_type: Expected token type ("access" or "refresh")

    Returns:
        Dict with sub, tid, and role if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        # Check token type
        if payload.get("type") != token_type:
            return None

        # Check expiration
        exp = payload.get("exp")
        if exp is None:
            return None
        if datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            return None

        return {
            "sub": payload.get("sub"),
            "tid": payload.get("tid", ""),
            "role": payload.get("role", "member"),
        }

    except JWTError:
        return None


def decode_token(token: str) -> Optional[dict]:
    """Decode a JWT token without verification.

    Useful for extracting payload info before full verification.

    Args:
        token: The JWT token to decode

    Returns:
        Token payload dict or None if invalid
    """
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False},
        )
    except JWTError:
        return None


def create_token_pair(user_id: str, tenant_id: str = "", role: str = "member") -> tuple[str, str, int]:
    """Create both access and refresh tokens.

    Args:
        user_id: The user's unique identifier
        tenant_id: The tenant ID to embed in the tokens
        role: The user's role within the tenant

    Returns:
        Tuple of (access_token, refresh_token, expires_in_seconds)
    """
    access_token = create_access_token(user_id, tenant_id, role)
    refresh_token = create_refresh_token(user_id, tenant_id, role)
    expires_in = settings.access_token_expire_minutes * 60

    return access_token, refresh_token, expires_in
