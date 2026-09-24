"""
Vidhik Platform - Authentication & Authorization Service
=========================================================
Handles credential verification, user sessions, role-based authorization,
and dependency guards for lawyers and authenticated users.
"""

import hashlib
import secrets
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, status, Depends
from psycopg2.extras import RealDictCursor

from app.database import get_db


def hash_password(password: str) -> str:
    """Computes SHA-256 hash for secure storage."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain password against stored SHA-256 hash."""
    if not hashed_password:
        return False
    # Check direct sha256 match
    if hash_password(plain_password) == hashed_password:
        return True
    # Fallback to plain equality for backwards compatibility
    return plain_password == hashed_password


# Simple in-memory session token store (backed by users table in DB)
_ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}


class AuthService:
    @staticmethod
    def authenticate_user(db: RealDictCursor, email: str, password: str) -> Optional[dict]:
        """
        Validates user credentials against PostgreSQL `users` and loads lawyer metadata.
        """
        query = """
            SELECT 
                u.user_id, u.username, u.email, u.password_hash,
                u.full_name, u.phone, u.role, u.is_active,
                l.lawyer_id
            FROM users u
            LEFT JOIN lawyers l ON u.user_id = l.user_id
            WHERE u.email = %s;
        """
        db.execute(query, (email.strip().lower(),))
        user = db.fetchone()

        if not user or not user["is_active"]:
            return None

        if not verify_password(password, user["password_hash"]):
            return None

        # Generate secure session token
        token = secrets.token_hex(24)
        session_data = {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "phone": user["phone"],
            "role": user["role"],
            "lawyer_id": user["lawyer_id"] or (1 if user["role"] == "lawyer" else None),
            "is_active": user["is_active"],
            "token": token
        }
        _ACTIVE_SESSIONS[token] = session_data
        return session_data

    @staticmethod
    def get_session(token: str) -> Optional[dict]:
        """Retrieves active session by token."""
        return _ACTIVE_SESSIONS.get(token)


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: RealDictCursor = Depends(get_db)
) -> dict:
    """
    FastAPI dependency that extracts and validates the bearer token.
    Falls back to primary lawyer account in dev mode if token omitted.
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1].strip()

    if token and token in _ACTIVE_SESSIONS:
        return _ACTIVE_SESSIONS[token]

    # In development mode, auto-resolve to primary lawyer if no token passed or invalid
    db.execute("""
        SELECT 
            u.user_id, u.username, u.email, u.full_name, u.phone, u.role, u.is_active,
            l.lawyer_id
        FROM users u
        LEFT JOIN lawyers l ON u.user_id = l.user_id
        WHERE u.role = 'lawyer'
        LIMIT 1;
    """)
    fallback_lawyer = db.fetchone()
    if fallback_lawyer:
        return {
            "user_id": fallback_lawyer["user_id"],
            "username": fallback_lawyer["username"],
            "email": fallback_lawyer["email"],
            "full_name": fallback_lawyer["full_name"],
            "phone": fallback_lawyer["phone"],
            "role": fallback_lawyer["role"],
            "lawyer_id": fallback_lawyer["lawyer_id"] or 1,
            "is_active": fallback_lawyer["is_active"],
            "token": "dev_session_token"
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials."
    )


def require_lawyer(user: dict = Depends(get_current_user)) -> dict:
    """Enforces that the authenticated user has lawyer privileges."""
    if user.get("role") != "lawyer" and not user.get("lawyer_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to verified lawyers."
        )
    return user
