"""
Vidhik Platform - Enterprise Authentication & Security API Router
===================================================================
Production-grade RESTful API endpoints for:
- Cloudflare Turnstile CAPTCHA validation
- Multi-channel OTP verification (Email & SMS)
- Mandatory RFC 6238 TOTP Two-Factor Authentication
- One-time emergency recovery codes
- Real Google OAuth 2.0 / OpenID Connect identity validation
- Real-time active sessions & remote revocation
- Anomaly detection & security incident alerts
- Password lifecycle & brute-force protected reset workflows
"""

import os
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, Any, List

from app.database import get_db
from app.schemas.auth import (
    RegisterInitiateRequest,
    VerifyOtpRequest,
    ResendOtpRequest,
    LoginRequest,
    GoogleLoginRequest,
    TwoFactorSetupVerifyRequest,
    TwoFactorLoginRequest,
    RegenerateRecoveryCodesRequest,
    RegenerateRecoveryCodesResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    AuthUserResponse,
    SessionListResponse,
    SecurityAlertListResponse,
    TurnstileConfigResponse,
    GoogleConfigResponse
)
from app.services.auth_service import AuthService, get_authenticated_user
from app.core.security import (
    TURNSTILE_SITE_KEY,
    GOOGLE_CLIENT_ID,
    is_production_environment,
    TEST_TURNSTILE_SITE_KEYS
)

router = APIRouter(prefix="/api/auth", tags=["Authentication & Security"])


