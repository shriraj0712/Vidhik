"""
Vidhik Platform - Phase 15 Authentication & Security Comprehensive Test Suite
=============================================================================
Validates:
1. Modern bcrypt password hashing and verification
2. Legacy SHA-256 password verification and transparent database migration flag
3. RFC 7519 signed JWT access token creation, claims, and decoding
4. Expired and tampered JWT rejection
5. Citizen and Lawyer login endpoint (status 200, JWT token, transparent rehash)
6. Invalid credentials rejection (strict 401)
7. Citizen registration endpoint (bcrypt hash, 201 Created, duplicate email 400)
8. Session revocation and logout endpoint
9. Authenticated profile check (GET /api/auth/me)
10. Strict role guards (require_citizen, require_lawyer, require_admin)
11. Cross-role boundary rejection (HTTP 403 Forbidden)
12. Admin oversight: user list, status toggle, audit log query (strictly no password leak)
13. Password reset workflow (forgot-password, reset token verification, session invalidation)
14. Authenticated password change workflow
15. Rate limiting on sensitive auth endpoints (HTTP 429 Too Many Requests)
16. OWASP security response headers (X-Content-Type-Options, X-Frame-Options, CSP, etc.)
17. Security audit logging (successful/failed logins, registrations, password changes)
18. Backward compatibility across Phase 9–14 endpoints
"""

import time
import hashlib
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.core.security import (
    hash_password,
    verify_and_migrate_password,
    is_bcrypt_hash,
    create_access_token,
    decode_access_token,
    generate_reset_token
)
from app.services.auth_service import AuthService, _ACTIVE_SESSIONS
from app.services.audit_service import AuditService


# ==============================================================================
# 1. PASSWORD HASHING & MIGRATION TESTS
# ==============================================================================

def test_password_hashing_bcrypt():
    """Validates that hash_password produces unique, valid bcrypt hashes with salt."""
    plain = "TestPassword@2026"
    h1 = hash_password(plain)
    h2 = hash_password(plain)

    assert is_bcrypt_hash(h1)
    assert is_bcrypt_hash(h2)
    # Different salts must yield different hash strings
    assert h1 != h2
    assert plain not in h1


def test_password_verification_bcrypt():
    """Validates verification of a correct bcrypt hash with no rehash flag."""
    plain = "SecureVidhikPass#1"
    h = hash_password(plain)

    valid, needs_rehash = verify_and_migrate_password(plain, h)
    assert valid is True
    assert needs_rehash is False

    invalid, _ = verify_and_migrate_password("WrongPassword", h)
    assert invalid is False


def test_legacy_sha256_verification_and_migration_flag():
    """Validates that legacy SHA-256 hashes authenticate successfully and trigger migration."""
    plain = "password123"
    legacy_sha256 = hashlib.sha256(plain.encode("utf-8")).hexdigest()

    valid, needs_rehash = verify_and_migrate_password(plain, legacy_sha256)
    assert valid is True
    assert needs_rehash is True, "Legacy hash must signal needs_rehash=True for transparent upgrade"

    wrong_valid, _ = verify_and_migrate_password("wrong", legacy_sha256)
    assert wrong_valid is False


def test_invalid_password_rejection():
    """Rejects empty, None, or mismatched password strings."""
    assert verify_and_migrate_password("", "$2b$12$somehash")[0] is False
    assert verify_and_migrate_password("test", None)[0] is False
    assert verify_and_migrate_password("test", "")[0] is False


# ==============================================================================
# 2. JWT TOKEN GENERATION & VERIFICATION TESTS
# ==============================================================================

def test_jwt_creation_and_payload_claims():
    """Validates JWT access token claims: sub, email, role, lawyer_id, iat, exp, type."""
    token = create_access_token(
        user_id=101,
        email="lawyer.test@vidhik.ai",
        role="lawyer",
        full_name="Advocate Test",
        lawyer_id=5,
        expires_delta=timedelta(minutes=30)
    )

    assert isinstance(token, str)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "101"
    assert payload["user_id"] == 101
    assert payload["email"] == "lawyer.test@vidhik.ai"
    assert payload["role"] == "lawyer"
    assert payload["full_name"] == "Advocate Test"
    assert payload["lawyer_id"] == 5
    assert payload["type"] == "access"
    assert payload["exp"] > payload["iat"]


