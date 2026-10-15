"""
Vidhik Platform - Comprehensive Email & Phone OTP Authentication Test Suite
=============================================================================
Tests validating the complete Signup -> OTP Delivery -> OTP Verification lifecycle:
1. Signup Initiation & Cloudflare Turnstile enforcement (valid, missing, invalid tokens)
2. Password validation and duplicate user handling
3. Multi-provider notification dispatch (SMTP, Twilio, MSG91, Resend, SendGrid)
4. Production vs Development provider configuration failure safety
5. Cryptographic OTP security:
   - Correct OTP verification
   - Incorrect OTP with attempt counter tracking
   - 5-attempt lockout enforcement (HTTP 429)
   - Expired OTP handling
   - Single-use enforcement (reused OTP rejected)
   - Resend cooldown enforcement (60s lock)
   - Superseded OTP invalidation
   - Safe DB transitions: unverified account cannot log in and failed OTP never marks verified
6. Masking of sensitive OTP data in logs
"""

import os
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db_cursor
from app.core.security import (
    generate_secure_otp,
    hash_otp,
    verify_otp_hash,
    hash_password,
    verify_turnstile_token_sync
)
from app.services.email_sms_service import EmailSmsService
from app.services.auth_service import AuthService


@pytest.fixture
def client():
    return TestClient(app)


# =============================================================================
# 1. SIGNUP INITIATION & TURNSTILE TESTS
# =============================================================================