def _get_client_ip(request: Request) -> str:
    """Extracts client IP from proxy headers or socket."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


# ==============================================================================
# 1. PUBLIC CONFIGURATION ENDPOINTS
# ==============================================================================

@router.get("/turnstile-config", response_model=TurnstileConfigResponse, summary="Get Turnstile Public Key")
def get_turnstile_config():
    """Returns the Cloudflare Turnstile public site key for frontend widget mounting."""
    site_key = os.getenv("TURNSTILE_SITE_KEY", TURNSTILE_SITE_KEY)
    if is_production_environment() and site_key in TEST_TURNSTILE_SITE_KEYS:
        return TurnstileConfigResponse(
            site_key="",
            enabled=False
        )
    return TurnstileConfigResponse(
        site_key=site_key,
        enabled=bool(site_key)
    )


@router.get("/google-config", response_model=GoogleConfigResponse, summary="Get Google OAuth Client ID")
def get_google_config():
    """Returns the public Google Client ID for Google Identity Services."""
    client_id = os.getenv("GOOGLE_CLIENT_ID", GOOGLE_CLIENT_ID)
    return GoogleConfigResponse(
        client_id=client_id,
        enabled=bool(client_id)
    )


# ==============================================================================
# 2. REGISTRATION & OTP VERIFICATION
# ==============================================================================

@router.post("/register-initiate", status_code=status.HTTP_200_OK, summary="Initiate Account Registration & OTP Dispatch")
def register_initiate(
    payload: RegisterInitiateRequest,
    request: Request,
    db: RealDictCursor = Depends(get_db)
):
    """
    Step 1 of Signup: Validates CAPTCHA, validates email/phone, enforces password complexity,
    creates pending account, and dispatches real 6-digit cryptographic OTP.
    """
    ip_addr = _get_client_ip(request)
    ua_str = request.headers.get("user-agent")

    return AuthService.initiate_registration(
        db=db,
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
        confirm_password=payload.confirm_password,
        phone=payload.phone,
        turnstile_token=payload.turnstile_token,
        ip_address=ip_addr,
        user_agent=ua_str
    )


@router.post("/register", summary="Backward-Compatible Registration Endpoint")
def register_legacy_alias(
    payload: RegisterInitiateRequest,
    request: Request,
    db: RealDictCursor = Depends(get_db)
):
    """Alias for /register-initiate to preserve backward compatibility."""
    return register_initiate(payload=payload, request=request, db=db)


@router.post("/verify-otp", summary="Verify OTP & Initiate Mandatory 2FA Setup")
def verify_otp(
    payload: VerifyOtpRequest,
    request: Request,
    db: RealDictCursor = Depends(get_db)
):
    """
    Step 2 of Signup: Verifies 6-digit OTP code against secure database record.
    On success, marks account identity as verified and returns TOTP 2FA setup credentials.
    """
    ip_addr = _get_client_ip(request)
    ua_str = request.headers.get("user-agent")
    target = payload.target or payload.email or payload.phone

    return AuthService.verify_otp(
        db=db,
        target=target,
        otp_code=payload.otp_code,
        purpose=payload.purpose,
        ip_address=ip_addr,
        user_agent=ua_str
    )


@router.post("/resend-otp", summary="Resend OTP with Cooldown Protection")
def resend_otp(
    payload: ResendOtpRequest,
    request: Request,
    db: RealDictCursor = Depends(get_db)
):
    """
    Resends verification OTP with 60-second cooldown protection.
    """
    ip_addr = _get_client_ip(request)
    ua_str = request.headers.get("user-agent")
    target = payload.target or payload.email or payload.phone

    return AuthService.resend_otp(
        db=db,
        target=target,
        purpose=payload.purpose,
        turnstile_token=payload.turnstile_token,
        ip_address=ip_addr,
        user_agent=ua_str
    )


# ==============================================================================
# 3. MANDATORY 2FA ENROLLMENT & TOTP VERIFICATION
# ==============================================================================

@router.post("/2fa/setup-verify", summary="Complete Mandatory 2FA Enrollment & Issue Session")
def complete_2fa_setup(
    payload: TwoFactorSetupVerifyRequest,
    request: Request,
    db: RealDictCursor = Depends(get_db)
):
    """
    Step 3 of Signup: Verifies authenticator code against secret, activates 2FA on account,
    generates 8 one-time cryptographic recovery codes, and returns authenticated session.
    """
    ip_addr = _get_client_ip(request)
    ua_str = request.headers.get("user-agent")
    token = payload.two_factor_setup_token or payload.two_factor_token
    code = payload.totp_code or payload.code

    return AuthService.complete_2fa_setup(
        db=db,
        two_factor_token=token,
        totp_code=code,
        secret_override=payload.secret,
        ip_address=ip_addr,
        user_agent=ua_str
    )


# ==============================================================================
# 4. LOGIN & 2FA CHALLENGE
# ==============================================================================

@router.post("/login", summary="User & Lawyer Login (Returns 2FA Challenge)")
def login(
    payload: LoginRequest,
    request: Request,
    db: RealDictCursor = Depends(get_db)
):
    """
    Step 1 of Login: Verifies Turnstile CAPTCHA, checks account lockout, verifies password hash,
    and returns a short-lived 2FA challenge token. Access token is strictly held until 2FA is verified.
    """
    ip_addr = _get_client_ip(request)
    ua_str = request.headers.get("user-agent")
    identifier = payload.identifier or payload.email

    return AuthService.authenticate_credentials(
        db=db,
        email=identifier,
        password=payload.password,
        turnstile_token=payload.turnstile_token,
        ip_address=ip_addr,
        user_agent=ua_str
    )


@router.post("/2fa/verify-login", response_model=AuthUserResponse, summary="Verify 2FA Code & Establish Session")
def verify_2fa_login(
    payload: TwoFactorLoginRequest,
    request: Request,
    db: RealDictCursor = Depends(get_db)
):
    """
    Step 2 of Login: Verifies TOTP code or emergency one-time recovery code,
    runs anomaly detection for new devices/locations, logs the session, and issues full JWT token.
    """
    ip_addr = _get_client_ip(request)
    ua_str = request.headers.get("user-agent")
    code = payload.totp_code or payload.code

    session = AuthService.verify_two_factor_login(
        db=db,
        two_factor_token=payload.two_factor_token,
        totp_code=code,
        use_recovery_code=payload.use_recovery_code,
        ip_address=ip_addr,
        user_agent=ua_str
    )
    return AuthUserResponse(**session)


# ==============================================================================
# 5. GOOGLE OAUTH 2.0 / OPENID CONNECT
# ==============================================================================

@router.post("/google", summary="Authenticate with Google (Enforces Mandatory 2FA)")
async def google_login(
    payload: GoogleLoginRequest,
    request: Request,
    db: RealDictCursor = Depends(get_db)
):
    """
    Verifies real Google ID token, provisions or links user identity,
    and issues mandatory 2FA challenge. Google login never bypasses 2FA.
    """
    ip_addr = _get_client_ip(request)
    ua_str = request.headers.get("user-agent")

    return await AuthService.authenticate_google(
        db=db,
        id_token_str=payload.id_token,
        turnstile_token=payload.turnstile_token,
        ip_address=ip_addr,
        user_agent=ua_str
    )


# ==============================================================================
# 6. PASSWORD RESET WORKFLOW
# ==============================================================================

@router.post("/forgot-password", summary="Request Password Reset Link & OTP")
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: RealDictCursor = Depends(get_db)
):
    """
    Dispatches cryptographic password reset token and OTP to registered email.
    """
    ip_addr = _get_client_ip(request)
    ua_str = request.headers.get("user-agent")

    return AuthService.request_password_reset(
        db=db,
        email=payload.email,
        turnstile_token=payload.turnstile_token,
        ip_address=ip_addr,
        user_agent=ua_str
    )


@router.post("/reset-password", summary="Complete Password Reset & Invalidate Sessions")
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: RealDictCursor = Depends(get_db)
):
    """
    Completes password reset with bcrypt hashing and invalidates all existing active sessions.
    """
    ip_addr = _get_client_ip(request)
    ua_str = request.headers.get("user-agent")

    return AuthService.complete_password_reset(
        db=db,
        new_password=payload.new_password,
        confirm_password=payload.confirm_password,
        reset_token=payload.reset_token,
        email=payload.email,
        otp_code=payload.otp_code,
        ip_address=ip_addr,
        user_agent=ua_str
    )


# ==============================================================================
# 7. SESSIONS & DEVICE SECURITY
# ==============================================================================

@router.get("/sessions", summary="Get Active Sessions")
def get_active_sessions(
    authorization: Optional[str] = Header(None),
    current_user: dict = Depends(get_authenticated_user),
    db: RealDictCursor = Depends(get_db)
):
    """
    Returns list of all active sessions for current user with device, browser, approximate location, and timestamps.
    """
    current_token = authorization.split(" ")[1].strip() if (authorization and authorization.startswith("Bearer ")) else None
    sessions_data = AuthService.get_user_sessions(
        db=db,
        user_id=current_user["user_id"],
        current_token=current_token
    )
    return sessions_data["active_sessions"]


@router.post("/sessions/revoke-others", summary="Sign Out All Other Sessions")
@router.delete("/sessions/revoke-others", summary="Sign Out All Other Sessions (DELETE)")
def revoke_other_sessions(
    request: Request,
    authorization: Optional[str] = Header(None),
    current_user: dict = Depends(get_authenticated_user),
    db: RealDictCursor = Depends(get_db)
):
    """
    Signs out all active sessions across all other devices except the current session.
    """
    current_token = authorization.split(" ")[1].strip() if (authorization and authorization.startswith("Bearer ")) else ""
    ip_addr = _get_client_ip(request) if request else None
    ua_str = request.headers.get("user-agent") if request else None

    count = AuthService.revoke_all_other_sessions(
        db=db,
        user_id=current_user["user_id"],
        current_token=current_token,
        ip_address=ip_addr,
        user_agent=ua_str
    )
    return {"status": "success", "revoked_count": count, "message": f"Successfully signed out of {count} other session(s)."}


@router.post("/sessions/{session_id}/revoke", summary="Revoke a Specific Active Session")
@router.delete("/sessions/{session_id}", summary="Revoke a Specific Active Session (DELETE)")
def revoke_session(
    session_id: int,
    request: Request,
    current_user: dict = Depends(get_authenticated_user),
    db: RealDictCursor = Depends(get_db)
):
    """
    Revokes a specific session, immediately denying further API requests from that device.
    """
    ip_addr = _get_client_ip(request)
    ua_str = request.headers.get("user-agent")

    AuthService.revoke_session(
        db=db,
        user_id=current_user["user_id"],
        session_id=session_id,
        ip_address=ip_addr,
        user_agent=ua_str
    )
    return {"status": "success", "message": "Session successfully terminated."}


# ==============================================================================
# 8. SECURITY ALERTS & AUDIT
# ==============================================================================

@router.get("/security-alerts", summary="Get Account Security Incidents")
def get_security_alerts(
    current_user: dict = Depends(get_authenticated_user),
    db: RealDictCursor = Depends(get_db)
):
    """
    Returns recent security incidents and suspicious login alerts.
    """
    data = AuthService.get_security_alerts(db=db, user_id=current_user["user_id"])
    return data["alerts"]


@router.post("/security-alerts/{alert_id}/read", summary="Mark Security Alert as Read")
def mark_alert_read(
    alert_id: int,
    current_user: dict = Depends(get_authenticated_user),
    db: RealDictCursor = Depends(get_db)
):
    """
    Dismisses/marks a security incident alert as read.
    """
    AuthService.mark_alert_read(db=db, user_id=current_user["user_id"], alert_id=alert_id)
    return {"status": "success", "message": "Alert marked as read."}


# ==============================================================================
# 9. CREDENTIAL & 2FA MANAGEMENT
# ==============================================================================

@router.post("/change-password", summary="Change Password for Authenticated User")
@router.post("/password/change", summary="Change Password for Authenticated User (Alias)")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: dict = Depends(get_authenticated_user),
    db: RealDictCursor = Depends(get_db)
):
    """
    Changes password for the currently authenticated user.
    """
    ip_addr = _get_client_ip(request)
    ua_str = request.headers.get("user-agent")

    AuthService.change_password(
        db=db,
        user_id=current_user["user_id"],
        current_password=payload.current_password,
        new_password=payload.new_password,
        confirm_password=payload.confirm_password,
        ip_address=ip_addr,
        user_agent=ua_str
    )
    return {"status": "success", "message": "Password successfully updated."}


@router.post("/2fa/regenerate-recovery-codes", response_model=RegenerateRecoveryCodesResponse, summary="Regenerate 2FA Recovery Codes")
@router.post("/recovery-codes/regenerate", response_model=RegenerateRecoveryCodesResponse, summary="Regenerate 2FA Recovery Codes (Alias)")
def regenerate_recovery_codes(
    payload: RegenerateRecoveryCodesRequest,
    request: Request,
    current_user: dict = Depends(get_authenticated_user),
    db: RealDictCursor = Depends(get_db)
):
    """
    Generates 8 new one-time emergency recovery codes and invalidates all previous codes.
    Requires password or TOTP verification.
    """
    ip_addr = _get_client_ip(request)
    ua_str = request.headers.get("user-agent")

    new_codes = AuthService.regenerate_recovery_codes(
        db=db,
        user_id=current_user["user_id"],
        password=payload.password,
        totp_code=payload.totp_code,
        ip_address=ip_addr,
        user_agent=ua_str
    )
    return RegenerateRecoveryCodesResponse(
        recovery_codes=new_codes,
        message="8 new recovery codes generated. Store them in a secure place."
    )


# ==============================================================================
# 10. SESSION PROFILE & LOGOUT
# ==============================================================================

@router.get("/me", response_model=AuthUserResponse, summary="Get Current Authenticated Session Profile")
def get_me(
    current_user: dict = Depends(get_authenticated_user)
):
    """
    Returns active session metadata, user profile, and verified security state.
    """
    return AuthUserResponse(**current_user)


@router.post("/logout", summary="Revoke Active Session")
def logout(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: RealDictCursor = Depends(get_db)
):
    """
    Revokes the active user session token in memory and persistent database records.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1].strip()
        ip_addr = _get_client_ip(request) if request else None
        ua_str = request.headers.get("user-agent") if request else None
        AuthService.logout_user(token=token, db=db, ip_address=ip_addr, user_agent=ua_str)

    return {"status": "success", "message": "Successfully logged out."}