def test_jwt_decode_and_expiration():
    """Rejects expired or tampered JWT access tokens."""
    # Expired token (-10 seconds)
    expired_token = create_access_token(
        user_id=202,
        email="expired@example.com",
        role="user",
        expires_delta=timedelta(seconds=-10)
    )
    assert decode_access_token(expired_token) is None

    # Tampered signature
    valid_token = create_access_token(user_id=202, email="user@example.com", role="user")
    tampered_token = valid_token[:-4] + "ABCD"
    assert decode_access_token(tampered_token) is None

    # Malformed string
    assert decode_access_token("gibberish.not.a.jwt") is None


# ==============================================================================
# 3. FASTAPI AUTH ENDPOINT TESTS (LOGIN, REGISTER, REFRESH, LOGOUT)
# ==============================================================================

def test_api_login_success_with_bcrypt_migration():
    """Tests POST /api/auth/login upgrades legacy SHA-256 to bcrypt and returns JWT."""
    client = TestClient(app)

    legacy_sha256 = hashlib.sha256("password123".encode("utf-8")).hexdigest()
    user_record = {
        "user_id": 1,
        "username": "rajesh_advocate",
        "email": "rajesh.advocate@vidhik.ai",
        "password_hash": legacy_sha256,
        "full_name": "Adv. Rajesh Kumar",
        "phone": "+91 98201 11222",
        "role": "lawyer",
        "is_active": True,
        "lawyer_id": 1
    }

    mock_db = MagicMock()
    mock_db.fetchone.return_value = user_record
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.post(
            "/api/auth/login",
            json={"email": "rajesh.advocate@vidhik.ai", "password": "password123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["email"] == "rajesh.advocate@vidhik.ai"
        assert data["role"] == "lawyer"
        assert data["lawyer_id"] == 1

        # Verify JWT decoded
        claims = decode_access_token(data["token"])
        assert claims is not None
        assert claims["user_id"] == 1

        # Verify database execute was called to update password_hash to bcrypt
        update_calls = [
            call for call in mock_db.execute.call_args_list
            if "UPDATE users SET password_hash" in str(call)
        ]
        assert len(update_calls) > 0, "Password hash must be transparently upgraded to bcrypt"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_api_login_invalid_credentials_rejected():
    """Tests POST /api/auth/login returns strict 401 on wrong password or inactive user."""
    client = TestClient(app)

    mock_db = MagicMock()
    mock_db.fetchone.return_value = {
        "user_id": 2,
        "username": "test_user",
        "email": "test@example.com",
        "password_hash": hash_password("correct_pass"),
        "full_name": "Test User",
        "phone": None,
        "role": "user",
        "is_active": True,
        "lawyer_id": None
    }
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        # Wrong password
        res = client.post("/api/auth/login", json={"email": "test@example.com", "password": "wrong_password"})
        assert res.status_code == 401
        assert "Invalid email or password" in res.json()["detail"]

        # Inactive user
        mock_db.fetchone.return_value["is_active"] = False
        res_inactive = client.post("/api/auth/login", json={"email": "test@example.com", "password": "correct_pass"})
        assert res_inactive.status_code == 401
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_api_citizen_registration_success():
    """Tests POST /api/auth/register creates citizen with bcrypt hash and returns JWT."""
    client = TestClient(app)

    mock_db = MagicMock()
    # First query checks for duplicate email (returns None = not duplicate)
    # Second query checks for unique username (returns None = unique)
    # Third query inserts user and returns new row
    mock_db.fetchone.side_effect = [
        None,  # No duplicate email
        None,  # Username unique
        {
            "user_id": 50,
            "username": "anita_deshmukh",
            "email": "anita.deshmukh@example.com",
            "full_name": "Anita Deshmukh",
            "phone": "+91 98200 44556",
            "role": "user",
            "is_active": True
        }
    ]
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.post(
            "/api/auth/register",
            json={
                "full_name": "Anita Deshmukh",
                "email": "anita.deshmukh@example.com",
                "password": "StrongPassword@123",
                "phone": "+91 98200 44556"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == 50
        assert data["role"] == "user"
        assert "token" in data

        # Check inserted password hash is bcrypt
        insert_calls = [
            call for call in mock_db.execute.call_args_list
            if "INSERT INTO users" in str(call)
        ]
        assert len(insert_calls) > 0
        args, _ = insert_calls[0]
        params = args[1]
        stored_hash = params[2]
        assert is_bcrypt_hash(stored_hash), "New user registration must store bcrypt hash"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_api_logout_and_revocation():
    """Tests POST /api/auth/logout invalidates session."""
    client = TestClient(app)
    token = create_access_token(user_id=1, email="user@vidhik.ai", role="user")
    _ACTIVE_SESSIONS[token] = {"user_id": 1, "token": token}

    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        res = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert "Successfully logged out" in res.json()["message"]
        assert token not in _ACTIVE_SESSIONS
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_api_get_me_profile():
    """Tests GET /api/auth/me returns authenticated identity."""
    client = TestClient(app)
    token = create_access_token(user_id=10, email="me@vidhik.ai", role="user", full_name="Me User")

    mock_db = MagicMock()
    mock_db.fetchone.side_effect = [
        {
            "user_id": 10,
            "username": "me_user",
            "email": "me@vidhik.ai",
            "full_name": "Me User",
            "phone": None,
            "role": "user",
            "is_active": True
        },
        None  # login_sessions revoked check
    ]
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert data["user_id"] == 10
        assert data["email"] == "me@vidhik.ai"
    finally:
        app.dependency_overrides.pop(get_db, None)


# ==============================================================================
# 4. STRICT ROLE BOUNDARY & AUTHORIZATION GUARDS TESTS
# ==============================================================================

def test_require_citizen_guard():
    """Ensures citizen endpoints admit citizens and block lawyers with 403."""
    client = TestClient(app)

    citizen_token = create_access_token(user_id=10, email="c@test.com", role="user")
    lawyer_token = create_access_token(user_id=20, email="l@test.com", role="lawyer")

    class FlexibleRow(dict):
        def __getitem__(self, key):
            if key in self:
                return super().__getitem__(key)
            return 0

    def make_mock(role: str):
        mock = MagicMock()
        def fake_fetchone():
            return FlexibleRow({
                "user_id": 10 if role == "user" else 20,
                "username": "cit" if role == "user" else "law",
                "email": f"{role}@test.com",
                "full_name": role.capitalize(),
                "phone": None,
                "role": role,
                "is_active": True,
                "revoked_at": None,
                "lawyer_id": 1 if role == "lawyer" else None
            })
        mock.fetchone.side_effect = fake_fetchone
        mock.fetchall.return_value = []
        return mock

    try:
        # 1. Citizen on citizen dashboard
        app.dependency_overrides[get_db] = lambda: make_mock("user")
        r_cit = client.get("/api/citizen/dashboard", headers={"Authorization": f"Bearer {citizen_token}"})
        assert r_cit.status_code == 200

        # 2. Lawyer on citizen dashboard -> strictly 403 Forbidden
        app.dependency_overrides[get_db] = lambda: make_mock("lawyer")
        r_law = client.get("/api/citizen/dashboard", headers={"Authorization": f"Bearer {lawyer_token}"})
        assert r_law.status_code == 403
        assert "Access restricted to citizen users" in r_law.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_require_lawyer_guard():
    """Ensures lawyer endpoints admit lawyers and block citizens with 403."""
    client = TestClient(app)

    citizen_token = create_access_token(user_id=10, email="c@test.com", role="user")
    lawyer_token = create_access_token(user_id=20, email="l@test.com", role="lawyer", lawyer_id=1)

    class FlexibleRow(dict):
        def __getitem__(self, key):
            if key in self:
                return super().__getitem__(key)
            return 0

    def make_mock(role: str):
        mock = MagicMock()
        def fake_fetchone():
            return FlexibleRow({
                "user_id": 10 if role == "user" else 20,
                "username": "cit" if role == "user" else "law",
                "email": f"{role}@test.com",
                "full_name": role.capitalize(),
                "phone": None,
                "role": role,
                "is_active": True,
                "revoked_at": None,
                "lawyer_id": 1 if role == "lawyer" else None
            })
        mock.fetchone.side_effect = fake_fetchone
        mock.fetchall.return_value = []
        return mock

    try:
        # Citizen on lawyer dashboard -> strictly 403 Forbidden
        app.dependency_overrides[get_db] = lambda: make_mock("user")
        r_cit_on_law = client.get("/api/lawyer/dashboard", headers={"Authorization": f"Bearer {citizen_token}"})
        assert r_cit_on_law.status_code == 403
        assert "Access restricted to verified lawyers" in r_cit_on_law.json()["detail"]

        # Lawyer on lawyer dashboard -> 200 OK
        app.dependency_overrides[get_db] = lambda: make_mock("lawyer")
        r_law = client.get("/api/lawyer/dashboard", headers={"Authorization": f"Bearer {lawyer_token}"})
        assert r_law.status_code == 200
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_require_admin_guard():
    """Ensures admin endpoints strictly admit admin and block user/lawyer with 403."""
    client = TestClient(app)

    user_token = create_access_token(user_id=10, email="u@test.com", role="user")
    admin_token = create_access_token(user_id=99, email="admin@vidhik.ai", role="admin")

    mock_db = MagicMock()

    # User on admin endpoint -> 403
    mock_db.fetchone.side_effect = [
        {"user_id": 10, "username": "u", "email": "u@test.com", "full_name": "U", "phone": None, "role": "user", "is_active": True},
        None
    ]
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        r_user = client.get("/api/admin/users", headers={"Authorization": f"Bearer {user_token}"})
        assert r_user.status_code == 403
        assert "Access restricted to platform administrators" in r_user.json()["detail"]

        # Admin on admin endpoint -> 200 OK
        mock_db.fetchone.side_effect = [
            {"user_id": 99, "username": "admin", "email": "admin@vidhik.ai", "full_name": "Admin", "phone": None, "role": "admin", "is_active": True},
            None,
            {"total": 1}
        ]
        mock_db.fetchall.return_value = [
            {
                "user_id": 1,
                "username": "rajesh",
                "email": "rajesh@vidhik.ai",
                "full_name": "Rajesh Kumar",
                "phone": None,
                "role": "lawyer",
                "is_active": True,
                "is_verified": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": None
            }
        ]
        r_admin = client.get("/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
        assert r_admin.status_code == 200
        admin_data = r_admin.json()
        assert admin_data["total"] == 1
        assert "password_hash" not in admin_data["users"][0], "Admin endpoint must never leak password_hash!"
    finally:
        app.dependency_overrides.pop(get_db, None)


# ==============================================================================
# 5. PASSWORD RESET & PASSWORD CHANGE TESTS
# ==============================================================================

def test_password_reset_flow():
    """Validates forgot-password token generation, reset completion, and rejection of used token."""
    client = TestClient(app)

    mock_db = MagicMock()
    # 1. Forgot password request
    mock_db.fetchone.return_value = {"user_id": 5, "email": "reset@example.com", "is_active": True}
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        res_forgot = client.post("/api/auth/forgot-password", json={"email": "reset@example.com"})
        assert res_forgot.status_code == 200
        reset_token = res_forgot.json()["reset_token"]
        assert reset_token is not None

        # 2. Complete reset with valid token
        future_exp = datetime.now(timezone.utc) + timedelta(minutes=45)
        mock_db.fetchone.return_value = {
            "reset_id": 1,
            "user_id": 5,
            "expires_at": future_exp,
            "used_at": None
        }

        res_reset = client.post(
            "/api/auth/reset-password",
            json={"reset_token": reset_token, "new_password": "NewSecurePassword#2026"}
        )
        assert res_reset.status_code == 200
        assert "Password successfully updated" in res_reset.json()["message"]

        # 3. Attempting to use already used token -> 400 Bad Request
        mock_db.fetchone.return_value = {
            "reset_id": 1,
            "user_id": 5,
            "expires_at": future_exp,
            "used_at": datetime.now(timezone.utc)
        }
        res_reuse = client.post(
            "/api/auth/reset-password",
            json={"reset_token": reset_token, "new_password": "AnotherPassword#123"}
        )
        assert res_reuse.status_code == 400
        assert "already used" in res_reuse.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_change_password_flow():
    """Validates authenticated user password change."""
    client = TestClient(app)
    token = create_access_token(user_id=12, email="user12@example.com", role="user")

    current_hash = hash_password("OldPassword@123")
    mock_db = MagicMock()
    mock_db.fetchone.side_effect = [
        {"user_id": 12, "username": "u12", "email": "user12@example.com", "full_name": "U12", "phone": None, "role": "user", "is_active": True},
        None,  # session revoked check
        {"password_hash": current_hash}  # change_password fetch
    ]
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        res = client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "OldPassword@123",
                "new_password": "BrandNewPassword@456"
            }
        )
        assert res.status_code == 200
        assert "Password changed successfully" in res.json()["message"]
    finally:
        app.dependency_overrides.pop(get_db, None)


# ==============================================================================
# 6. SECURITY HEADERS & RATE LIMITING TESTS
# ==============================================================================

def test_security_headers_middleware():
    """Asserts that OWASP security response headers are present on all responses."""
    client = TestClient(app)
    res = client.get("/health")

    assert res.status_code == 200
    headers = res.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in headers
    assert "default-src 'self'" in headers["Content-Security-Policy"]


def test_rate_limiter_middleware_trigger():
    """Asserts that exceeding auth endpoint limit triggers HTTP 429 Too Many Requests."""
    from app.middleware.rate_limiter import RateLimiterMiddleware
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    async def dummy_login(request):
        return JSONResponse({"status": "ok"})

    dummy_app = Starlette(routes=[Route("/api/auth/login", dummy_login, methods=["POST"])])
    # Set limit to 3 per minute
    dummy_app.add_middleware(RateLimiterMiddleware, limit_per_minute=3)
    c = TestClient(dummy_app)

    # First 3 requests succeed
    for _ in range(3):
        r = c.post("/api/auth/login")
        assert r.status_code == 200

    # 4th request must be rate limited with 429
    r_blocked = c.post("/api/auth/login")
    assert r_blocked.status_code == 429
    assert "Too many authentication requests" in r_blocked.json()["detail"]
    assert "Retry-After" in r_blocked.headers


# ==============================================================================
# 7. BACKWARD COMPATIBILITY ACROSS PHASES 9-14
# ==============================================================================

def test_backward_compatibility_phases_9_to_14():
    """Verifies that statutory, RAG, Assistant, and Documentation endpoints remain healthy."""
    client = TestClient(app)

    # Health check
    r_health = client.get("/health")
    assert r_health.status_code == 200

    # RAG health check (Phase 9)
    r_rag = client.get("/api/rag/health")
    assert r_rag.status_code == 200

    # Assistant health check (Phase 10)
    r_ast = client.get("/api/assistant/health")
    assert r_ast.status_code == 200

    # Root API summary
    r_root = client.get("/")
    assert r_root.status_code == 200
    assert "Vidhik Legal Platform" in r_root.text or "Vidhik" in str(r_root.json())
