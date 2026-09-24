"""
Vidhik Platform - Authentication API Router
============================================
Provides secure authentication and user state endpoints for the Lawyer Workspace.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from psycopg2.extras import RealDictCursor

from app.database import get_db
from app.schemas.lawyer import LoginRequest, AuthUserResponse
from app.services.auth_service import AuthService, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=AuthUserResponse, summary="Lawyer / User Login")
def login(
    payload: LoginRequest,
    db: RealDictCursor = Depends(get_db)
):
    """
    Authenticates a user via email and password.
    Returns session metadata, assigned role, and lawyer identification token.
    """
    session = AuthService.authenticate_user(db, payload.email, payload.password)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify credentials."
        )
    return AuthUserResponse(**session)


@router.get("/me", response_model=AuthUserResponse, summary="Get Current Session Profile")
def get_me(
    current_user: dict = Depends(get_current_user)
):
    """
    Returns current authenticated user details and active session state.
    """
    return AuthUserResponse(**current_user)
