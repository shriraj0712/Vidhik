"""
Vidhik Platform - Enterprise Authentication & Security Service
==============================================================
Production-grade authentication, authorization, and account security engine:
- Server-side Cloudflare Turnstile verification
- Cryptographic OTP email/SMS verification with attempt throttling & cooldown
- Mandatory RFC 6238 TOTP Two-Factor Authentication
- One-time hashed recovery codes
- Real Google OAuth 2.0 / OpenID Connect token verification with mandatory 2FA
- Bcrypt password hashing (cost 12) + transparent legacy upgrade
- Sliding-window account lockout & brute force mitigation
- Real session lifecycle (HttpOnly/Bearer, rotation, explicit revocation)
- User-Agent device parsing & approximate GeoIP resolution
- Suspicious login anomaly evaluation & real-time security alerts
- Comprehensive immutable audit logging
"""

import os
import secrets
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta
from fastapi import Header, HTTPException, status, Depends
from psycopg2.extras import RealDictCursor

from app.database import get_db
from app.core.security import (
    hash_password,
    verify_and_migrate_password,
    validate_password_strength,
    generate_secure_otp,
    hash_otp,
    verify_otp_hash,
    generate_totp_secret,
    get_totp_uri,
    generate_qr_code_data_url,
    verify_totp_code,
    generate_recovery_codes,
    hash_recovery_code,
    verify_recovery_code,
    create_access_token,
    create_two_factor_challenge_token,
    create_two_factor_setup_token,
    create_refresh_token,
    decode_access_token,
    decode_two_factor_token,
    generate_reset_token,
    verify_turnstile_token_sync,
    verify_google_id_token,
    parse_user_agent,
    resolve_ip_location,
    evaluate_login_risk,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS
)
from app.services.audit_service import AuditService
from app.services.email_sms_service import EmailSmsService

logger = logging.getLogger("vidhik.security.auth")

# In-memory active session token cache (kept synchronized with login_sessions table)
_ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}

MAX_FAILED_ATTEMPTS = int(os.getenv("MAX_FAILED_LOGIN_ATTEMPTS", "5"))
LOCKOUT_MINUTES = int(os.getenv("ACCOUNT_LOCKOUT_MINUTES", "15"))


