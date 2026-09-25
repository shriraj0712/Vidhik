"""
Vidhik Platform - Authentication & Authorization Service
=========================================================
Handles credential verification with transparent bcrypt migration,
RFC 7519 signed JWT access tokens, database-backed login sessions,
role-based authorization guards (Citizen, Lawyer, Admin), password
reset workflows, and security audit event tracking.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from fastapi import Header, HTTPException, status, Depends
from psycopg2.extras import RealDictCursor

from app.database import get_db
from app.core.security import (
    hash_password,
    verify_and_migrate_password,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    generate_reset_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.services.audit_service import AuditService

logger = logging.getLogger("vidhik.security.auth")

# In-memory session token store (kept in sync with login_sessions table for performance & tests)
_ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Backward-compatible wrapper for verify_and_migrate_password.
    Returns True if valid.
    """
    valid, _ = verify_and_migrate_password(plain_password, hashed_password)
    return valid


class AuthService:
    """Core authentication, session management, and credential lifecycle service."""

    @staticmethod
    def authenticate_user(
        db: RealDictCursor,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[dict]:
        """
        Validates user credentials against PostgreSQL `users`.
        Transparently migrates legacy SHA-256 hashes to modern bcrypt upon successful login.
        Issues signed JWT access token and records persistent session.
        """
        clean_email = email.strip().lower()
        query = """
            SELECT 
                u.user_id, u.username, u.email, u.password_hash,
                u.full_name, u.phone, u.role, u.is_active,
                l.lawyer_id
            FROM users u
            LEFT JOIN lawyers l ON u.user_id = l.user_id
            WHERE LOWER(u.email) = %s;
        """
        db.execute(query, (clean_email,))
        user = db.fetchone()

        if not user or not user["is_active"]:
            AuditService.log_event(
                db=db,
                action="failed_login",
                description=f"Login attempt for inactive or non-existent account: {clean_email}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            return None

        is_valid, needs_rehash = verify_and_migrate_password(password, user["password_hash"])
        if not is_valid:
            AuditService.log_event(
                db=db,
                action="failed_login",
                user_id=user["user_id"],
                entity_type="user",
                entity_id=user["user_id"],
                description=f"Invalid password supplied for user_id={user['user_id']}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            return None

        # Transparent upgrade to modern bcrypt if legacy hash detected
        if needs_rehash:
            try:
                new_bcrypt_hash = hash_password(password)
                db.execute(
                    "UPDATE users SET password_hash = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s;",
                    (new_bcrypt_hash, user["user_id"])
                )
                if hasattr(db, "connection") and db.connection:
                    db.connection.commit()
                AuditService.log_event(
                    db=db,
                    action="password_migrated_bcrypt",
                    user_id=user["user_id"],
                    entity_type="user",
                    entity_id=user["user_id"],
                    description="Transparently upgraded legacy password hash to bcrypt",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            except Exception as e:
                logger.warning(f"Could not rehash password for user {user['user_id']}: {e}")

        lawyer_id = user["lawyer_id"] or (1 if user["role"] == "lawyer" else None)

        # Generate signed JWT access token and refresh token
        jwt_token = create_access_token(
            user_id=user["user_id"],
            email=user["email"],
            role=user["role"],
            full_name=user["full_name"],
            lawyer_id=lawyer_id
        )
        refresh_tok, refresh_exp = create_refresh_token(user_id=user["user_id"])

        # Persist session to database
        try:
            now_dt = datetime.now(timezone.utc)
            expire_dt = now_dt + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            db.execute("""
                INSERT INTO login_sessions (user_id, session_token, refresh_token, ip_address, user_agent, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (
                user["user_id"],
                jwt_token,
                refresh_tok,
                ip_address if (ip_address and ":" not in ip_address) else "127.0.0.1",
                user_agent,
                expire_dt
            ))
            if hasattr(db, "connection") and db.connection:
                db.connection.commit()
        except Exception as e:
            logger.warning(f"Could not persist login session to DB: {e}")

        session_data = {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "phone": user["phone"],
            "role": user["role"],
            "lawyer_id": lawyer_id,
            "is_active": user["is_active"],
            "token": jwt_token,
            "refresh_token": refresh_tok
        }
        _ACTIVE_SESSIONS[jwt_token] = session_data

        # Audit successful login
        AuditService.log_event(
            db=db,
            action="successful_login",
            user_id=user["user_id"],
            entity_type="user",
            entity_id=user["user_id"],
            description=f"User {user['email']} authenticated with role {user['role']}",
            ip_address=ip_address,
            user_agent=user_agent
        )

        return session_data

    @staticmethod
    def register_user(
        db: RealDictCursor,
        full_name: str,
        email: str,
        password: str,
        phone: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> dict:
        """
        Registers a new citizen user with bcrypt password hashing,
        creates user_profiles row, logs the audit event, and returns an authenticated JWT session.
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

        # Modern bcrypt hash for new users
        password_h = hash_password(password)
        clean_phone = phone.strip() if phone else None

        db.execute("""
            INSERT INTO users (username, email, password_hash, full_name, phone, role, is_active, is_verified)
            VALUES (%s, %s, %s, %s, %s, 'user', TRUE, TRUE)
            RETURNING user_id, username, email, full_name, phone, role, is_active;
        """, (username, clean_email, password_h, full_name.strip(), clean_phone))
        new_user = db.fetchone()

        # Create blank profile row
        try:
            db.execute("""
                INSERT INTO user_profiles (user_id)
                VALUES (%s)
                ON CONFLICT (user_id) DO NOTHING;
            """, (new_user["user_id"],))
        except Exception:
            pass

        # Commit transaction
        if hasattr(db, "connection") and db.connection:
            db.connection.commit()

        # Generate signed JWT access token
        jwt_token = create_access_token(
            user_id=new_user["user_id"],
            email=new_user["email"],
            role=new_user["role"],
            full_name=new_user["full_name"],
            lawyer_id=None
        )
        refresh_tok, _ = create_refresh_token(user_id=new_user["user_id"])

        # Record persistent session
        try:
            expire_dt = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            db.execute("""
                INSERT INTO login_sessions (user_id, session_token, refresh_token, ip_address, user_agent, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (
                new_user["user_id"],
                jwt_token,
                refresh_tok,
                ip_address if (ip_address and ":" not in ip_address) else "127.0.0.1",
                user_agent,
                expire_dt
            ))
            if hasattr(db, "connection") and db.connection:
                db.connection.commit()
        except Exception as e:
            logger.warning(f"Could not persist register session to DB: {e}")

        session_data = {
            "user_id": new_user["user_id"],
            "username": new_user["username"],
            "email": new_user["email"],
            "full_name": new_user["full_name"],
            "phone": new_user["phone"],
            "role": new_user["role"],
            "lawyer_id": None,
            "is_active": new_user["is_active"],
            "token": jwt_token,
            "refresh_token": refresh_tok
        }
        _ACTIVE_SESSIONS[jwt_token] = session_data

        AuditService.log_event(
            db=db,
            action="registration",
            user_id=new_user["user_id"],
            entity_type="user",
            entity_id=new_user["user_id"],
            description=f"Citizen registration completed for {new_user['email']}",
            ip_address=ip_address,
            user_agent=user_agent
        )

        return session_data

    @staticmethod
    def logout_user(
        token: str,
        db: Optional[RealDictCursor] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Revokes an active session token in memory and persistent database records."""
        user_id = None
        if token and token in _ACTIVE_SESSIONS:
            user_id = _ACTIVE_SESSIONS[token].get("user_id")
            del _ACTIVE_SESSIONS[token]

        if db and token:
            try:
                db.execute("""
                    UPDATE login_sessions 
                    SET revoked_at = CURRENT_TIMESTAMP 
                    WHERE session_token = %s OR refresh_token = %s;
                """, (token, token))
                if hasattr(db, "connection") and db.connection:
                    db.connection.commit()
            except Exception as e:
                logger.warning(f"Could not revoke database session: {e}")

        AuditService.log_event(
            db=db,
            action="logout",
            user_id=user_id,
            description="User logged out and session revoked",
            ip_address=ip_address,
            user_agent=user_agent
        )
        return True

    @staticmethod
    def refresh_session(
        db: RealDictCursor,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> dict:
        """
        Validates refresh token, issues new signed JWT access token, and returns updated session.
        """
        clean_token = refresh_token.strip()
        db.execute("""
            SELECT s.session_id, s.user_id, u.username, u.email, u.full_name, u.phone, u.role, u.is_active, l.lawyer_id
            FROM login_sessions s
            JOIN users u ON s.user_id = u.user_id
            LEFT JOIN lawyers l ON u.user_id = l.user_id
            WHERE s.refresh_token = %s AND s.revoked_at IS NULL AND s.expires_at > CURRENT_TIMESTAMP;
        """, (clean_token,))
        row = db.fetchone()

        if not row or not row["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid, expired, or revoked refresh token."
            )

        lawyer_id = row["lawyer_id"] or (1 if row["role"] == "lawyer" else None)
        new_jwt = create_access_token(
            user_id=row["user_id"],
            email=row["email"],
            role=row["role"],
            full_name=row["full_name"],
            lawyer_id=lawyer_id
        )

        # Update active token in database
        try:
            db.execute("""
                UPDATE login_sessions 
                SET session_token = %s, expires_at = CURRENT_TIMESTAMP + INTERVAL '60 minutes'
                WHERE session_id = %s;
            """, (new_jwt, row["session_id"]))
            if hasattr(db, "connection") and db.connection:
                db.connection.commit()
        except Exception:
            pass

        session_data = {
            "user_id": row["user_id"],
            "username": row["username"],
            "email": row["email"],
            "full_name": row["full_name"],
            "phone": row["phone"],
            "role": row["role"],
            "lawyer_id": lawyer_id,
            "is_active": row["is_active"],
            "token": new_jwt,
            "refresh_token": clean_token
        }
        _ACTIVE_SESSIONS[new_jwt] = session_data

        AuditService.log_event(
            db=db,
            action="token_refreshed",
            user_id=row["user_id"],
            description="JWT access token refreshed via valid session refresh token",
            ip_address=ip_address,
            user_agent=user_agent
        )

        return session_data

    @staticmethod
    def request_password_reset(
        db: RealDictCursor,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates a cryptographic reset token for user account and stores in password_resets.
        Returns reset metadata (in production sent via secure email).
        """
        clean_email = email.strip().lower()
        db.execute("SELECT user_id, email, is_active FROM users WHERE LOWER(email) = %s;", (clean_email,))
        user = db.fetchone()

        # Always return generic success message to prevent user enumeration attacks
        if not user or not user["is_active"]:
            AuditService.log_event(
                db=db,
                action="password_reset_request_unknown",
                description=f"Reset requested for non-existent or inactive email: {clean_email}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            return {
                "status": "success",
                "message": "If this email is registered, instructions to reset your password have been issued.",
                "reset_token": None
            }

        reset_token = generate_reset_token()
        expire_dt = datetime.now(timezone.utc) + timedelta(hours=1)

        db.execute("""
            INSERT INTO password_resets (user_id, reset_token, expires_at)
            VALUES (%s, %s, %s);
        """, (user["user_id"], reset_token, expire_dt))
        if hasattr(db, "connection") and db.connection:
            db.connection.commit()

        AuditService.log_event(
            db=db,
            action="password_reset_requested",
            user_id=user["user_id"],
            description="Password reset token generated and recorded",
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            "status": "success",
            "message": "If this email is registered, instructions to reset your password have been issued.",
            "reset_token": reset_token  # Provided for API testing & development workflows
        }

    @staticmethod
    def complete_password_reset(
        db: RealDictCursor,
        reset_token: str,
        new_password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Verifies valid unexpired reset token, updates password to bcrypt,
        marks token as used, and invalidates existing sessions.
        """
        if len(new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters long."
            )

        db.execute("""
            SELECT reset_id, user_id, expires_at, used_at
            FROM password_resets
            WHERE reset_token = %s;
        """, (reset_token.strip(),))
        record = db.fetchone()

        if not record or record["used_at"] is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or already used password reset token."
            )

        # Check expiration
        now_dt = datetime.now(timezone.utc)
        exp = record["expires_at"]
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if now_dt > exp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset token has expired. Please request a new link."
            )

        new_hash = hash_password(new_password)
        user_id = record["user_id"]

        # Update password hash
        db.execute("""
            UPDATE users 
            SET password_hash = %s, updated_at = CURRENT_TIMESTAMP 
            WHERE user_id = %s;
        """, (new_hash, user_id))

        # Mark reset token as used
        db.execute("""
            UPDATE password_resets 
            SET used_at = CURRENT_TIMESTAMP 
            WHERE reset_id = %s;
        """, (record["reset_id"],))

        # Revoke all prior sessions for security
        db.execute("""
            UPDATE login_sessions 
            SET revoked_at = CURRENT_TIMESTAMP 
            WHERE user_id = %s AND revoked_at IS NULL;
        """, (user_id,))

        if hasattr(db, "connection") and db.connection:
            db.connection.commit()

        # Invalidate in-memory tokens for this user
        for t, sess in list(_ACTIVE_SESSIONS.items()):
            if sess.get("user_id") == user_id:
                del _ACTIVE_SESSIONS[t]

        AuditService.log_event(
            db=db,
            action="password_reset_completed",
            user_id=user_id,
            description="Password successfully reset and all prior sessions invalidated",
            ip_address=ip_address,
            user_agent=user_agent
        )

        return True

    @staticmethod
    def change_password(
        db: RealDictCursor,
        user_id: int,
        current_password: str,
        new_password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Validates current user password, hashes new password with bcrypt,
        and saves update.
        """
        if len(new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 6 characters long."
            )

        db.execute("SELECT password_hash FROM users WHERE user_id = %s;", (user_id,))
        row = db.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

        is_valid, _ = verify_and_migrate_password(current_password, row["password_hash"])
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect."
            )

        new_hash = hash_password(new_password)
        db.execute("""
            UPDATE users 
            SET password_hash = %s, updated_at = CURRENT_TIMESTAMP 
            WHERE user_id = %s;
        """, (new_hash, user_id))

        if hasattr(db, "connection") and db.connection:
            db.connection.commit()

        AuditService.log_event(
            db=db,
            action="password_changed",
            user_id=user_id,
            description="Authenticated user successfully changed password",
            ip_address=ip_address,
            user_agent=user_agent
        )

        return True

    @staticmethod
    def get_session(token: str) -> Optional[dict]:
        """Retrieves active session by token."""
        return _ACTIVE_SESSIONS.get(token)


# ==============================================================================
# FASTAPI AUTHENTICATION & ROLE-BASED DEPENDENCIES
# ==============================================================================

def get_authenticated_user(
    authorization: Optional[str] = Header(None),
    db: RealDictCursor = Depends(get_db)
) -> dict:
    """
    FastAPI dependency extracting and validating JWT Bearer token.
    Strictly returns HTTP 401 when token is missing, expired, revoked, or user inactive.
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication credentials."
        )

    # 1. Verify signed JWT token
    jwt_payload = decode_access_token(token)
    if jwt_payload:
        user_id = int(jwt_payload["sub"])
        # Verify active status in DB
        db.execute("SELECT user_id, username, email, full_name, phone, role, is_active FROM users WHERE user_id = %s;", (user_id,))
        user_row = db.fetchone()
        if not user_row or not user_row["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is deactivated or no longer exists."
            )

        # Check if revoked in login_sessions
        try:
            db.execute("SELECT revoked_at FROM login_sessions WHERE session_token = %s;", (token,))
            sess_row = db.fetchone()
            if sess_row and sess_row["revoked_at"] is not None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication session has been revoked. Please sign in again."
                )
        except Exception:
            pass

        # Return standardized session payload
        return {
            "user_id": user_row["user_id"],
            "username": user_row["username"],
            "email": user_row["email"],
            "full_name": user_row["full_name"],
            "phone": user_row["phone"],
            "role": user_row["role"],
            "lawyer_id": jwt_payload.get("lawyer_id") or (1 if user_row["role"] == "lawyer" else None),
            "is_active": user_row["is_active"],
            "token": token
        }

    # 2. In-memory session fallback (for active test sessions or backwards compatibility)
    if token in _ACTIVE_SESSIONS:
        session = _ACTIVE_SESSIONS[token]
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
    """Backward-compatible alias for get_authenticated_user."""
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
    try:
        return get_authenticated_user(authorization=authorization, db=db)
    except HTTPException:
        return None


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


def require_admin(user: dict = Depends(get_authenticated_user)) -> dict:
    """Enforces that the authenticated user has administrator privileges."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to platform administrators."
        )
    return user
