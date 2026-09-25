"""
Vidhik Platform - Authentication API Router
============================================
Provides secure authentication and user state endpoints for the Lawyer Workspace.
"""

from fastapi import APIRouter, Depends, HTTPException, Header, status
from psycopg2.extras import RealDictCursor
from typing import Optional

from app.database import get_db
from app.schemas.lawyer import LoginRequest, AuthUserResponse
from app.schemas.citizen import RegisterRequest
from app.services.auth_service import AuthService, get_authenticated_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=AuthUserResponse, summary="Lawyer / Citizen User Login")
def login(
    payload: LoginRequest,
    db: RealDictCursor = Depends(get_db)
):
    """
    Authenticates a user via email and password.
    Returns session metadata, assigned role, and user identification token.
    """
    session = AuthService.authenticate_user(db, payload.email, payload.password)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify credentials."
        )
    return AuthUserResponse(**session)


@router.post("/register", response_model=AuthUserResponse, status_code=status.HTTP_201_CREATED, summary="Citizen Registration")
def register(
    payload: RegisterRequest,
    db: RealDictCursor = Depends(get_db)
):
    """
    Registers a new citizen user account, initializes user profile,
    and returns authenticated session token.
    """
    session = AuthService.register_user(
        db=db,
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
        phone=payload.phone
    )
    return AuthUserResponse(**session)


@router.post("/logout", summary="Revoke Session")
def logout(
    authorization: Optional[str] = Header(None)
):
    """
    Revokes the active user session token.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1].strip()
        AuthService.logout_user(token)
    return {"status": "success", "message": "Successfully logged out."}


@router.get("/me", response_model=AuthUserResponse, summary="Get Current Session Profile")
def get_me(
    current_user: dict = Depends(get_authenticated_user)
):
    """
    Returns current authenticated user details and active session state.
    """
    return AuthUserResponse(**current_user)
