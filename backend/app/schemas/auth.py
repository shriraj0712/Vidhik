"""
Vidhik Platform - Authentication & Security Pydantic Schemas
============================================================
Pydantic v2 schemas for enterprise authentication:
- Registration & CAPTCHA verification
- OTP lifecycle (email & SMS)
- Mandatory RFC 6238 TOTP 2FA enrollment & challenge
- One-time recovery codes
- Google OAuth 2.0 / OIDC identity
- Active sessions & device monitoring
- Real-time security incident alerts
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, field_validator


# ==============================================================================
# 1. REGISTRATION & ONBOARDING SCHEMAS
# ==============================================================================

class RegisterInitiateRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=200, description="Full Name")
    email: str = Field(..., min_length=5, max_length=150, description="Valid Email Address")
    phone: Optional[str] = Field(None, max_length=20, description="Mobile Phone Number")
    password: str = Field(..., min_length=8, max_length=128, description="Strong Password (min 8 chars)")
    confirm_password: Optional[str] = Field(None, max_length=128, description="Password Confirmation")
    turnstile_token: Optional[str] = Field(None, description="Cloudflare Turnstile token")

    @field_validator("email")
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("full_name")
    def clean_name(cls, v: str) -> str:
        return v.strip()


class VerifyOtpRequest(BaseModel):
    target: Optional[str] = Field(None, description="Email or phone number receiving OTP")
    email: Optional[str] = Field(None, description="Email receiving OTP")
    phone: Optional[str] = Field(None, description="Phone receiving OTP")
    otp_code: str = Field(..., min_length=4, max_length=8, description="6-digit numeric OTP code")
    purpose: str = Field("signup_verification", description="OTP purpose (signup_verification, password_reset, email_verification)")


class ResendOtpRequest(BaseModel):
    target: Optional[str] = Field(None, description="Email or phone destination")
    email: Optional[str] = Field(None, description="Email receiving OTP")
    phone: Optional[str] = Field(None, description="Phone receiving OTP")
    purpose: str = Field("signup_verification", description="Verification purpose")
    turnstile_token: Optional[str] = Field(None, description="Cloudflare Turnstile token")


# ==============================================================================
# 2. LOGIN & CREDENTIAL VERIFICATION SCHEMAS
# ==============================================================================

class LoginRequest(BaseModel):
    email: Optional[str] = Field(None, description="User or Lawyer email")
    identifier: Optional[str] = Field(None, description="Email or mobile identifier")
    password: str = Field(..., min_length=1, description="Password")
    turnstile_token: Optional[str] = Field(None, description="Cloudflare Turnstile token")


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(..., description="Google OAuth 2.0 / OIDC Identity JWT")
    turnstile_token: Optional[str] = Field(None, description="Cloudflare Turnstile token")


# ==============================================================================
# 3. MANDATORY 2FA & RECOVERY SCHEMAS
# ==============================================================================

class TwoFactorSetupInitiateResponse(BaseModel):
    status: str = "2fa_enrollment_required"
    two_factor_token: str
    qr_uri: str
    qr_code_data_url: str
    totp_secret: str
    instructions: str = "Scan this QR code with Google Authenticator, Authy, or Microsoft Authenticator."


class TwoFactorSetupVerifyRequest(BaseModel):
    two_factor_setup_token: Optional[str] = Field(None, description="Short-lived 2FA setup enrollment token")
    two_factor_token: Optional[str] = Field(None, description="Alias for setup token")
    totp_code: Optional[str] = Field(None, max_length=10, description="6-digit TOTP code from authenticator app")
    code: Optional[str] = Field(None, max_length=10, description="Alias for code")
    secret: Optional[str] = Field(None, description="Base32 TOTP secret if passing back")


class TwoFactorLoginRequest(BaseModel):
    two_factor_token: str = Field(..., description="Short-lived 2FA challenge token")
    totp_code: Optional[str] = Field(None, max_length=20, description="6-digit TOTP code or recovery code")
    code: Optional[str] = Field(None, max_length=20, description="Alias for code")
    use_recovery_code: bool = Field(False, description="True if code is a one-time recovery code")


class RegenerateRecoveryCodesRequest(BaseModel):
    password: Optional[str] = Field(None, description="Current password for authorization")
    totp_code: Optional[str] = Field(None, description="Current TOTP code for authorization")


class RegenerateRecoveryCodesResponse(BaseModel):
    status: str = "success"
    recovery_codes: List[str]
    message: str = "Store these recovery codes in a secure location. Each code can be used exactly once."


# ==============================================================================
# 4. PASSWORD MANAGEMENT SCHEMAS
# ==============================================================================

class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., description="Registered email address")
    turnstile_token: Optional[str] = Field(None, description="Cloudflare Turnstile token")


class ResetPasswordRequest(BaseModel):
    reset_token: Optional[str] = Field(None, description="Cryptographic reset token from link")
    email: Optional[str] = Field(None, description="Email if resetting via OTP")
    otp_code: Optional[str] = Field(None, description="6-digit OTP if resetting via OTP")
    new_password: str = Field(..., min_length=8, max_length=128, description="New strong password")
    confirm_password: Optional[str] = Field(None, max_length=128, description="Confirmation of new password")


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="Current plaintext password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New strong password")
    confirm_password: Optional[str] = Field(None, max_length=128, description="Confirm new password")


# ==============================================================================
# 5. RESPONSE & SESSION MODELS
# ==============================================================================

class AuthUserResponse(BaseModel):
    user_id: int
    username: str
    email: str
    full_name: str
    phone: Optional[str] = None
    role: str
    lawyer_id: Optional[int] = None
    token: str
    access_token: Optional[str] = None
    token_type: Optional[str] = "bearer"
    refresh_token: Optional[str] = None
    is_active: bool = True
    email_verified: bool = True
    phone_verified: bool = False
    two_factor_enabled: bool = True
    account_status: str = "active"


class LoginChallengeResponse(BaseModel):
    status: str = "2fa_required"
    two_factor_token: str
    message: str = "Two-Factor Authentication required. Enter code from your authenticator app."


class SessionItemResponse(BaseModel):
    session_id: int
    device: Optional[str] = "Desktop"
    browser: Optional[str] = "Browser"
    os: Optional[str] = "Windows"
    ip_address: Optional[str] = "127.0.0.1"
    location: Optional[str] = "Pune, Maharashtra, India"
    login_method: str = "password"
    created_at: datetime
    expires_at: datetime
    is_current: bool = False


class SessionListResponse(BaseModel):
    current_session: Optional[SessionItemResponse] = None
    active_sessions: List[SessionItemResponse] = []
    total_sessions: int = 0


class SecurityAlertItem(BaseModel):
    alert_id: int
    title: str
    alert_type: str
    severity: str
    description: str
    device: Optional[str] = None
    browser: Optional[str] = None
    ip_address: Optional[str] = None
    location: Optional[str] = None
    is_read: bool = False
    created_at: datetime


class SecurityAlertListResponse(BaseModel):
    alerts: List[SecurityAlertItem] = []
    unread_count: int = 0


class TurnstileConfigResponse(BaseModel):
    site_key: str
    enabled: bool = True


class GoogleConfigResponse(BaseModel):
    client_id: str
    enabled: bool = True
