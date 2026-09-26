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
    def register_user(
        db: RealDictCursor,
        full_name: str,
        email: str,
        password: str,
        phone: Optional[str] = None
    ) -> dict:
        """
        Registers a new citizen user, validates uniqueness, creates user_profiles row,
        and generates an authenticated session token.
        """
        clean_email = email.strip().lower()
        if not clean_email or "@" not in clean_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Valid email address is required."
            )
        if len(password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters long."
            )
        if not full_name or len(full_name.strip()) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Full name must be at least 2 characters long."
            )

        # Check for duplicate email
        db.execute("SELECT user_id FROM users WHERE LOWER(email) = %s;", (clean_email,))
        if db.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered. Please sign in instead."
            )

        # Generate unique username from email
        base_username = clean_email.split("@")[0].replace(".", "_")[:40]
        username = base_username
        counter = 1
        while True:
            db.execute("SELECT user_id FROM users WHERE username = %s;", (username,))
            if not db.fetchone():
                break
            username = f"{base_username}_{counter}"
            counter += 1

        password_h = hash_password(password)
        clean_phone = phone.strip() if phone else None

        db.execute("""
            INSERT INTO users (username, email, password_hash, full_name, phone, role, is_active, is_verified)
            VALUES (%s, %s, %s, %s, %s, 'user', TRUE, TRUE)
            RETURNING user_id, username, email, full_name, phone, role, is_active;
        """, (username, clean_email, password_h, full_name.strip(), clean_phone))
        new_user = db.fetchone()
        if not new_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user record."
            )

        # Create blank profile row
        db.execute("""
            INSERT INTO user_profiles (user_id)
            VALUES (%s)
            ON CONFLICT (user_id) DO NOTHING;
        """, (new_user["user_id"],))

        # Commit transaction
        db.connection.commit()

        # Generate session token
        token = secrets.token_hex(24)
        session_data = {
            "user_id": new_user["user_id"],
            "username": new_user["username"],
            "email": new_user["email"],
            "full_name": new_user["full_name"],
            "phone": new_user["phone"],
            "role": new_user["role"],
            "lawyer_id": None,
            "is_active": new_user["is_active"],
            "token": token
        }
        _ACTIVE_SESSIONS[token] = session_data
        return session_data

    @staticmethod
    def logout_user(token: str) -> bool:
        """Revokes an active session token."""
        if token and token in _ACTIVE_SESSIONS:
            del _ACTIVE_SESSIONS[token]
            return True
        return False

    @staticmethod
    def get_session(token: str) -> Optional[dict]:
        """Retrieves active session by token."""
        return _ACTIVE_SESSIONS.get(token)


def get_authenticated_user(
    authorization: Optional[str] = Header(None),
    db: RealDictCursor = Depends(get_db)
) -> dict:
    """
    FastAPI dependency that extracts and validates the Bearer token.
    Strictly returns HTTP 401 when authentication is missing or invalid.
    No silent fallback.
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication credentials."
        )

    if token in _ACTIVE_SESSIONS:
        session = _ACTIVE_SESSIONS[token]
        # Verify user is active
        db.execute("SELECT is_active, role FROM users WHERE user_id = %s;", (session["user_id"],))
        user_row = db.fetchone()
        if not user_row or not user_row["is_active"]:
            _ACTIVE_SESSIONS.pop(token, None)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is deactivated or no longer exists."
            )
        return session

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session expired or invalid authentication token."
    )


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: RealDictCursor = Depends(get_db)
) -> dict:
    """
    Backward-compatible alias for get_authenticated_user.
    Strictly requires valid authentication.
    """
    return get_authenticated_user(authorization, db)


def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: RealDictCursor = Depends(get_db)
) -> Optional[dict]:
    """
    Optional user dependency: returns user session if valid token provided,
    otherwise returns None without raising an exception.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1].strip()
    return _ACTIVE_SESSIONS.get(token)


def require_citizen(user: dict = Depends(get_authenticated_user)) -> dict:
    """Enforces that the authenticated user has citizen/user privileges."""
    if user.get("role") not in ("user", "citizen", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to citizen users."
        )
    return user


def require_lawyer(user: dict = Depends(get_authenticated_user)) -> dict:
    """Enforces that the authenticated user has lawyer privileges."""
    if user.get("role") != "lawyer" and not user.get("lawyer_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to verified lawyers."
        )
    return user