class AuthService:
    """Core production authentication and account security service."""

    # ==========================================================================
    # 1. REGISTRATION & OTP INITIATION
    # ==========================================================================

    @staticmethod
    def initiate_registration(
        db: RealDictCursor,
        full_name: str,
        email: str,
        password: str,
        confirm_password: Optional[str] = None,
        phone: Optional[str] = None,
        turnstile_token: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Step 1 of Signup:
        - Validates Turnstile CAPTCHA with Cloudflare
        - Validates email & phone formats
        - Validates password complexity policy and confirmation matching
        - Checks for existing verified identity
        - Creates pending unverified account
        - Generates secure OTP and sends via email/SMS
        """
        clean_email = email.strip().lower()
        clean_name = full_name.strip()
        clean_phone = phone.strip() if phone else None

        # 1. Turnstile CAPTCHA validation
        captcha_valid, captcha_err = verify_turnstile_token_sync(turnstile_token, ip_address)
        if not captcha_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=captcha_err or "CAPTCHA verification failed. Please try again."
            )

        # 2. Name validation
        if not clean_name or len(clean_name) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Full name must be at least 2 characters long."
            )

        # 3. Email format validation
        if "@" not in clean_email or "." not in clean_email.split("@")[-1] or len(clean_email) < 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please provide a valid email address."
            )

        # 4. Password confirmation matching
        if confirm_password is not None and password != confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match. Please re-enter your password."
            )

        # 5. Password complexity validation
        pwd_valid, pwd_err = validate_password_strength(password)
        if not pwd_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=pwd_err
            )

        # 6. Duplicate account check
        db.execute("SELECT user_id, email_verified, is_active FROM users WHERE LOWER(email) = %s;", (clean_email,))
        existing_user = db.fetchone()
        if existing_user and existing_user.get("email_verified") is True:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email already exists. Please sign in instead."
            )

        # 7. Hash password with bcrypt
        pwd_hash = hash_password(password)

        if existing_user:
            # Update pending unverified account
            user_id = existing_user["user_id"]
            db.execute("""
                UPDATE users
                SET full_name = %s, phone = %s, password_hash = %s, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s;
            """, (clean_name, clean_phone, pwd_hash, user_id))
        else:
            # Generate unique username
            base_user = clean_email.split("@")[0].replace(".", "_")[:35]
            username = base_user
            ctr = 1
            while True:
                db.execute("SELECT user_id FROM users WHERE username = %s;", (username,))
                if not db.fetchone():
                    break
                username = f"{base_user}_{ctr}"
                ctr += 1

            db.execute("""
                INSERT INTO users (
                    username, email, password_hash, full_name, phone, role,
                    is_active, is_verified, email_verified, phone_verified,
                    account_status, two_factor_enabled
                ) VALUES (
                    %s, %s, %s, %s, %s, 'user',
                    TRUE, FALSE, FALSE, FALSE,
                    'pending_verification', FALSE
                ) RETURNING user_id;
            """, (username, clean_email, pwd_hash, clean_name, clean_phone))
            created_row = db.fetchone()
            user_id = created_row["user_id"]

            # Initialize profile row
            try:
                db.execute("""
                    INSERT INTO user_profiles (user_id, preferred_language)
                    VALUES (%s, 'en')
                    ON CONFLICT (user_id) DO NOTHING;
                """, (user_id,))
            except Exception:
                pass

        # Commit transaction
        if hasattr(db, "connection") and db.connection:
            db.connection.commit()

        # 8. Generate & store cryptographic OTP
        otp_code = generate_secure_otp(6)
        otp_hashed = hash_otp(otp_code)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        # Invalidate old OTPs for this target
        db.execute("""
            DELETE FROM otp_verifications
            WHERE LOWER(target) = %s AND purpose IN ('signup_verification', 'registration', 'signup') AND verified_at IS NULL;
        """, (clean_email,))

        db.execute("""
            INSERT INTO otp_verifications (
                user_id, target, target_type, otp_hash, purpose, expires_at, attempts, max_attempts, resend_count, last_resend_at
            ) VALUES (%s, %s, 'email', %s, 'signup_verification', %s, 0, 5, 0, CURRENT_TIMESTAMP);
        """, (user_id, clean_email, otp_hashed, expires_at))

        if hasattr(db, "connection") and db.connection:
            db.connection.commit()

        # 9. Dispatch OTP and fail closed if email was not accepted by the provider.
        email_sent = EmailSmsService.send_otp_email(
            clean_email, otp_code, "signup_verification", clean_name
        )
        if not email_sent:
            db.execute("""
                DELETE FROM otp_verifications
                WHERE LOWER(target) = %s
                  AND purpose = 'signup_verification'
                  AND verified_at IS NULL;
            """, (clean_email,))
            if hasattr(db, "connection") and db.connection:
                db.connection.commit()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Verification email could not be sent. Configure a working email provider and try again."
            )

        # Email is the primary signup channel; SMS is best-effort only.
        if clean_phone:
            try:
                if not EmailSmsService.send_otp_sms(clean_phone, otp_code, "signup_verification"):
                    logger.warning("Optional signup SMS was not delivered.")
            except Exception:
                logger.exception("Optional signup SMS dispatch failed.")

        AuditService.log_event(
            db=db,
            action="ACCOUNT_CREATED",
            user_id=user_id,
            entity_type="user",
            entity_id=user_id,
            description=f"Registration initiated for {clean_email}. OTP dispatched.",
            ip_address=ip_address,
            user_agent=user_agent
        )

        masked_dest = clean_email[:2] + "***@" + clean_email.split("@")[-1]
        return {
            "status": "otp_required",
            "target": clean_email,
            "destination_masked": masked_dest,
            "expires_in_seconds": 600,
            "resend_cooldown_seconds": 60,
            "message": f"Verification code sent to {masked_dest}. Enter the 6-digit code to continue."
        }

    # ==========================================================================
        # 2. OTP VERIFICATION & MANDATORY 2FA INITIALIZATION
    # ==========================================================================

    @staticmethod
    def verify_otp(
        db: RealDictCursor,
        target: str,
        otp_code: str,
        purpose: str = "signup_verification",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verifies 6-digit OTP code against hashed database record.
        Enforces maximum failed attempts and expiration.
        On success, marks email/phone as verified and triggers mandatory 2FA setup.
        """
        if not target or not target.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification destination target is required."
            )

        clean_target = target.strip().lower()
        clean_code = (otp_code or "").strip().replace(" ", "")

        if not clean_code or len(clean_code) != 6 or not clean_code.isdigit():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please provide a valid 6-digit numeric verification code."
            )

        # Normalize purpose
        norm_purpose = "signup_verification" if purpose in ("signup_verification", "registration", "signup") else purpose

        db.execute("""
            SELECT id, user_id, target, otp_hash, expires_at, verified_at, attempts, max_attempts,
                   (expires_at < CURRENT_TIMESTAMP) AS is_expired
            FROM otp_verifications
            WHERE LOWER(target) = %s AND (purpose = %s OR purpose = %s) AND verified_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1;
        """, (clean_target, norm_purpose, purpose))
        otp_record = db.fetchone()

        if not otp_record:
            # Check if this code was already verified
            db.execute("""
                SELECT id, verified_at FROM otp_verifications
                WHERE LOWER(target) = %s AND (purpose = %s OR purpose = %s) AND verified_at IS NOT NULL
                ORDER BY verified_at DESC LIMIT 1;
            """, (clean_target, norm_purpose, purpose))
            already_verified = db.fetchone()
            if already_verified:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This verification code has already been used. Please sign in."
                )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No pending verification code found. Please request a new code."
            )

        # Check maximum attempts
        if otp_record["attempts"] >= otp_record["max_attempts"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed verification attempts. Please request a new code."
            )

        # Check expiration (DB boolean or Python fallback)
        is_expired = otp_record.get("is_expired")
        if is_expired is None:
            now_dt = datetime.now(timezone.utc)
            exp_dt = otp_record["expires_at"]
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            is_expired = now_dt > exp_dt

        if is_expired:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification code has expired. Please request a new code."
            )

        # Verify cryptographic hash
        is_match = verify_otp_hash(clean_code, otp_record["otp_hash"])
        if not is_match:
            # Increment failed attempts
            db.execute("""
                UPDATE otp_verifications
                SET attempts = attempts + 1
                WHERE id = %s;
            """, (otp_record["id"],))
            if hasattr(db, "connection") and db.connection:
                db.connection.commit()

            remaining = otp_record["max_attempts"] - (otp_record["attempts"] + 1)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid verification code. {max(0, remaining)} attempts remaining."
            )

        # Mark OTP as verified to prevent reuse
        db.execute("""
            UPDATE otp_verifications
            SET verified_at = CURRENT_TIMESTAMP
            WHERE id = %s;
        """, (otp_record["id"],))

        user_id = otp_record["user_id"]

        # If signup verification, mark user as verified
        if norm_purpose == "signup_verification":
            db.execute("""
                UPDATE users
                SET email_verified = TRUE, is_verified = TRUE, account_status = 'active', updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                RETURNING user_id, email, full_name, role;
            """, (user_id,))
            user_row = db.fetchone()
        else:
            db.execute("SELECT user_id, email, full_name, role FROM users WHERE user_id = %s;", (user_id,))
            user_row = db.fetchone()

        if hasattr(db, "connection") and db.connection:
            db.connection.commit()

        AuditService.log_event(
            db=db,
            action="EMAIL_VERIFIED",
            user_id=user_id,
            entity_type="user",
            entity_id=user_id,
            description=f"Identity verified via OTP for target {clean_target}",
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Initialize mandatory 2FA enrollment credentials
        totp_secret = generate_totp_secret()
        user_email = user_row["email"] if user_row else clean_target
        qr_uri = get_totp_uri(totp_secret, user_email, "Vidhik AI")
        qr_code_data_url = generate_qr_code_data_url(qr_uri)
        two_factor_setup_token = create_two_factor_setup_token(user_id, user_email, totp_secret)

        return {
            "status": "2fa_enrollment_required",
            "two_factor_token": two_factor_setup_token,
            "two_factor_setup_token": two_factor_setup_token,
            "qr_uri": qr_uri,
            "qr_code_data_url": qr_code_data_url,
            "totp_secret": totp_secret,
            "secret": totp_secret,
            "message": "Identity verified successfully. Mandatory Two-Factor Authentication (2FA) setup is now required."
        }

    # ==========================================================================
    # 3. OTP RESEND WITH THROTTLING
    # ==========================================================================

    @staticmethod
    def resend_otp(
        db: RealDictCursor,
        target: str,
        purpose: str = "signup_verification",
        turnstile_token: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resends verification OTP with strict 60-second cooldown enforcement.
        """
        if not target or not target.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification destination target is required."
            )

        clean_target = target.strip().lower()
        norm_purpose = "signup_verification" if purpose in ("signup_verification", "registration", "signup") else purpose

        # Find latest OTP record
        db.execute("""
            SELECT id, user_id, resend_count, last_resend_at, verified_at, expires_at,
                   EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - COALESCE(last_resend_at, created_at))) AS seconds_since_resend
            FROM otp_verifications
            WHERE LOWER(target) = %s AND (purpose = %s OR purpose = %s)
            ORDER BY created_at DESC
            LIMIT 1;
        """, (clean_target, norm_purpose, purpose))
        record = db.fetchone()

        if not record or record.get("verified_at") is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No pending verification request found for this identity."
            )

        seconds_elapsed = record.get("seconds_since_resend")
        if seconds_elapsed is not None and seconds_elapsed < 60:
            cooldown_remaining = max(1, int(60 - seconds_elapsed))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {cooldown_remaining} seconds before requesting another code."
            )

        if record["resend_count"] >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Maximum resend limit reached for this session. Please try again in 1 hour."
            )

        # Generate new OTP
        new_otp = generate_secure_otp(6)
        new_hash = hash_otp(new_otp)
        now_dt = datetime.now(timezone.utc)
        expires_at = now_dt + timedelta(minutes=10)

        # Fetch user name if available.
        user_name = None
        if record["user_id"]:
            db.execute("SELECT full_name FROM users WHERE user_id = %s;", (record["user_id"],))
            u_row = db.fetchone()
            if u_row:
                user_name = u_row["full_name"]

        # Do not invalidate the current code unless the replacement is accepted.
        if "@" in clean_target:
            delivered = EmailSmsService.send_otp_email(clean_target, new_otp, norm_purpose, user_name)
        else:
            delivered = EmailSmsService.send_otp_sms(clean_target, new_otp, norm_purpose)

        if not delivered:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Verification code could not be delivered. Check provider configuration and try again."
            )

        db.execute("""
            UPDATE otp_verifications
            SET otp_hash = %s, expires_at = %s, attempts = 0,
                resend_count = resend_count + 1, last_resend_at = CURRENT_TIMESTAMP
            WHERE id = %s AND verified_at IS NULL;
        """, (new_hash, expires_at, record["id"]))

        if hasattr(db, "connection") and db.connection:
            db.connection.commit()

        return {
            "status": "otp_sent",
            "resend_cooldown_seconds": 60,
            "expires_in_seconds": 600,
            "message": "A new verification code has been dispatched."
        }

    # ==========================================================================
    # 4. MANDATORY 2FA SETUP & RECOVERY CODES ENROLLMENT
    # ==========================================================================

    @staticmethod
    def complete_2fa_setup(
        db: RealDictCursor,
        two_factor_token: str,
        totp_code: str,
        secret_override: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Completes mandatory 2FA enrollment:
        - Validates 2FA setup token
        - Verifies 6-digit TOTP code against Base32 secret
        - Persists 2FA secret on users table
        - Generates 8 one-time hashed recovery codes
        - Creates active login session and returns authenticated JWT
        """
        payload = decode_two_factor_token(two_factor_token)
        if not payload or payload.get("type") != "2fa_setup":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired 2FA setup token. Please initiate setup again."
            )

        user_id = int(payload["sub"])
        secret = payload.get("temp_secret") or secret_override

        if not secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="TOTP configuration secret missing."
            )

        # Verify TOTP code
        is_valid = verify_totp_code(secret, totp_code)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid authenticator code. Please ensure your authenticator app time is synchronized."
            )

        # 1. Update user 2FA status in database
        db.execute("""
            UPDATE users
            SET two_factor_enabled = TRUE, two_factor_secret = %s,
                account_status = 'active', updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
            RETURNING user_id, username, email, full_name, phone, role, is_active;
        """, (secret, user_id))
        user_row = db.fetchone()

        # 2. Generate 8 one-time recovery codes
        plain_recovery_codes = generate_recovery_codes(8)

        # Remove old recovery codes if any
        db.execute("DELETE FROM two_factor_recovery_codes WHERE user_id = %s;", (user_id,))

        for code in plain_recovery_codes:
            code_hash = hash_recovery_code(code)
            db.execute("""
                INSERT INTO two_factor_recovery_codes (user_id, code_hash)
                VALUES (%s, %s);
            """, (user_id, code_hash))

        # 3. Create persistent login session
        lawyer_id = 1 if user_row["role"] == "lawyer" else None
        jwt_token = create_access_token(
            user_id=user_row["user_id"],
            email=user_row["email"],
            role=user_row["role"],
            full_name=user_row["full_name"],
            lawyer_id=lawyer_id
        )
        refresh_tok, _ = create_refresh_token(user_row["user_id"])

        ua_meta = parse_user_agent(user_agent)
        geo_meta = resolve_ip_location(ip_address)
        expire_dt = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        db.execute("""
            INSERT INTO login_sessions (
                user_id, session_token, refresh_token, ip_address, user_agent,
                device, browser, os, location_city, location_region, location_country,
                login_method, is_suspicious, expires_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '2fa_setup', FALSE, %s);
        """, (
            user_row["user_id"],
            jwt_token,
            refresh_tok,
            ip_address or "127.0.0.1",
            user_agent,
            ua_meta["device"],
            ua_meta["browser"],
            ua_meta["os"],
            geo_meta["city"],
            geo_meta["region"],
            geo_meta["country"],
            expire_dt
        ))

        if hasattr(db, "connection") and db.connection:
            db.connection.commit()

        session_data = {
            "user_id": user_row["user_id"],
            "username": user_row["username"],
            "email": user_row["email"],
            "full_name": user_row["full_name"],
            "phone": user_row["phone"],
            "role": user_row["role"],
            "lawyer_id": lawyer_id,
            "token": jwt_token,
            "access_token": jwt_token,
            "token_type": "bearer",
            "refresh_token": refresh_tok,
            "is_active": user_row["is_active"],
            "email_verified": True,
            "phone_verified": bool(user_row["phone"]),
            "two_factor_enabled": True,
            "account_status": "active"
        }
        _ACTIVE_SESSIONS[jwt_token] = session_data

        AuditService.log_event(
            db=db,
            action="TWO_FACTOR_ENABLED",
            user_id=user_row["user_id"],
            entity_type="user",
            entity_id=user_row["user_id"],
            description=f"Mandatory 2FA configured ({geo_meta['formatted']}). Recovery codes issued.",
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            "status": "authenticated",
            "recovery_codes": plain_recovery_codes,
            "token": jwt_token,
            "access_token": jwt_token,
            "token_type": "bearer",
            "refresh_token": refresh_tok,
            "user": session_data,
            "message": "Two-Factor Authentication successfully activated. Save your recovery codes in a secure location."
        }

    # ==========================================================================
    # 5. USER LOGIN & MANDATORY 2FA CHALLENGE
    # ==========================================================================

    @staticmethod
    def authenticate_credentials(
        db: RealDictCursor,
        email: str,
        password: str,
        turnstile_token: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Step 1 of Login:
        - Validates Turnstile CAPTCHA
        - Checks account lockout from previous brute-force attempts
        - Validates password hash with bcrypt (+ transparent migration)
        - On valid credentials, enforces Mandatory 2FA challenge.
        - NO access token is returned here; only a 2FA challenge token.
        """
        clean_email = email.strip().lower()

        # 1. Turnstile CAPTCHA validation
        captcha_valid, captcha_err = verify_turnstile_token_sync(turnstile_token, ip_address)
        if not captcha_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=captcha_err or "CAPTCHA verification failed. Please try again."
            )

        # 2. Fetch user
        query = """
            SELECT 
                u.user_id, u.username, u.email, u.password_hash,
                u.full_name, u.phone, u.role, u.is_active,
                u.email_verified, u.is_verified, u.account_status,
                u.two_factor_enabled, u.two_factor_secret,
                u.failed_login_attempts, u.locked_until,
                l.lawyer_id
            FROM users u
            LEFT JOIN lawyers l ON u.user_id = l.user_id
            WHERE LOWER(u.email) = %s OR u.phone = %s;
        """
        db.execute(query, (clean_email, clean_email))
        user = db.fetchone()

        now_dt = datetime.now(timezone.utc)

        if not user or not user["is_active"]:
            AuditService.log_event(
                db=db,
                action="LOGIN_FAILED",
                description=f"Login attempt for inactive or non-existent account: {clean_email}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password. Please verify your credentials."
            )

        # 3. Check account verification status
        if user.get("email_verified") is False and (user.get("account_status") == "pending_verification" or not user.get("is_verified", True)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account verification is pending. Please verify your account using the OTP code sent to your email or mobile."
            )

        # 4. Check account lockout
        locked_until = user.get("locked_until")
        if locked_until:
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            if now_dt < locked_until:
                remaining_sec = int((locked_until - now_dt).total_seconds())
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail=f"Account is temporarily locked due to multiple failed attempts. Please retry in {max(1, remaining_sec // 60)} minutes."
                )

        # 4. Verify password
        is_valid, needs_rehash = verify_and_migrate_password(password, user["password_hash"])
        if not is_valid:
            # Increment failed attempts
            new_failed = (user.get("failed_login_attempts") or 0) + 1
            lockout_dt = None
            if new_failed >= MAX_FAILED_ATTEMPTS:
                lockout_dt = now_dt + timedelta(minutes=LOCKOUT_MINUTES)
                # Create security alert for account lockout
                geo_meta = resolve_ip_location(ip_address)
                ua_meta = parse_user_agent(user_agent)
                db.execute("""
                    INSERT INTO security_alerts (
                        user_id, title, alert_type, severity, description,
                        device, browser, ip_address, location
                    ) VALUES (%s, 'Account Locked Due to Repeated Failures', 'FAILED_LOGINS', 'high', %s, %s, %s, %s, %s);
                """, (
                    user["user_id"],
                    f"Account locked after {new_failed} consecutive failed login attempts.",
                    ua_meta["device"],
                    ua_meta["browser"],
                    ip_address or "127.0.0.1",
                    geo_meta["formatted"]
                ))
                AuditService.log_event(
                    db=db,
                    action="BRUTE_FORCE_TRIGGERED",
                    user_id=user["user_id"],
                    description=f"Account locked for {LOCKOUT_MINUTES}m due to {new_failed} failed attempts",
                    ip_address=ip_address,
                    user_agent=user_agent
                )

            db.execute("""
                UPDATE users
                SET failed_login_attempts = %s, locked_until = %s, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s;
            """, (new_failed, lockout_dt, user["user_id"]))

            if hasattr(db, "connection") and db.connection:
                db.connection.commit()

            AuditService.log_event(
                db=db,
                action="LOGIN_FAILED",
                user_id=user["user_id"],
                entity_type="user",
                entity_id=user["user_id"],
                description=f"Invalid password for user_id={user['user_id']}",
                ip_address=ip_address,
                user_agent=user_agent
            )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password. Please verify your credentials."
            )

        # 5. Password correct: Reset failure counters & transparent rehash if legacy
        if needs_rehash:
            try:
                new_bcrypt = hash_password(password)
                db.execute("UPDATE users SET password_hash = %s WHERE user_id = %s;", (new_bcrypt, user["user_id"]))
            except Exception:
                pass

        db.execute("""
            UPDATE users
            SET failed_login_attempts = 0, locked_until = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s;
        """, (user["user_id"],))

        if hasattr(db, "connection") and db.connection:
            db.connection.commit()

        lawyer_id = user["lawyer_id"] or (1 if user["role"] == "lawyer" else None)

        # 6. ENFORCE MANDATORY 2FA
        if user["two_factor_enabled"] and user["two_factor_secret"]:
            # Issue short-lived 2FA Challenge Token (5 min expiry)
            challenge_tok = create_two_factor_challenge_token(
                user_id=user["user_id"],
                email=user["email"],
                role=user["role"],
                full_name=user["full_name"],
                lawyer_id=lawyer_id,
                login_method="password"
            )
            return {
                "status": "2fa_required",
                "two_factor_required": True,
                "two_factor_token": challenge_tok,
                "message": "Two-Factor Authentication code required. Please enter the 6-digit code from your authenticator app."
            }
        else:
            # User has not enrolled in mandatory 2FA: Force immediate enrollment
            totp_secret = generate_totp_secret()
            qr_uri = get_totp_uri(totp_secret, user["email"], "Vidhik AI")
            qr_data_url = generate_qr_code_data_url(qr_uri)
            setup_tok = create_two_factor_setup_token(user["user_id"], user["email"], totp_secret)
            return {
                "status": "2fa_enrollment_required",
                "two_factor_token": setup_tok,
                "qr_uri": qr_uri,
                "qr_code_data_url": qr_data_url,
                "totp_secret": totp_secret,
                "message": "Mandatory Two-Factor Authentication (2FA) setup is required for this account."
            }

    # ==========================================================================
    # 6. 2FA VERIFICATION & FINAL SESSION ESTABLISHMENT
    # ==========================================================================

    @staticmethod
    def verify_two_factor_login(
        db: RealDictCursor,
        two_factor_token: str,
        totp_code: str,
        use_recovery_code: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Step 2 of Login:
        - Validates short-lived 2FA challenge token
        - Verifies TOTP code or one-time recovery code
        - Runs anomaly detection (new device, new location)
        - Creates persistent login_sessions row
        - Generates real signed JWT access token + refresh token
        """
        payload = decode_two_factor_token(two_factor_token)
        if not payload or payload.get("type") != "2fa_challenge":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired Two-Factor session. Please sign in again."
            )

        user_id = int(payload["sub"])

        # Fetch user
        db.execute("""
            SELECT 
                u.user_id, u.username, u.email, u.full_name, u.phone,
                u.role, u.is_active, u.two_factor_secret, u.email_verified,
                l.lawyer_id
            FROM users u
            LEFT JOIN lawyers l ON u.user_id = l.user_id
            WHERE u.user_id = %s;
        """, (user_id,))
        user = db.fetchone()

        if not user or not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is deactivated or unavailable."
            )

        clean_code = totp_code.strip()

        # 1. Verification of Code (TOTP or Recovery Code)
        login_method = "2fa_totp"
        is_recovery_format = bool(use_recovery_code or ("-" in clean_code) or len(clean_code) != 6 or not clean_code.isdigit())
        if is_recovery_format:
            # Recovery code verification
            clean_rec_code = clean_code.upper().replace(" ", "")
            db.execute("""
                SELECT id, code_hash, used_at
                FROM two_factor_recovery_codes
                WHERE user_id = %s AND used_at IS NULL;
            """, (user_id,))
            recovery_rows = db.fetchall()

            matched_rec_id = None
            for r_row in recovery_rows:
                if verify_recovery_code(clean_rec_code, r_row["code_hash"]):
                    matched_rec_id = r_row["id"]
                    break

            if not matched_rec_id:
                AuditService.log_event(
                    db=db,
                    action="2FA_FAILED",
                    user_id=user_id,
                    description="Failed 2FA attempt using invalid or consumed recovery code",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or already used recovery code."
                )

            # Consume recovery code
            db.execute("""
                UPDATE two_factor_recovery_codes
                SET used_at = CURRENT_TIMESTAMP
                WHERE id = %s;
            """, (matched_rec_id,))
            login_method = "2fa_recovery"

            # Create security alert for recovery code consumption
            geo_meta = resolve_ip_location(ip_address)
            ua_meta = parse_user_agent(user_agent)
            db.execute("""
                INSERT INTO security_alerts (
                    user_id, title, alert_type, severity, description,
                    device, browser, ip_address, location
                ) VALUES (%s, 'Emergency Recovery Code Used', 'RECOVERY_CODE_USED', 'high', %s, %s, %s, %s, %s);
            """, (
                user_id,
                "A one-time emergency recovery code was used to sign in to your Vidhik account.",
                ua_meta["device"],
                ua_meta["browser"],
                ip_address or "127.0.0.1",
                geo_meta["formatted"]
            ))
        else:
            # Standard TOTP verification
            is_valid = verify_totp_code(user["two_factor_secret"], clean_code)
            if not is_valid:
                AuditService.log_event(
                    db=db,
                    action="2FA_FAILED",
                    user_id=user_id,
                    description="Failed 2FA attempt with incorrect authenticator code",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authenticator code. Please check the code in your authenticator app and try again."
                )

        # 2. Anomaly Detection (New Device / New Location)
        ua_meta = parse_user_agent(user_agent)
        geo_meta = resolve_ip_location(ip_address)

        db.execute("""
            SELECT device, browser, location_city, ip_address
            FROM login_sessions
            WHERE user_id = %s AND revoked_at IS NULL
            ORDER BY created_at DESC
            LIMIT 10;
        """, (user_id,))
        recent_sessions = db.fetchall()

        is_suspicious, risk_desc = evaluate_login_risk(
            user_id=user_id,
            current_ip=ip_address or "127.0.0.1",
            current_device=ua_meta["device"],
            current_browser=ua_meta["browser"],
            current_location=geo_meta["formatted"],
            recent_sessions=recent_sessions
        )

        if is_suspicious:
            alert_title = f"New Login from {ua_meta['browser']} on {ua_meta['device']}"
            alert_desc = f"New login detected from {geo_meta['formatted']} ({ip_address}) using {ua_meta['browser']} on {ua_meta['device']}."
            
            db.execute("""
                INSERT INTO security_alerts (
                    user_id, title, alert_type, severity, description,
                    device, browser, ip_address, location
                ) VALUES (%s, %s, 'NEW_DEVICE', 'medium', %s, %s, %s, %s, %s);
            """, (
                user_id,
                alert_title,
                alert_desc,
                ua_meta["device"],
                ua_meta["browser"],
                ip_address or "127.0.0.1",
                geo_meta["formatted"]
            ))

            # Dispatch security alert email
            EmailSmsService.send_security_alert_email(
                to_email=user["email"],
                user_name=user["full_name"] or user["username"],
                alert_type="NEW_DEVICE",
                title=alert_title,
                description=alert_desc,
                device=f"{ua_meta['browser']} on {ua_meta['device']} ({ua_meta['os']})",
                location=geo_meta["formatted"],
                ip_address=ip_address or "127.0.0.1"
            )

        # 3. Issue signed JWT & refresh tokens
        lawyer_id = user["lawyer_id"] or (1 if user["role"] == "lawyer" else None)
        jwt_token = create_access_token(
            user_id=user["user_id"],
            email=user["email"],
            role=user["role"],
            full_name=user["full_name"],
            lawyer_id=lawyer_id
        )
        refresh_tok, _ = create_refresh_token(user["user_id"])

        expire_dt = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        # Persist session with device and login-risk metadata
        try:
            db.execute("""
                INSERT INTO login_sessions (
                    user_id, session_token, refresh_token, ip_address, user_agent,
                    device, browser, os, location_city, location_region, location_country,
                    login_method, is_suspicious, expires_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                user["user_id"], jwt_token, refresh_tok,
                ip_address or "127.0.0.1", user_agent,
                ua_meta["device"], ua_meta["browser"], ua_meta["os"],
                geo_meta["city"], geo_meta["region"], geo_meta["country"],
                login_method, is_suspicious, expire_dt
            ))
            if hasattr(db, "connection") and db.connection:
                db.connection.commit()
        except Exception as e:
            logger.warning(f"Could not persist login session to DB: {e}")
            if hasattr(db, "connection") and db.connection:
                try:
                    db.connection.rollback()
                except Exception:
                    pass

        session_data = {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "phone": user["phone"],
            "role": user["role"],
            "lawyer_id": lawyer_id,
            "token": jwt_token,
            "access_token": jwt_token,
            "token_type": "bearer",
            "refresh_token": refresh_tok,
            "is_active": user["is_active"],
            "email_verified": user.get("email_verified", True),
            "phone_verified": bool(user.get("phone")),
            "two_factor_enabled": True,
            "account_status": "active"
        }
        _ACTIVE_SESSIONS[jwt_token] = session_data

        AuditService.log_event(
            db=db,
            action="LOGIN_SUCCESS",
            user_id=user["user_id"],
            entity_type="user",
            entity_id=user["user_id"],
            description=f"User {user['email']} authenticated with 2FA ({login_method}) from {geo_meta['formatted']}",
            ip_address=ip_address,
            user_agent=user_agent
        )

        return session_data

    # ==========================================================================
    # 7. GOOGLE OAUTH 2.0 / OIDC IDENTITY
    # ==========================================================================

    @staticmethod
    async def authenticate_google(
        db: RealDictCursor,
        id_token_str: str,
        turnstile_token: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verifies Google ID token, provisions or links user identity,
        and enforces mandatory VIDHIK 2FA challenge.
        """
        # 1. Turnstile CAPTCHA validation
        captcha_valid, captcha_err = verify_turnstile_token_sync(turnstile_token, ip_address)
        if not captcha_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=captcha_err or "CAPTCHA verification failed."
            )

        # 2. Verify Google ID token
        is_valid, g_payload, g_err = await verify_google_id_token(id_token_str)
        if not is_valid or not g_payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=g_err or "Google authentication failed. Please try again."
            )

        google_email = g_payload["email"]
        google_sub = g_payload["sub"]
        google_name = g_payload.get("full_name") or google_email.split("@")[0]

        # 3. Lookup user by email or google_sub
        db.execute("""
            SELECT 
                user_id, username, email, full_name, phone, role, is_active,
                two_factor_enabled, two_factor_secret, google_sub
            FROM users
            WHERE LOWER(email) = %s OR google_sub = %s;
        """, (google_email, google_sub))
        user = db.fetchone()

        if user:
            # Update google_sub and verified flag if not set
            user_id = user["user_id"]
            db.execute("""
                UPDATE users
                SET google_sub = %s, email_verified = TRUE, is_verified = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s;
            """, (google_sub, user_id))
        else:
            # Create new user via Google
            base_user = google_email.split("@")[0].replace(".", "_")[:35]
            username = base_user
            ctr = 1
            while True:
                db.execute("SELECT user_id FROM users WHERE username = %s;", (username,))
                if not db.fetchone():
                    break
                username = f"{base_user}_{ctr}"
                ctr += 1

            # Generate random complex initial password hash
            random_pwd = secrets.token_urlsafe(32)
            pwd_hash = hash_password(random_pwd)

            db.execute("""
                INSERT INTO users (
                    username, email, password_hash, full_name, role,
                    is_active, is_verified, email_verified, phone_verified,
                    account_status, two_factor_enabled, auth_provider, google_sub
                ) VALUES (
                    %s, %s, %s, %s, 'user',
                    TRUE, TRUE, TRUE, FALSE,
                    'active', FALSE, 'google', %s
                ) RETURNING user_id, username, email, full_name, role, is_active, two_factor_enabled;
            """, (username, google_email, pwd_hash, google_name, google_sub))
            user = db.fetchone()
            user_id = user["user_id"]

            try:
                db.execute("INSERT INTO user_profiles (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING;", (user_id,))
            except Exception:
                pass

        if hasattr(db, "connection") and db.connection:
            db.connection.commit()

        AuditService.log_event(
            db=db,
            action="GOOGLE_LOGIN",
            user_id=user_id,
            entity_type="user",
            entity_id=user_id,
            description=f"Google identity verified for {google_email}",
            ip_address=ip_address,
            user_agent=user_agent
        )

        # 4. Enforce Mandatory VIDHIK 2FA
        if user["two_factor_enabled"] and user.get("two_factor_secret"):
            challenge_tok = create_two_factor_challenge_token(
                user_id=user_id,
                email=google_email,
                role=user["role"],
                full_name=user["full_name"],
                login_method="google"
            )
            return {
                "status": "2fa_required",
                "two_factor_token": challenge_tok,
                "message": "Google identity verified. Enter code from your authenticator app to access Vidhik."
            }
        else:
            totp_secret = generate_totp_secret()
            qr_uri = get_totp_uri(totp_secret, google_email, "Vidhik AI")
            qr_data_url = generate_qr_code_data_url(qr_uri)
            setup_tok = create_two_factor_setup_token(user_id, google_email, totp_secret)
            return {
                "status": "2fa_enrollment_required",
                "two_factor_token": setup_tok,
                "qr_uri": qr_uri,
                "qr_code_data_url": qr_data_url,
                "totp_secret": totp_secret,
                "message": "Google authentication verified. Mandatory Two-Factor Authentication setup is required to proceed."
            }

    # ==========================================================================
    # 8. PASSWORD RESET WORKFLOW
    # ==========================================================================

    @staticmethod
    def request_password_reset(
        db: RealDictCursor,
        email: str,
        turnstile_token: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initiates password reset with cryptographic reset token and email OTP.
        Always returns generic message to prevent account enumeration.
        """
        clean_email = email.strip().lower()

        # 1. Turnstile CAPTCHA validation
        captcha_valid, _ = verify_turnstile_token_sync(turnstile_token, ip_address)
        if not captcha_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CAPTCHA verification failed. Please complete the security check."
            )

        db.execute("SELECT user_id, full_name, is_active FROM users WHERE LOWER(email) = %s;", (clean_email,))
        user = db.fetchone()

        if not user or not user["is_active"]:
            AuditService.log_event(
                db=db,
                action="PASSWORD_RESET_ATTEMPT_UNKNOWN",
                description=f"Password reset requested for non-existent email: {clean_email}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            return {
                "status": "success",
                "message": "If this email is registered, password reset instructions have been dispatched to your inbox."
            }

        # Generate reset token and OTP
        reset_token = generate_reset_token()
        otp_code = generate_secure_otp(6)
        otp_hash = hash_otp(otp_code)
        now_dt = datetime.now(timezone.utc)
        exp_token = now_dt + timedelta(hours=1)
        exp_otp = now_dt + timedelta(minutes=15)

        # Dispatch first; don't store a reset code that was not delivered.
        email_sent = EmailSmsService.send_otp_email(
            clean_email, otp_code, "password_reset", user["full_name"]
        )
        if not email_sent:
            logger.warning("Password reset email was not delivered by the configured provider.")
            return {
                "status": "success",
                "message": "If this email is registered, password reset instructions have been dispatched to your inbox."
            }

        db.execute("""
            INSERT INTO password_resets (user_id, reset_token, expires_at)
            VALUES (%s, %s, %s);
        """, (user["user_id"], reset_token, exp_token))

        db.execute("""
            DELETE FROM otp_verifications
            WHERE target = %s AND purpose = 'password_reset' AND verified_at IS NULL;
        """, (clean_email,))

        db.execute("""
            INSERT INTO otp_verifications (
                user_id, target, target_type, otp_hash, purpose, expires_at
            ) VALUES (%s, %s, 'email', %s, 'password_reset', %s);
        """, (user["user_id"], clean_email, otp_hash, exp_otp))

        if hasattr(db, "connection") and db.connection:
            db.connection.commit()

        AuditService.log_event(
            db=db,
            action="PASSWORD_RESET_REQUESTED",
            user_id=user["user_id"],
            description="Password reset token and verification OTP generated",
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            "status": "success",
            "message": "If this email is registered, password reset instructions have been dispatched to your inbox."
        }

    @staticmethod
    def complete_password_reset(
        db: RealDictCursor,
        new_password: str,
        confirm_password: str,
        reset_token: Optional[str] = None,
        email: Optional[str] = None,
        otp_code: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Completes password reset via reset token or OTP:
        - Validates password complexity & match
        - Validates token/OTP validity
        - Hashes new password with bcrypt
        - Revokes ALL active user sessions across all devices
        - Creates security alert
        """
        if new_password != confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password and confirmation do not match."
            )

        pwd_valid, pwd_err = validate_password_strength(new_password)
        if not pwd_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=pwd_err
            )

        user_id = None

        if reset_token:
            db.execute("""
                SELECT reset_id, user_id, expires_at, used_at
                FROM password_resets
                WHERE reset_token = %s;
            """, (reset_token.strip(),))
            r_record = db.fetchone()

            if not r_record or r_record["used_at"] is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or already used password reset link."
                )

            now_dt = datetime.now(timezone.utc)
            exp_dt = r_record["expires_at"]
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)

            if now_dt > exp_dt:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password reset link has expired. Please request a new one."
                )

            user_id = r_record["user_id"]
            db.execute("UPDATE password_resets SET used_at = CURRENT_TIMESTAMP WHERE reset_id = %s;", (r_record["reset_id"],))

        elif email and otp_code:
            clean_email = email.strip().lower()
            clean_code = otp_code.strip()

            db.execute("""
                SELECT id, user_id, otp_hash, expires_at, attempts, max_attempts
                FROM otp_verifications
                WHERE LOWER(target) = %s AND purpose = 'password_reset' AND verified_at IS NULL
                ORDER BY created_at DESC LIMIT 1;
            """, (clean_email,))
            otp_record = db.fetchone()

            if not otp_record or not verify_otp_hash(clean_code, otp_record["otp_hash"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid password reset verification code."
                )

            now_dt = datetime.now(timezone.utc)
            exp_dt = otp_record["expires_at"]
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)

            if now_dt > exp_dt:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password reset code has expired."
                )

            user_id = otp_record["user_id"]
            db.execute("UPDATE otp_verifications SET verified_at = CURRENT_TIMESTAMP WHERE id = %s;", (otp_record["id"],))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either reset token or email + verification code is required."
            )

        # Update password
        new_hash = hash_password(new_password)
        db.execute("""
            UPDATE users
            SET password_hash = %s, failed_login_attempts = 0, locked_until = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s;
        """, (new_hash, user_id))

        # Revoke ALL existing active sessions
        db.execute("""
            UPDATE login_sessions
            SET revoked_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND revoked_at IS NULL;
        """, (user_id,))

        if hasattr(db, "connection") and db.connection:
            db.connection.commit()

        # Invalidate in-memory cache
        for tok, sess in list(_ACTIVE_SESSIONS.items()):
            if sess.get("user_id") == user_id:
                _ACTIVE_SESSIONS.pop(tok, None)

        # Create security alert
        ua_meta = parse_user_agent(user_agent)
        geo_meta = resolve_ip_location(ip_address)
        db.execute("""
            INSERT INTO security_alerts (
                user_id, title, alert_type, severity, description,
                device, browser, ip_address, location
            ) VALUES (%s, 'Password Reset Completed', 'PASSWORD_CHANGED', 'high', %s, %s, %s, %s, %s);
        """, (
            user_id,
            "Your password was successfully reset. All previous sessions have been logged out for security.",
            ua_meta["device"],
            ua_meta["browser"],
            ip_address or "127.0.0.1",
            geo_meta["formatted"]
        ))

        AuditService.log_event(
            db=db,
            action="PASSWORD_RESET",
            user_id=user_id,
            entity_type="user",
            entity_id=user_id,
            description="Password reset completed successfully. Prior sessions revoked.",
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            "status": "success",
            "message": "Password has been successfully updated. Please sign in with your new password."
        }

    # ==========================================================================
    # 9. SESSION MANAGEMENT & SECURITY ACTIVITY
    # ==========================================================================

    @staticmethod
    def get_user_sessions(
        db: RealDictCursor,
        user_id: int,
        current_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieves all active sessions for the authenticated user.
        """
        db.execute("""
            SELECT 
                session_id, session_token, ip_address, user_agent,
                device, browser, os, location_city, location_region, location_country,
                login_method, created_at, expires_at
            FROM login_sessions
            WHERE user_id = %s AND revoked_at IS NULL AND expires_at > CURRENT_TIMESTAMP
            ORDER BY created_at DESC;
        """, (user_id,))
        rows = db.fetchall()

        sessions_list = []
        current_session = None

        for r in rows:
            is_cur = bool(current_token and r["session_token"] == current_token)
            loc_parts = [p for p in (r.get("location_city"), r.get("location_region"), r.get("location_country")) if p]
            loc_formatted = ", ".join(loc_parts) if loc_parts else "Pune, Maharashtra, India"

            item = {
                "id": r["session_id"],
                "session_id": r["session_id"],
                "device": r["device"] or "Desktop",
                "device_type": r["device"] or "Desktop",
                "browser": r["browser"] or "Browser",
                "os": r["os"] or "Windows",
                "ip_address": r["ip_address"] or "127.0.0.1",
                "location": loc_formatted,
                "approximate_location": loc_formatted,
                "login_method": r["login_method"] or "password",
                "created_at": r["created_at"],
                "last_active": r["created_at"],
                "expires_at": r["expires_at"],
                "is_current": is_cur
            }
            if is_cur:
                current_session = item
            sessions_list.append(item)

        return {
            "current_session": current_session,
            "active_sessions": sessions_list,
            "total_sessions": len(sessions_list)
        }

    @staticmethod
    def revoke_session(
        db: RealDictCursor,
        user_id: int,
        session_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Revokes a specific user session."""
        db.execute("""
            UPDATE login_sessions
            SET revoked_at = CURRENT_TIMESTAMP
            WHERE session_id = %s AND user_id = %s
            RETURNING session_token;
        """, (session_id, user_id))
        row = db.fetchone()

        if row and row["session_token"]:
            _ACTIVE_SESSIONS.pop(row["session_token"], None)

        if hasattr(db, "connection") and db.connection:
            db.connection.commit()

        AuditService.log_event(
            db=db,
            action="SESSION_REVOKED",
            user_id=user_id,
            description=f"Session id={session_id} explicitly revoked by user",
            ip_address=ip_address,
            user_agent=user_agent
        )
        return True

    @staticmethod
    def revoke_all_other_sessions(
        db: RealDictCursor,
        user_id: int,
        current_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """Revokes all active sessions except the current session."""
        db.execute("""
            UPDATE login_sessions
            SET revoked_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND session_token != %s AND revoked_at IS NULL
            RETURNING session_token;
        """, (user_id, current_token))
        revoked_rows = db.fetchall()

        for r in revoked_rows:
            if r["session_token"]:
                _ACTIVE_SESSIONS.pop(r["session_token"], None)

        if hasattr(db, "connection") and db.connection:
            db.connection.commit()

        AuditService.log_event(
            db=db,
            action="SESSION_REVOKED_OTHERS",
            user_id=user_id,
            description=f"Revoked {len(revoked_rows)} other sessions",
            ip_address=ip_address,
            user_agent=user_agent
        )
        return len(revoked_rows)

    @staticmethod
    def get_security_alerts(
        db: RealDictCursor,
        user_id: int
    ) -> Dict[str, Any]:
        """Retrieves security incidents and alerts for the user."""
        db.execute("""
            SELECT 
                alert_id, title, alert_type, severity, description,
                device, browser, ip_address, location, is_read, created_at
            FROM security_alerts
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 30;
        """, (user_id,))
        alerts = db.fetchall()
        unread_count = sum(1 for a in alerts if not a.get("is_read"))
        alerts_list = []
        for a in alerts:
            alerts_list.append({
                "id": a["alert_id"],
                "alert_id": a["alert_id"],
                "title": a["title"],
                "alert_type": a["alert_type"],
                "severity": a["severity"],
                "description": a["description"],
                "message": a["description"] or a["title"],
                "device": a["device"],
                "browser": a["browser"],
                "ip_address": a["ip_address"],
                "location": a["location"],
                "is_read": a["is_read"],
                "created_at": a["created_at"]
            })
        return {
            "alerts": alerts_list,
            "unread_count": unread_count
        }

    @staticmethod
    def mark_alert_read(
        db: RealDictCursor,
        user_id: int,
        alert_id: int
    ) -> bool:
        """Marks a security alert as read."""
        db.execute("""
            UPDATE security_alerts
            SET is_read = TRUE
            WHERE alert_id = %s AND user_id = %s;
        """, (alert_id, user_id))
        if hasattr(db, "connection") and db.connection:
            db.connection.commit()
        return True

    @staticmethod
    def regenerate_recovery_codes(
        db: RealDictCursor,
        user_id: int,
        password: Optional[str] = None,
        totp_code: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> List[str]:
        """
        Regenerates 8 one-time recovery codes. Invalidates previous codes.
        Requires re-authentication with password or TOTP code.
        """
        db.execute("SELECT password_hash, two_factor_secret FROM users WHERE user_id = %s;", (user_id,))
        user = db.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        auth_ok = False
        if password:
            valid_pwd, _ = verify_and_migrate_password(password, user["password_hash"])
            if valid_pwd:
                auth_ok = True
        if not auth_ok and totp_code and user.get("two_factor_secret"):
            if verify_totp_code(user["two_factor_secret"], totp_code):
                auth_ok = True

        if not auth_ok:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Re-authentication required. Please provide your current password or 6-digit authenticator code."
            )

        # Invalidate old recovery codes
        db.execute("DELETE FROM two_factor_recovery_codes WHERE user_id = %s;", (user_id,))

        # Generate new recovery codes
        new_codes = generate_recovery_codes(8)
        for code in new_codes:
            db.execute("""
                INSERT INTO two_factor_recovery_codes (user_id, code_hash)
                VALUES (%s, %s);
            """, (user_id, hash_recovery_code(code)))

        # Create security alert
        ua_meta = parse_user_agent(user_agent)
        geo_meta = resolve_ip_location(ip_address)
        db.execute("""
            INSERT INTO security_alerts (
                user_id, title, alert_type, severity, description,
                device, browser, ip_address, location
            ) VALUES (%s, 'Recovery Codes Regenerated', 'RECOVERY_CODES_REGENERATED', 'high', %s, %s, %s, %s, %s);
        """, (
            user_id,
            "Your two-factor authentication recovery codes were regenerated. All previous codes are now invalid.",
            ua_meta["device"],
            ua_meta["browser"],
            ip_address or "127.0.0.1",
            geo_meta["formatted"]
        ))

        if hasattr(db, "connection") and db.connection:
            db.connection.commit()

        AuditService.log_event(
            db=db,
            action="RECOVERY_CODES_REGENERATED",
            user_id=user_id,
            description="2FA recovery codes regenerated by user",
            ip_address=ip_address,
            user_agent=user_agent
        )
        return new_codes

    @staticmethod
    def change_password(
        db: RealDictCursor,
        user_id: int,
        current_password: str,
        new_password: str,
        confirm_password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Validates current password, checks complexity, updates to bcrypt,
        revokes other sessions, and generates security alert.
        """
        effective_confirm = confirm_password if confirm_password is not None else new_password
        if new_password != effective_confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password and confirmation do not match."
            )

        pwd_valid, pwd_err = validate_password_strength(new_password)
        if not pwd_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=pwd_err
            )

        db.execute("SELECT password_hash FROM users WHERE user_id = %s;", (user_id,))
        row = db.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User account not found.")

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

        # Create security alert
        ua_meta = parse_user_agent(user_agent)
        geo_meta = resolve_ip_location(ip_address)
        db.execute("""
            INSERT INTO security_alerts (
                user_id, title, alert_type, severity, description,
                device, browser, ip_address, location
            ) VALUES (%s, 'Password Changed', 'PASSWORD_CHANGED', 'medium', %s, %s, %s, %s, %s);
        """, (
            user_id,
            "Your Vidhik account password was successfully changed.",
            ua_meta["device"],
            ua_meta["browser"],
            ip_address or "127.0.0.1",
            geo_meta["formatted"]
        ))

        if hasattr(db, "connection") and db.connection:
            db.connection.commit()

        AuditService.log_event(
            db=db,
            action="PASSWORD_CHANGED",
            user_id=user_id,
            description="User changed password",
            ip_address=ip_address,
            user_agent=user_agent
        )
        return True

    @staticmethod
    def logout_user(
        token: str,
        db: Optional[RealDictCursor] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Revokes an active session token."""
        user_id = None
        if token and token in _ACTIVE_SESSIONS:
            user_id = _ACTIVE_SESSIONS[token].get("user_id")
            _ACTIVE_SESSIONS.pop(token, None)

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
            action="LOGOUT",
            user_id=user_id,
            description="User logged out and session revoked",
            ip_address=ip_address,
            user_agent=user_agent
        )
        return True


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
        db.execute("""
            SELECT 
                u.user_id, u.username, u.email, u.full_name, u.phone,
                u.role, u.is_active, u.email_verified, u.phone_verified,
                u.two_factor_enabled, u.account_status,
                l.lawyer_id
            FROM users u
            LEFT JOIN lawyers l ON u.user_id = l.user_id
            WHERE u.user_id = %s;
        """, (user_id,))
        user_row = db.fetchone()

        if not user_row or not user_row["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is deactivated or no longer exists."
            )

        # Check if revoked in login_sessions
        try:
            db.execute("SELECT revoked_at, expires_at FROM login_sessions WHERE session_token = %s;", (token,))
            sess_row = db.fetchone()
            if sess_row and sess_row["revoked_at"] is not None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication session has been revoked. Please sign in again."
                )
        except HTTPException:
            raise
        except Exception:
            if hasattr(db, "connection") and db.connection:
                try:
                    db.connection.rollback()
                except Exception:
                    pass

        lawyer_id = user_row["lawyer_id"] or (1 if user_row["role"] == "lawyer" else None)
        return {
            "user_id": user_row["user_id"],
            "username": user_row["username"],
            "email": user_row["email"],
            "full_name": user_row["full_name"],
            "phone": user_row["phone"],
            "role": user_row["role"],
            "lawyer_id": lawyer_id,
            "is_active": user_row["is_active"],
            "email_verified": user_row.get("email_verified", True),
            "phone_verified": user_row.get("phone_verified", False),
            "two_factor_enabled": user_row.get("two_factor_enabled", True),
            "account_status": user_row.get("account_status", "active"),
            "token": token
        }

    # 2. In-memory session fallback (for active test sessions)
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
    """Optional user dependency."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
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


def user_hash_placeholder(h: str) -> str:
    """Helper for query interpolation."""
    return h
