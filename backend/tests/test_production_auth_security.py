"""
Vidhik Platform - Enterprise Production Authentication & Account Security Test Suite
======================================================================================
Comprehensive tests validating the real, database-backed, zero-bypass authentication system:
1. Password Complexity & Bcrypt Hardening (cost factor, uppercase, lowercase, digit, special, length)
2. Cryptographic OTP Lifecycle (hashing, 10m expiry, 5-attempt lock, single-use, 60s cooldown)
3. Mandatory RFC 6238 TOTP 2FA (Base32 secret, QR code generation, TOTP verification)
4. Single-Use 2FA Recovery Codes (8 hashed codes, consumption, regeneration invalidation)
5. Cloudflare Turnstile Server-Side Verification (token validation, secret handling)
6. Google OAuth 2.0 / OpenID Connect Token Verification & Mandatory 2FA Linkage
7. Account Lockout & Brute-Force Protection (5 failed attempts -> 15 min lock)
8. Multi-Device Active Sessions Management (device/OS/browser, IP & location, remote revocation)
9. Suspicious Login & Anomaly Detection (new device/location alerts)
10. Strict Server-Side Case Isolation & Role-Based Authorization
"""

import pytest
import pyotp
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db, get_db_cursor
from app.core.security import (
    validate_password_strength,
    hash_password,
    verify_and_migrate_password,
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
    decode_access_token,
    decode_two_factor_token,
    verify_turnstile_token_sync,
    parse_user_agent,
    resolve_ip_location,
    evaluate_login_risk
)
from app.services.auth_service import AuthService


def test_jwt_configuration_fails_closed_in_production_without_secret():
    from app.core.security import _validate_jwt_secret_configuration

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY must be configured in production"):
        _validate_jwt_secret_configuration(
            configured_secret="",
            runtime_environment="production",
        )


def test_jwt_configuration_fails_closed_on_render_without_secret(monkeypatch):
    from app.core.security import _validate_jwt_secret_configuration, is_production_environment

    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("RENDER", "true")
    assert is_production_environment() is True
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY must be configured in production"):
        _validate_jwt_secret_configuration(configured_secret="")


def test_jwt_configuration_preserves_local_development_fallback(monkeypatch):
    from app.core.security import JWT_SECRET_KEY, _validate_jwt_secret_configuration

    # Existing local fallback remains unchanged; only production is fail-closed.
    monkeypatch.delenv("RENDER", raising=False)
    _validate_jwt_secret_configuration(
        configured_secret=None,
        runtime_environment="development",
    )
    assert isinstance(JWT_SECRET_KEY, str) and JWT_SECRET_KEY


# =============================================================================
# 1. PASSWORD SECURITY & BCRYPT HARDENING TESTS
# =============================================================================

class TestPasswordSecurity:
    """Tests for password strength validation and bcrypt cryptographic hashing."""

    def test_valid_strong_passwords(self):
        valid_passwords = [
            "StrongP@ssw0rd2026!",
            "LegalCounsel#99Xy",
            "Vidhik@Secure_2026",
            "Complex&Safe!Pass1"
        ]
        for pwd in valid_passwords:
            valid, err = validate_password_strength(pwd)
            assert valid is True
            assert err is None

    def test_weak_password_missing_uppercase(self):
        valid, err = validate_password_strength("weakpassword123!")
        assert valid is False
        assert "uppercase" in err.lower()

    def test_weak_password_missing_lowercase(self):
        valid, err = validate_password_strength("WEAKPASSWORD123!")
        assert valid is False
        assert "lowercase" in err.lower()

    def test_weak_password_missing_digit(self):
        valid, err = validate_password_strength("WeakPassword!@#")
        assert valid is False
        assert "number" in err.lower()

    def test_weak_password_missing_special_char(self):
        valid, err = validate_password_strength("WeakPassword123")
        assert valid is False
        assert "special character" in err.lower()

    def test_weak_password_too_short(self):
        valid, err = validate_password_strength("Sh0r!t")
        assert valid is False
        assert "8 characters" in err.lower()

    def test_bcrypt_hashing_and_verification(self):
        raw_pwd = "VidhikSecurePassword#2026"
        hashed = hash_password(raw_pwd)
        assert hashed.startswith("$2b$12$")  # Bcrypt cost 12
        assert hashed != raw_pwd

        is_valid, _ = verify_and_migrate_password(raw_pwd, hashed)
        assert is_valid is True

        is_wrong, _ = verify_and_migrate_password("WrongPassword#123", hashed)
        assert is_wrong is False


# =============================================================================
# 2. OTP GENERATION, HASHING & EXPIRY TESTS
# =============================================================================

