"""
Vidhik Platform - Authentication & Security API Router
======================================================
Provides secure authentication, citizen registration, JWT token refresh,
password reset, credential rotation, and session inspection endpoints.
Preserves existing frontend contract and role-guarded behavior.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from psycopg2.extras import RealDictCursor

from app.database import get_db
from app.schemas.lawyer import LoginRequest, AuthUserResponse
from app.schemas.citizen import RegisterRequest
from app.schemas.auth import (
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest
)
from app.services.auth_service import AuthService, get_authenticated_user

router = APIRouter(prefix="/api/auth", tags=["Authentication & Security"])


def _extract_request_meta(request: Request):
    """Helper to extract IP address and User-Agent from incoming request."""
    ip = request.client.host if request.client else "127.0.0.1"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    ua = request.headers.get("user-agent", "unknown")
    return ip, ua


@router.post("/login", response_model=AuthUserResponse, summary="User / Lawyer / Admin Login")
def login(
    payload: LoginRequest,
    request: Request,
    db: RealDictCursor = Depends(get_db)
):
    """
    Authenticates a user via email and password.
    Supports transparent migration from legacy SHA-256 hashes to modern bcrypt.
    Returns signed RFC 7519 JWT access token, role, and identity metadata.
    """
    ip, ua = _extract_request_meta(request)
    session = AuthService.authenticate_user(
        db=db,
        email=payload.email,
        password=payload.password,
        ip_address=ip,
        user_agent=ua
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify credentials."
        )
    return AuthUserResponse(**session)


@router.post("/register", response_model=AuthUserResponse, status_code=status.HTTP_201_CREATED, summary="Citizen Registration")
def register(
    payload: RegisterRequest,
    request: Request,
    db: RealDictCursor = Depends(get_db)
):
    """
    Registers a new citizen user account with bcrypt password hashing,
    initializes user profile, records an audit event, and returns an authenticated JWT session.
    """
    ip, ua = _extract_request_meta(request)
    session = AuthService.register_user(
        db=db,
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
        phone=payload.phone,
        ip_address=ip,
        user_agent=ua
    )
    return AuthUserResponse(**session)


@router.post("/logout", summary="Revoke Session & Access Token")
def logout(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: RealDictCursor = Depends(get_db)
):
    """
    Revokes the active user session token and records the logout in audit logs.
    """
    ip, ua = _extract_request_meta(request)
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1].strip()
        AuthService.logout_user(token=token, db=db, ip_address=ip, user_agent=ua)
    return {"status": "success", "message": "Successfully logged out and session revoked."}


@router.get("/me", response_model=AuthUserResponse, summary="Get Current Session Profile")
def get_me(
    current_user: dict = Depends(get_authenticated_user)
):
    """
    Returns current authenticated user details and active session state.
    Strictly requires valid, non-expired Bearer token.
    """
    return AuthUserResponse(**current_user)


@router.post("/refresh", response_model=AuthUserResponse, summary="Refresh JWT Access Token")
def refresh_token(
    payload: RefreshTokenRequest,
    request: Request,
    db: RealDictCursor = Depends(get_db)
):
    """
    Exchanges an active refresh token for a newly issued signed JWT access token.
    """
    ip, ua = _extract_request_meta(request)
    session = AuthService.refresh_session(
        db=db,
        refresh_token=payload.refresh_token,
        ip_address=ip,
        user_agent=ua
    )
    return AuthUserResponse(**session)


@router.post("/forgot-password", summary="Request Password Reset")
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: RealDictCursor = Depends(get_db)
):
    """
    Initiates the password reset workflow.
    Generates a secure cryptographic reset token stored in `password_resets`.
    """
    ip, ua = _extract_request_meta(request)
    return AuthService.request_password_reset(
        db=db,
        email=payload.email,
        ip_address=ip,
        user_agent=ua
    )


@router.post("/reset-password", summary="Complete Password Reset")
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: RealDictCursor = Depends(get_db)
):
    """
    Resets the account password using a valid, unexpired reset token.
    Invalidates all prior login sessions.
    """
    ip, ua = _extract_request_meta(request)
    AuthService.complete_password_reset(
        db=db,
        reset_token=payload.reset_token,
        new_password=payload.new_password,
        ip_address=ip,
        user_agent=ua
    )
    return {"status": "success", "message": "Password successfully updated. Please log in with your new password."}


@router.post("/change-password", summary="Change Password (Authenticated)")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: dict = Depends(get_authenticated_user),
    db: RealDictCursor = Depends(get_db)
):
    """
    Allows an authenticated user to update their password.
    Requires verification of the current password before applying bcrypt hash.
    """
    ip, ua = _extract_request_meta(request)
    AuthService.change_password(
        db=db,
        user_id=current_user["user_id"],
        current_password=payload.current_password,
        new_password=payload.new_password,
        ip_address=ip,
        user_agent=ua
    )
    return {"status": "success", "message": "Password changed successfully."}
