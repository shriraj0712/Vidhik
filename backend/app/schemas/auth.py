"""
Vidhik Platform - Phase 15 Authentication & Security Schemas
=============================================================
Defines Pydantic request and response models for authentication,
token refresh, password reset, password change, audit logging,
and admin user management.
"""

from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


class TokenResponse(BaseModel):
    """Token issuance response with access token, type, and expiration."""
    access_token: str
    token_type: str = "Bearer"
    expires_in_minutes: int
    refresh_token: Optional[str] = None
    role: str
    user_id: int
    email: str
    full_name: str


class RefreshTokenRequest(BaseModel):
    """Payload to refresh an access token using a valid session/refresh token."""
    refresh_token: str = Field(..., description="Active session or refresh token")


class ForgotPasswordRequest(BaseModel):
    """Payload to initiate a password reset workflow."""
    email: str = Field(..., description="Registered user email address")


class ResetPasswordRequest(BaseModel):
    """Payload to complete a password reset with a valid token."""
    reset_token: str = Field(..., description="Valid password reset token")
    new_password: str = Field(..., min_length=6, max_length=100, description="New secure password")


class ChangePasswordRequest(BaseModel):
    """Payload for authenticated users to update their password."""
    current_password: str = Field(..., min_length=1, description="Current plaintext password")
    new_password: str = Field(..., min_length=6, max_length=100, description="New secure password")


class AdminUserResponse(BaseModel):
    """Safe user profile for administrative inspection (never leaks hashes or tokens)."""
    user_id: int
    username: str
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class AdminUserListResponse(BaseModel):
    """Paginated list of users for administration."""
    total: int
    users: List[AdminUserResponse]


class AdminUserStatusUpdateRequest(BaseModel):
    """Payload for administrators to toggle user active status."""
    is_active: bool = Field(..., description="Target active status for user account")


class AuditLogResponse(BaseModel):
    """Sanitized audit log entry for security and administrative review."""
    audit_id: int
    user_id: Optional[int] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    description: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    """Paginated list of security audit logs."""
    total: int
    logs: List[AuditLogResponse]
