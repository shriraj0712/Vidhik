"""
Vidhik Platform - Centralized Security & Cryptographic Core
===========================================================
Handles modern bcrypt password hashing, legacy SHA-256 verification
with transparent upgrade detection, and RFC 7519 signed JWT token
creation and verification.
"""

import os
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
import jwt
import bcrypt

# ==============================================================================
# CONFIGURATION (Loaded from environment variables)
# ==============================================================================
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "vidhik-dev-insecure-jwt-secret-replace-in-production-2026")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


# ==============================================================================
# 1. PASSWORD HASHING & MIGRATION (BCRYPT + LEGACY SHA-256)
# ==============================================================================

def hash_password(password: str) -> str:
    """
    Hashes a plaintext password using modern bcrypt with auto-generated salt.
    Never logs or exposes the password.
    """
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def is_bcrypt_hash(hash_str: str) -> bool:
    """Determines whether a stored hash string is a standard bcrypt hash."""
    return hash_str.startswith("$2a$") or hash_str.startswith("$2b$") or hash_str.startswith("$2y$")


def verify_and_migrate_password(plain_password: str, stored_hash: Optional[str]) -> Tuple[bool, bool]:
    """
    Verifies a plaintext password against the stored database hash.

    Returns:
        (is_valid, needs_rehash)
        - is_valid: True if password matches the stored hash
        - needs_rehash: True if matched via legacy SHA-256 or plaintext fallback,
          indicating the database row should immediately be upgraded to modern bcrypt.
    """
    if not stored_hash or not plain_password:
        return False, False

    stored_hash_clean = stored_hash.strip()

    # 1. Modern bcrypt check
    if is_bcrypt_hash(stored_hash_clean):
        try:
            matched = bcrypt.checkpw(plain_password.encode("utf-8"), stored_hash_clean.encode("utf-8"))
            return matched, False
        except Exception:
            return False, False

    # 2. Legacy SHA-256 check (migration support)
    sha256_hash = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    if sha256_hash.lower() == stored_hash_clean.lower():
        # Valid credentials, but needs upgrade to bcrypt in database
        return True, True

    # 3. Legacy plaintext seed check (one-time test account migration)
    if plain_password == stored_hash_clean:
        return True, True

    return False, False


# ==============================================================================
# 2. JWT TOKEN GENERATION & VERIFICATION (RFC 7519)
# ==============================================================================

def create_access_token(
    user_id: int,
    email: str,
    role: str,
    full_name: Optional[str] = None,
    lawyer_id: Optional[int] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Generates a cryptographically signed JWT access token.
    Claims include sub, email, role, full_name, lawyer_id, iat, exp, and type='access'.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "user_id": user_id,
        "email": email.strip().lower(),
        "role": role,
        "full_name": full_name or "",
        "lawyer_id": lawyer_id,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access"
    }

    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(
    user_id: int,
    expires_delta: Optional[timedelta] = None
) -> Tuple[str, datetime]:
    """
    Generates a cryptographically secure refresh token string and expiration timestamp.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    token = secrets.token_urlsafe(32)
    return token, expire


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodes and verifies a JWT token's signature, expiration, and claims.
    Returns the payload dictionary if valid, or None if expired/tampered.
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub"]}
        )
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception):
        return None


def generate_reset_token() -> str:
    """Generates an unguessable 32-byte cryptographic token for password resets."""
    return secrets.token_urlsafe(32)