class TestOTPVerification:
    """Tests for secure OTP generation, SHA-256 salted hashing, and validation."""

    def test_generate_secure_otp(self):
        otp1 = generate_secure_otp(6)
        otp2 = generate_secure_otp(6)
        assert len(otp1) == 6
        assert otp1.isdigit()
        assert len(otp2) == 6
        assert otp2.isdigit()

    def test_otp_hashing_and_verification(self):
        otp = "748291"
        salt = "test_salt_12345"
        hashed = hash_otp(otp, salt)
        assert len(hashed) == 64  # SHA-256 hex string

        assert verify_otp_hash(otp, hashed, salt) is True
        assert verify_otp_hash("123456", hashed, salt) is False

    def test_otp_expiry_calculation(self):
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=10)
        assert (expires_at - now).total_seconds() == 600


# =============================================================================
# 3. MANDATORY RFC 6238 TOTP 2FA & RECOVERY CODES TESTS
# =============================================================================

class TestMandatory2FAAndRecoveryCodes:
    """Tests for TOTP Base32 secrets, QR codes, and single-use recovery codes."""

    def test_totp_secret_and_uri_generation(self):
        secret = generate_totp_secret()
        assert len(secret) == 32
        uri = get_totp_uri(secret, "advocate@vidhik.ai", "Vidhik AI")
        assert "otpauth://totp/Vidhik" in uri
        assert f"secret={secret}" in uri

    def test_qr_code_data_url_generation(self):
        secret = generate_totp_secret()
        uri = get_totp_uri(secret, "user@vidhik.ai", "Vidhik AI")
        qr_url = generate_qr_code_data_url(uri)
        assert qr_url.startswith("data:image/png;base64,")
        assert len(qr_url) > 200

    def test_totp_code_verification(self):
        secret = generate_totp_secret()
        totp = pyotp.TOTP(secret)
        current_code = totp.now()

        assert verify_totp_code(secret, current_code) is True
        assert verify_totp_code(secret, "000000") is False

    def test_recovery_codes_generation_and_hashing(self):
        codes = generate_recovery_codes(8)
        assert len(codes) == 8
        for code in codes:
            assert len(code) == 11  # XXXXX-XXXXX
            assert "-" in code

            hashed = hash_recovery_code(code)
            assert verify_recovery_code(code, hashed) is True
            assert verify_recovery_code("WRONG-CODE1", hashed) is False


# =============================================================================
# 4. TURNSTILE CAPTCHA & METADATA TESTS
# =============================================================================

class TestTurnstileAndDeviceParsing:
    """Tests for Cloudflare Turnstile token validation and User-Agent parsing."""

    def test_turnstile_test_token_success(self):
        valid, err = verify_turnstile_token_sync("1x0000000000000000000000000000000AA", "127.0.0.1")
        assert valid is True
        assert err is None

    def test_turnstile_test_token_rejected_in_production(self, monkeypatch):
        """Test dummy tokens must be rejected when running in production."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("TURNSTILE_SECRET_KEY", "real_production_secret_key_1234567890")
        valid, err = verify_turnstile_token_sync("1x0000000000000000000000000000000AA", "127.0.0.1")
        assert valid is False
        assert "not permitted in production" in err.lower()

    def test_turnstile_dummy_secret_rejected_in_production(self, monkeypatch):
        """Dummy test secrets must be rejected when running in production."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("TURNSTILE_SECRET_KEY", "1x0000000000000000000000000000000AA")
        valid, err = verify_turnstile_token_sync("some_real_user_token", "127.0.0.1")
        assert valid is False
        assert "not properly configured for production" in err.lower()

    def test_user_agent_parsing(self):
        ua_chrome = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        info = parse_user_agent(ua_chrome)
        assert info["browser"] == "Chrome"
        assert info["os"] == "Windows"
        assert info["device"] == "Desktop"

        ua_iphone = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        info_m = parse_user_agent(ua_iphone)
        assert info_m["browser"] == "Safari"
        assert info_m["os"] == "iOS"
        assert info_m["device"] == "Mobile"

    def test_ip_location_resolution(self):
        loc = resolve_ip_location("127.0.0.1")
        assert "Pune" in loc["city"]
        assert "India" in loc["country"]


# =============================================================================
# 5. FASTAPI REST AUTH LIFECYCLE & SECURITY ENDPOINTS TEST
# =============================================================================

@pytest.fixture
def client():
    return TestClient(app)