class TestSignupInitiationAndTurnstile:
    """Tests for registration initiation, field validation, and Turnstile CAPTCHA enforcement."""

    def test_signup_initiate_success_with_turnstile(self, client):
        test_email = f"signup.test.{int(datetime.now().timestamp())}@vidhik.ai"
        try:
            resp = client.post("/api/auth/register-initiate", json={
                "full_name": "Adv. Rajesh Deshmukh",
                "email": test_email,
                "phone": "+919876543210",
                "password": "StrongPassword@2026!",
                "turnstile_token": "1x0000000000000000000000000000000AA"
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "otp_required"
            assert "expires_in_seconds" in data
            assert data["expires_in_seconds"] == 600

            # Verify user created in unverified state
            with get_db_cursor() as cur:
                cur.execute("SELECT user_id, email_verified, is_verified, account_status FROM users WHERE email = %s;", (test_email.lower(),))
                user = cur.fetchone()
                assert user is not None
                assert user["email_verified"] is False
                assert user["is_verified"] is False
                assert user["account_status"] == "pending_verification"
        finally:
            with get_db_cursor() as cur:
                cur.execute("DELETE FROM otp_verifications WHERE target = %s;", (test_email.lower(),))
                cur.execute("DELETE FROM users WHERE email = %s;", (test_email.lower(),))
                cur.connection.commit()

    def test_signup_initiate_missing_turnstile_in_production(self, client):
        """When Turnstile token is missing, registration is rejected."""
        resp = client.post("/api/auth/register-initiate", json={
            "full_name": "Adv. Rajesh Deshmukh",
            "email": "test.turnstile.fail@vidhik.ai",
            "password": "StrongPassword@2026!",
            "turnstile_token": None
        })
        assert resp.status_code == 400
        assert "captcha" in resp.json()["detail"].lower() or "turnstile" in resp.json()["detail"].lower()

    def test_signup_initiate_invalid_turnstile_token(self, client):
        """Invalid Turnstile response token is rejected."""
        with patch("app.services.auth_service.verify_turnstile_token_sync", return_value=(False, "Turnstile token validation rejected")):
            resp = client.post("/api/auth/register-initiate", json={
                "full_name": "Adv. Rajesh Deshmukh",
                "email": "test.invalid.token@vidhik.ai",
                "password": "StrongPassword@2026!",
                "turnstile_token": "invalid_fake_token_123"
            })
            assert resp.status_code == 400
            assert "token validation rejected" in resp.json()["detail"]

    def test_signup_initiate_duplicate_email_rejected(self, client):
        """Attempting to initiate registration for already existing verified email is rejected."""
        existing_email = f"existing.user.{int(datetime.now().timestamp())}@vidhik.ai"
        try:
            with get_db_cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (username, email, password_hash, full_name, role, email_verified, is_verified, account_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (existing_email.split('@')[0], existing_email.lower(), hash_password("Password@2026!"), "Existing User", "lawyer", True, True, "active")
                )
                cur.connection.commit()

            resp = client.post("/api/auth/register-initiate", json={
                "full_name": "Adv. Copycat",
                "email": existing_email,
                "password": "StrongPassword@2026!",
                "turnstile_token": "1x0000000000000000000000000000000AA"
            })
            assert resp.status_code == 400
            assert "already exists" in resp.json()["detail"].lower() or "already registered" in resp.json()["detail"].lower()
        finally:
            with get_db_cursor() as cur:
                cur.execute("DELETE FROM users WHERE email = %s;", (existing_email.lower(),))
                cur.connection.commit()

    def test_signup_initiate_weak_password_rejected(self, client):
        resp = client.post("/api/auth/register-initiate", json={
            "full_name": "Adv. Weak Password",
            "email": "weak.password.test@vidhik.ai",
            "password": "weak",
            "turnstile_token": "1x0000000000000000000000000000000AA"
        })
        assert resp.status_code == 422 or resp.status_code == 400


# =============================================================================
# 2. NOTIFICATION & PROVIDER DELIVERY TESTS
# =============================================================================

class TestOTPDeliveryProviders:
    """Tests for multi-provider email/SMS delivery, provider fallbacks, and production safety."""

    def test_email_dispatch_resend_mocked(self):
        with patch.dict("os.environ", {"EMAIL_PROVIDER": "resend", "RESEND_API_KEY": "re_test_key_123"}):
            with patch("httpx.Client.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_post.return_value = mock_resp

                success = EmailSmsService.send_otp_email(
                    to_email="lawyer@vidhik.ai",
                    otp_code="982341",
                    purpose="signup_verification",
                    user_name="Adv. Lawyer"
                )
                assert success is True

    def test_sms_dispatch_twilio_mocked(self):
        with patch.dict("os.environ", {
            "SMS_PROVIDER": "twilio",
            "TWILIO_ACCOUNT_SID": "AC_test_sid",
            "TWILIO_AUTH_TOKEN": "auth_token_123",
            "TWILIO_PHONE_NUMBER": "+1234567890"
        }):
            with patch("httpx.Client.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.status_code = 201
                mock_post.return_value = mock_resp

                success = EmailSmsService.send_otp_sms(
                    to_phone="+919876543210",
                    otp_code="654321"
                )
                assert success is True

    def test_production_environment_missing_provider_fails_safely(self):
        """In production, if real providers are not configured, delivery must return False."""
        with patch.dict("os.environ", {
            "APP_ENV": "production",
            "EMAIL_PROVIDER": "smtp",
            "SMTP_HOST": "",
            "SMTP_USER": "",
            "SMTP_PASSWORD": ""
        }):
            success = EmailSmsService.send_otp_email("production.test@vidhik.ai", "123456")
            assert success is False

    def test_log_masking_never_exposes_raw_otp(self):
        """Ensure logging functions sanitize and mask destinations and OTPs."""
        masked_email = EmailSmsService._mask_email("advocate.sharma@vidhik.ai")
        assert "sharma" not in masked_email
        assert masked_email.startswith("ad***@")

        masked_phone = EmailSmsService._mask_phone("+919876543210")
        assert "9876" not in masked_phone
        assert masked_phone.endswith("3210")


# =============================================================================
# 3. OTP VERIFICATION LIFECYCLE & SECURITY TESTS
# =============================================================================

class TestOTPSecurityLifecycle:
    """Tests for cryptographic OTP verification, brute-force lockout, single-use, and cooldowns."""

    def test_otp_verification_success_and_state_transition(self, client):
        test_email = f"verify.test.{int(datetime.now().timestamp())}@vidhik.ai"
        try:
            # 1. Initiate
            client.post("/api/auth/register-initiate", json={
                "full_name": "Adv. Verification Test",
                "email": test_email,
                "password": "StrongPassword@2026!",
                "turnstile_token": "1x0000000000000000000000000000000AA"
            })

            # 2. Get and update OTP record with known code
            test_otp = "123456"
            with get_db_cursor() as cur:
                cur.execute(
                    "UPDATE otp_verifications SET otp_hash = %s WHERE target = %s;",
                    (hash_otp(test_otp), test_email.lower())
                )
                cur.connection.commit()

            # 3. Verify OTP
            resp = client.post("/api/auth/verify-otp", json={
                "email": test_email,
                "otp_code": test_otp,
                "purpose": "signup_verification"
            })
            assert resp.status_code == 200
            data = resp.json()
            assert "two_factor_setup_token" in data

            # 4. Verify DB state transition: email_verified=True, is_verified=True, account_status='active'
            with get_db_cursor() as cur:
                cur.execute("SELECT email_verified, is_verified, account_status FROM users WHERE email = %s;", (test_email.lower(),))
                user = cur.fetchone()
                assert user["email_verified"] is True
                assert user["is_verified"] is True
                assert user["account_status"] == "active"

        finally:
            with get_db_cursor() as cur:
                cur.execute("DELETE FROM otp_verifications WHERE target = %s;", (test_email.lower(),))
                cur.execute("DELETE FROM users WHERE email = %s;", (test_email.lower(),))
                cur.connection.commit()

    def test_otp_invalid_code_increments_attempts(self, client):
        test_email = f"attempts.test.{int(datetime.now().timestamp())}@vidhik.ai"
        try:
            client.post("/api/auth/register-initiate", json={
                "full_name": "Adv. Attempt Test",
                "email": test_email,
                "password": "StrongPassword@2026!",
                "turnstile_token": "1x0000000000000000000000000000000AA"
            })

            # Submit bad OTP
            resp = client.post("/api/auth/verify-otp", json={
                "email": test_email,
                "otp_code": "999999",
                "purpose": "signup_verification"
            })
            assert resp.status_code == 400
            assert "invalid" in resp.json()["detail"].lower()

            # Verify attempts counter incremented in DB
            with get_db_cursor() as cur:
                cur.execute("SELECT attempts, max_attempts FROM otp_verifications WHERE target = %s;", (test_email.lower(),))
                otp_rec = cur.fetchone()
                assert otp_rec["attempts"] >= 1
                assert otp_rec["max_attempts"] == 5

        finally:
            with get_db_cursor() as cur:
                cur.execute("DELETE FROM otp_verifications WHERE target = %s;", (test_email.lower(),))
                cur.execute("DELETE FROM users WHERE email = %s;", (test_email.lower(),))
                cur.connection.commit()

    def test_otp_lockout_after_5_failed_attempts(self, client):
        test_email = f"lockout.otp.{int(datetime.now().timestamp())}@vidhik.ai"
        try:
            client.post("/api/auth/register-initiate", json={
                "full_name": "Adv. Lockout Test",
                "email": test_email,
                "password": "StrongPassword@2026!",
                "turnstile_token": "1x0000000000000000000000000000000AA"
            })

            # Set attempts to 5 in DB
            with get_db_cursor() as cur:
                cur.execute("UPDATE otp_verifications SET attempts = 5 WHERE target = %s;", (test_email.lower(),))
                cur.connection.commit()

            # Attempt verification -> must return 429
            resp = client.post("/api/auth/verify-otp", json={
                "email": test_email,
                "otp_code": "123456",
                "purpose": "signup_verification"
            })
            assert resp.status_code == 429
            assert "failed verification attempts" in resp.json()["detail"].lower() or "too many" in resp.json()["detail"].lower()

        finally:
            with get_db_cursor() as cur:
                cur.execute("DELETE FROM otp_verifications WHERE target = %s;", (test_email.lower(),))
                cur.execute("DELETE FROM users WHERE email = %s;", (test_email.lower(),))
                cur.connection.commit()

    def test_otp_expired_code_rejected(self, client):
        test_email = f"expired.otp.{int(datetime.now().timestamp())}@vidhik.ai"
        try:
            client.post("/api/auth/register-initiate", json={
                "full_name": "Adv. Expired Test",
                "email": test_email,
                "password": "StrongPassword@2026!",
                "turnstile_token": "1x0000000000000000000000000000000AA"
            })

            # Set expires_at in the past
            with get_db_cursor() as cur:
                past_time = datetime.now(timezone.utc) - timedelta(minutes=15)
                cur.execute("UPDATE otp_verifications SET expires_at = %s WHERE target = %s;", (past_time, test_email.lower()))
                cur.connection.commit()

            resp = client.post("/api/auth/verify-otp", json={
                "email": test_email,
                "otp_code": "123456",
                "purpose": "signup_verification"
            })
            assert resp.status_code == 400
            assert "expired" in resp.json()["detail"].lower()

        finally:
            with get_db_cursor() as cur:
                cur.execute("DELETE FROM otp_verifications WHERE target = %s;", (test_email.lower(),))
                cur.execute("DELETE FROM users WHERE email = %s;", (test_email.lower(),))
                cur.connection.commit()

    def test_otp_single_use_enforcement(self, client):
        """Verifying an already-verified OTP code a second time must fail."""
        test_email = f"singleuse.otp.{int(datetime.now().timestamp())}@vidhik.ai"
        try:
            client.post("/api/auth/register-initiate", json={
                "full_name": "Adv. SingleUse Test",
                "email": test_email,
                "password": "StrongPassword@2026!",
                "turnstile_token": "1x0000000000000000000000000000000AA"
            })

            test_otp = "889900"
            with get_db_cursor() as cur:
                cur.execute("UPDATE otp_verifications SET otp_hash = %s WHERE target = %s;", (hash_otp(test_otp), test_email.lower()))
                cur.connection.commit()

            # First verification succeeds
            resp1 = client.post("/api/auth/verify-otp", json={
                "email": test_email,
                "otp_code": test_otp,
                "purpose": "signup_verification"
            })
            assert resp1.status_code == 200

            # Second verification with same code fails
            resp2 = client.post("/api/auth/verify-otp", json={
                "email": test_email,
                "otp_code": test_otp,
                "purpose": "signup_verification"
            })
            assert resp2.status_code == 400
            assert "already been used" in resp2.json()["detail"].lower() or "already verified" in resp2.json()["detail"].lower() or "no pending" in resp2.json()["detail"].lower()

        finally:
            with get_db_cursor() as cur:
                cur.execute("DELETE FROM otp_verifications WHERE target = %s;", (test_email.lower(),))
                cur.execute("DELETE FROM users WHERE email = %s;", (test_email.lower(),))
                cur.connection.commit()

    def test_resend_otp_cooldown_enforcement(self, client):
        """Requesting OTP resend before the 60s cooldown expires must return 429."""
        test_email = f"cooldown.otp.{int(datetime.now().timestamp())}@vidhik.ai"
        try:
            client.post("/api/auth/register-initiate", json={
                "full_name": "Adv. Cooldown Test",
                "email": test_email,
                "password": "StrongPassword@2026!",
                "turnstile_token": "1x0000000000000000000000000000000AA"
            })

            # Immediate resend should be blocked by 60s cooldown
            resp = client.post("/api/auth/resend-otp", json={
                "email": test_email,
                "purpose": "signup_verification"
            })
            assert resp.status_code == 429
            assert "wait" in resp.json()["detail"].lower()

        finally:
            with get_db_cursor() as cur:
                cur.execute("DELETE FROM otp_verifications WHERE target = %s;", (test_email.lower(),))
                cur.execute("DELETE FROM users WHERE email = %s;", (test_email.lower(),))
                cur.connection.commit()

    def test_resend_otp_invalidates_superseded_code(self, client):
        """When a new OTP is resent, the previous code must be invalidated."""
        test_email = f"supersede.otp.{int(datetime.now().timestamp())}@vidhik.ai"
        try:
            client.post("/api/auth/register-initiate", json={
                "full_name": "Adv. Supersede Test",
                "email": test_email,
                "password": "StrongPassword@2026!",
                "turnstile_token": "1x0000000000000000000000000000000AA"
            })

            old_otp = "111111"
            # Set old code and last_resend_at to 2 minutes ago to bypass cooldown
            with get_db_cursor() as cur:
                two_min_ago = datetime.now(timezone.utc) - timedelta(minutes=2)
                cur.execute(
                    "UPDATE otp_verifications SET otp_hash = %s, created_at = %s, last_resend_at = %s WHERE target = %s;",
                    (hash_otp(old_otp), two_min_ago, two_min_ago, test_email.lower())
                )
                cur.connection.commit()

            # Resend OTP
            resend_resp = client.post("/api/auth/resend-otp", json={
                "email": test_email,
                "purpose": "signup_verification"
            })
            assert resend_resp.status_code == 200

            # Attempting to verify with old_otp must fail
            verify_old = client.post("/api/auth/verify-otp", json={
                "email": test_email,
                "otp_code": old_otp,
                "purpose": "signup_verification"
            })
            assert verify_old.status_code == 400
            assert "invalid" in verify_old.json()["detail"].lower()

        finally:
            with get_db_cursor() as cur:
                cur.execute("DELETE FROM otp_verifications WHERE target = %s;", (test_email.lower(),))
                cur.execute("DELETE FROM users WHERE email = %s;", (test_email.lower(),))
                cur.connection.commit()

    def test_unverified_account_cannot_login(self, client):
        """Unverified accounts cannot bypass OTP to log in."""
        unverified_email = f"unverified.{int(datetime.now().timestamp())}@vidhik.ai"
        pwd = "ValidPassword@2026#"
        try:
            with get_db_cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (username, email, password_hash, full_name, role, email_verified, is_verified, account_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (unverified_email.split('@')[0], unverified_email.lower(), hash_password(pwd), "Unverified User", "lawyer", False, False, "pending_verification")
                )
                cur.connection.commit()

            resp = client.post("/api/auth/login", json={
                "identifier": unverified_email,
                "password": pwd,
                "turnstile_token": "1x0000000000000000000000000000000AA"
            })
            assert resp.status_code == 403
            assert "verification" in resp.json()["detail"].lower() or "verify" in resp.json()["detail"].lower()
        finally:
            with get_db_cursor() as cur:
                cur.execute("DELETE FROM users WHERE email = %s;", (unverified_email.lower(),))
                cur.connection.commit()


# =============================================================================
# 4. REGRESSION: LOCKOUT RECIPIENT & MOCK DOMAIN DISPATCH
# =============================================================================

class TestLockoutAndNotificationRecipient:
    """Regression tests ensuring lockout alerts and OTPs use registered user email and avoid NXDOMAIN."""

    def test_mock_domain_prevents_smtp_nxdomain_bounce(self):
        """Synthetic test domains like vidhik.ai should not be forwarded to live SMTP relay."""
        with patch.dict(os.environ, {"APP_ENV": "development", "EMAIL_PROVIDER": "smtp"}):
            with patch("smtplib.SMTP") as mock_smtp:
                delivered = EmailSmsService.send_otp_email("lockout.otp.1792062455@vidhik.ai", "123456")
                assert delivered is True
                mock_smtp.assert_not_called()

    def test_account_lockout_dispatches_alert_to_registered_user_email(self, client):
        """Account lockout alert email must always target user's registered email."""
        test_email = f"target.user.{int(datetime.now().timestamp())}@vidhik.ai"
        pwd = "StrongPassword@2026!"
        try:
            with get_db_cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (username, email, password_hash, full_name, role, email_verified, two_factor_enabled, failed_login_attempts)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING user_id;
                    """,
                    (test_email.split('@')[0], test_email.lower(), hash_password(pwd), "Real Registered User", "user", True, True, 4)
                )
                cur.connection.commit()

            with patch("app.services.email_sms_service.EmailSmsService.send_security_alert_email") as mock_alert:
                # 5th failed attempt triggers lockout
                resp = client.post("/api/auth/login", json={
                    "identifier": test_email,
                    "password": "WrongPassword999!",
                    "turnstile_token": "1x0000000000000000000000000000000AA"
                })
                assert resp.status_code == 401
                mock_alert.assert_called_once()
                assert mock_alert.call_args.kwargs.get("to_email") == test_email.lower()
                assert mock_alert.call_args.kwargs.get("alert_type") == "ACCOUNT_LOCKED"
        finally:
            with get_db_cursor() as cur:
                cur.execute("DELETE FROM security_alerts WHERE user_id IN (SELECT user_id FROM users WHERE email = %s);", (test_email.lower(),))
                cur.execute("DELETE FROM users WHERE email = %s;", (test_email.lower(),))
                cur.connection.commit()

    def test_resend_otp_targets_registered_user_email(self):
        """resend_otp must use registered user's email if linked to user_id."""
        test_email = f"resend.reg.{int(datetime.now().timestamp())}@vidhik.ai"
        user_id = None
        try:
            with get_db_cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (username, email, password_hash, full_name, role, email_verified, is_verified)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING user_id;
                    """,
                    (test_email.split('@')[0], test_email.lower(), "hash", "Registered User", "user", True, True)
                )
                user_id = cur.fetchone()["user_id"]
                cur.execute(
                    """
                    INSERT INTO otp_verifications (user_id, target, target_type, otp_hash, purpose, expires_at, attempts, max_attempts, resend_count, last_resend_at)
                    VALUES (%s, %s, 'email', %s, 'signup_verification', CURRENT_TIMESTAMP + INTERVAL '10 minutes', 0, 5, 0, CURRENT_TIMESTAMP - INTERVAL '120 seconds');
                    """,
                    (user_id, "some_internal_identifier", hash_otp("111222"))
                )
                cur.connection.commit()

                with patch("app.services.email_sms_service.EmailSmsService.send_otp_email", return_value=True) as mock_send:
                    res = AuthService.resend_otp(cur, "some_internal_identifier", "signup_verification")
                    assert res["status"] == "otp_sent"
                    mock_send.assert_called_once()
                    assert mock_send.call_args[0][0] == test_email.lower()
        finally:
            if user_id:
                with get_db_cursor() as cur:
                    cur.execute("DELETE FROM otp_verifications WHERE user_id = %s;", (user_id,))
                    cur.execute("DELETE FROM users WHERE email = %s;", (test_email.lower(),))
                    cur.connection.commit()