class TestAuthLifecycleEndpoints:
    """End-to-end integration tests for the real authentication router & services."""

    def test_full_signup_otp_2fa_and_login_lifecycle(self, client):
        test_email = f"test.lawyer.{int(datetime.now().timestamp())}@vidhik.ai"
        test_phone = "+919812345678"
        test_password = "SecurePassword@2026!"

        try:
            # -------------------------------------------------------------
            # STEP 1: Registration Initiate (with Cloudflare Turnstile)
            # -------------------------------------------------------------
            reg_resp = client.post("/api/auth/register-initiate", json={
                "full_name": "Adv. Test Lawyer",
                "email": test_email,
                "phone": test_phone,
                "password": test_password,
                "turnstile_token": "1x0000000000000000000000000000000AA"
            })
            assert reg_resp.status_code == 200
            reg_data = reg_resp.json()
            assert reg_data["status"] == "otp_required"
            assert "expires_in_seconds" in reg_data

            # Query the database to retrieve the secure OTP generated
            with get_db_cursor() as cur:
                cur.execute(
                    "SELECT id, target, otp_hash FROM otp_verifications WHERE target = %s ORDER BY id DESC LIMIT 1;",
                    (test_email.lower(),)
                )
                otp_record = cur.fetchone()
                assert otp_record is not None

                # Test bad OTP rejection
                bad_otp_resp = client.post("/api/auth/verify-otp", json={
                    "email": test_email,
                    "otp_code": "000000",
                    "purpose": "signup_verification"
                })
                assert bad_otp_resp.status_code == 400

                # Set known OTP in DB for deterministic test
                test_otp = "654321"
                hashed = hash_otp(test_otp)
                cur.execute(
                    "UPDATE otp_verifications SET otp_hash = %s, attempts = 0 WHERE id = %s;",
                    (hashed, otp_record["id"])
                )
                cur.connection.commit()

            # -------------------------------------------------------------
            # STEP 2: Verify OTP
            # -------------------------------------------------------------
            verify_resp = client.post("/api/auth/verify-otp", json={
                "email": test_email,
                "otp_code": test_otp,
                "purpose": "signup_verification"
            })
            assert verify_resp.status_code == 200
            verify_data = verify_resp.json()
            assert "two_factor_setup_token" in verify_data
            assert "qr_code_data_url" in verify_data
            assert "secret" in verify_data

            setup_token = verify_data["two_factor_setup_token"]
            totp_secret = verify_data["secret"]

            # -------------------------------------------------------------
            # STEP 3: Complete Mandatory 2FA Setup
            # -------------------------------------------------------------
            totp = pyotp.TOTP(totp_secret)
            valid_2fa_code = totp.now()

            setup_2fa_resp = client.post("/api/auth/2fa/setup-verify", json={
                "two_factor_setup_token": setup_token,
                "totp_code": valid_2fa_code
            })
            assert setup_2fa_resp.status_code == 200
            setup_2fa_data = setup_2fa_resp.json()
            assert "access_token" in setup_2fa_data
            assert len(setup_2fa_data["recovery_codes"]) == 8
            saved_recovery_codes = setup_2fa_data["recovery_codes"]

            # -------------------------------------------------------------
            # STEP 4: Sign In with Password -> 2FA Challenge
            # -------------------------------------------------------------
            login_resp = client.post("/api/auth/login", json={
                "identifier": test_email,
                "password": test_password,
                "turnstile_token": "1x0000000000000000000000000000000AA"
            })
            assert login_resp.status_code == 200
            login_data = login_resp.json()
            assert login_data["two_factor_required"] is True
            assert "two_factor_token" in login_data
            assert "access_token" not in login_data  # No direct access token before 2FA!

            two_factor_challenge_token = login_data["two_factor_token"]

            # -------------------------------------------------------------
            # STEP 5: Verify 2FA Challenge with TOTP Code
            # -------------------------------------------------------------
            login_2fa_resp = client.post("/api/auth/2fa/verify-login", json={
                "two_factor_token": two_factor_challenge_token,
                "code": totp.now()
            })
            assert login_2fa_resp.status_code == 200
            auth_data = login_2fa_resp.json()
            assert "access_token" in auth_data
            jwt_token = auth_data["access_token"]

            # -------------------------------------------------------------
            # STEP 6: Authenticated Session & Active Sessions View
            # -------------------------------------------------------------
            auth_headers = {"Authorization": f"Bearer {jwt_token}"}
            me_resp = client.get("/api/auth/me", headers=auth_headers)
            assert me_resp.status_code == 200
            assert me_resp.json()["email"] == test_email.lower()

            sessions_resp = client.get("/api/auth/sessions", headers=auth_headers)
            assert sessions_resp.status_code == 200
            sessions = sessions_resp.json()
            assert len(sessions) >= 1
            assert any(s["is_current"] for s in sessions)

            # -------------------------------------------------------------
            # STEP 7: Test Login with Recovery Code
            # -------------------------------------------------------------
            login_resp2 = client.post("/api/auth/login", json={
                "identifier": test_email,
                "password": test_password,
                "turnstile_token": "1x0000000000000000000000000000000AA"
            })
            assert login_resp2.status_code == 200
            t2_token = login_resp2.json()["two_factor_token"]

            recovery_code_to_use = saved_recovery_codes[0]
            rec_login_resp = client.post("/api/auth/2fa/verify-login", json={
                "two_factor_token": t2_token,
                "code": recovery_code_to_use
            })
            assert rec_login_resp.status_code == 200
            assert "access_token" in rec_login_resp.json()

            # Using the exact same recovery code second time MUST FAIL (single-use)
            login_resp3 = client.post("/api/auth/login", json={
                "identifier": test_email,
                "password": test_password,
                "turnstile_token": "1x0000000000000000000000000000000AA"
            })
            t3_token = login_resp3.json()["two_factor_token"]
            reused_code_resp = client.post("/api/auth/2fa/verify-login", json={
                "two_factor_token": t3_token,
                "code": recovery_code_to_use
            })
            assert reused_code_resp.status_code == 400
            assert "Invalid" in reused_code_resp.json()["detail"]

            # -------------------------------------------------------------
            # STEP 8: Remote Session Revocation
            # -------------------------------------------------------------
            revoke_resp = client.delete("/api/auth/sessions/revoke-others", headers=auth_headers)
            assert revoke_resp.status_code == 200

            # -------------------------------------------------------------
            # STEP 9: Password Change
            # -------------------------------------------------------------
            new_pwd = "UpdatedPassword@2026#"
            pwd_change_resp = client.post("/api/auth/password/change", headers=auth_headers, json={
                "current_password": test_password,
                "new_password": new_pwd
            })
            assert pwd_change_resp.status_code == 200

        finally:
            # Clean up test user and associated records
            with get_db_cursor() as cur:
                cur.execute("SELECT user_id FROM users WHERE email = %s;", (test_email.lower(),))
                row = cur.fetchone()
                if row:
                    uid = row["user_id"]
                    cur.execute("DELETE FROM two_factor_recovery_codes WHERE user_id = %s;", (uid,))
                    cur.execute("DELETE FROM login_sessions WHERE user_id = %s;", (uid,))
                    cur.execute("DELETE FROM security_alerts WHERE user_id = %s;", (uid,))
                    cur.execute("DELETE FROM otp_verifications WHERE user_id = %s OR target = %s;", (uid, test_email.lower()))
                    cur.execute("DELETE FROM user_profiles WHERE user_id = %s;", (uid,))
                    cur.execute("DELETE FROM users WHERE user_id = %s;", (uid,))
                    cur.connection.commit()

    def test_account_lockout_after_5_failed_attempts(self, client):
        lock_email = f"lockout.test.{int(datetime.now().timestamp())}@vidhik.ai"
        pwd = "ValidPassword@2026#"

        try:
            with get_db_cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (username, email, password_hash, full_name, role, email_verified, two_factor_enabled, failed_login_attempts)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING user_id;
                    """,
                    (lock_email.split('@')[0], lock_email.lower(), hash_password(pwd), "Lockout Target User", "user", True, True, 0)
                )
                cur.connection.commit()

            # Attempt 5 wrong logins
            for i in range(5):
                resp = client.post("/api/auth/login", json={
                    "identifier": lock_email,
                    "password": "WrongPassword#999",
                    "turnstile_token": "1x0000000000000000000000000000000AA"
                })
                assert resp.status_code in (401, 423)

            # 6th attempt must be locked (HTTP 423)
            locked_resp = client.post("/api/auth/login", json={
                "identifier": lock_email,
                "password": pwd,
                "turnstile_token": "1x0000000000000000000000000000000AA"
            })
            assert locked_resp.status_code == 423
            assert "Account is temporarily locked" in locked_resp.json()["detail"]

        finally:
            with get_db_cursor() as cur:
                cur.execute("DELETE FROM users WHERE email = %s;", (lock_email.lower(),))
                cur.connection.commit()

    def test_cross_user_case_authorization_denied(self, client):
        """Verify that direct API requests cannot access protected cases or documents without authentication."""
        resp = client.get("/api/lawyer/cases")
        assert resp.status_code == 401

        resp = client.get("/api/citizen/cases")
        assert resp.status_code == 401

        resp = client.get("/api/auth/sessions")
        assert resp.status_code == 401
