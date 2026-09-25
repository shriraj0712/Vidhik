"""
Vidhik Platform - Administration & Security Oversight API Router
================================================================
Provides administrative oversight for user account lifecycle, status
toggling (activation/deactivation), and security audit log inspection.
Strictly guarded by `require_admin`. Never exposes password hashes or tokens.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from psycopg2.extras import RealDictCursor

from app.database import get_db
from app.schemas.auth import (
    AdminUserResponse,
    AdminUserListResponse,
    AdminUserStatusUpdateRequest,
    AuditLogListResponse
)
from app.services.auth_service import require_admin
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/admin", tags=["Administration & Security"])


@router.get("/users", response_model=AdminUserListResponse, summary="List Users (Admin)")
def list_users(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    role: Optional[str] = Query(None, description="Filter by role (user, lawyer, admin)"),
    search: Optional[str] = Query(None, description="Search by username, full name, or email"),
    admin_user: dict = Depends(require_admin),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves a paginated list of registered user accounts.
    Strictly excludes sensitive credentials (password_hash).
    """
    conditions = []
    params = []

    if role:
        conditions.append("u.role = %s")
        params.append(role.strip().lower())
    if search:
        search_param = f"%{search.strip()}%"
        conditions.append("(u.username ILIKE %s OR u.email ILIKE %s OR u.full_name ILIKE %s)")
        params.extend([search_param, search_param, search_param])

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    # Total count
    db.execute(f"SELECT COUNT(*) AS total FROM users u {where_clause};", tuple(params))
    total_row = db.fetchone()
    total = total_row["total"] if total_row else 0

    # User rows
    query = f"""
        SELECT 
            u.user_id, u.username, u.email, u.full_name, u.phone,
            u.role, u.is_active, u.is_verified, u.created_at, u.updated_at
        FROM users u
        {where_clause}
        ORDER BY u.created_at DESC
        LIMIT %s OFFSET %s;
    """
    params.extend([limit, offset])
    db.execute(query, tuple(params))
    rows = db.fetchall() or []

    return AdminUserListResponse(total=total, users=[AdminUserResponse(**r) for r in rows])


@router.get("/users/{user_id}", response_model=AdminUserResponse, summary="Get User Details (Admin)")
def get_user_detail(
    user_id: int,
    admin_user: dict = Depends(require_admin),
    db: RealDictCursor = Depends(get_db)
):
    """
    Inspects safe details of a single user account.
    """
    db.execute("""
        SELECT 
            u.user_id, u.username, u.email, u.full_name, u.phone,
            u.role, u.is_active, u.is_verified, u.created_at, u.updated_at
        FROM users u
        WHERE u.user_id = %s;
    """, (user_id,))
    row = db.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} was not found."
        )

    return AdminUserResponse(**row)


@router.put("/users/{user_id}/status", response_model=AdminUserResponse, summary="Toggle User Active Status (Admin)")
def set_user_status(
    user_id: int,
    payload: AdminUserStatusUpdateRequest,
    request: Request,
    admin_user: dict = Depends(require_admin),
    db: RealDictCursor = Depends(get_db)
):
    """
    Activates or deactivates a user account.
    Deactivating terminates any active sessions for the targeted user.
    """
    # Prevent admin from deactivating themselves
    if user_id == admin_user["user_id"] and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot deactivate their own active account."
        )

    db.execute("SELECT user_id, email, is_active FROM users WHERE user_id = %s;", (user_id,))
    existing = db.fetchone()
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} was not found."
        )

    db.execute("""
        UPDATE users 
        SET is_active = %s, updated_at = CURRENT_TIMESTAMP 
        WHERE user_id = %s
        RETURNING user_id, username, email, full_name, phone, role, is_active, is_verified, created_at, updated_at;
    """, (payload.is_active, user_id))
    updated = db.fetchone()

    # If deactivated, revoke all active sessions
    if not payload.is_active:
        try:
            db.execute("UPDATE login_sessions SET revoked_at = CURRENT_TIMESTAMP WHERE user_id = %s;", (user_id,))
        except Exception:
            pass

    if hasattr(db, "connection") and db.connection:
        db.connection.commit()

    ip = request.client.host if request.client else "127.0.0.1"
    action_name = "account_activated" if payload.is_active else "account_deactivated"
    AuditService.log_event(
        db=db,
        action=action_name,
        user_id=admin_user["user_id"],
        entity_type="user",
        entity_id=user_id,
        description=f"Admin {admin_user['email']} set is_active={payload.is_active} for user_id={user_id} ({existing['email']})",
        ip_address=ip
    )

    return AdminUserResponse(**updated)


@router.get("/audit-logs", response_model=AuditLogListResponse, summary="Inspect Audit Logs (Admin)")
def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    action: Optional[str] = Query(None, description="Filter by event action"),
    user_id: Optional[int] = Query(None, description="Filter by target user ID"),
    admin_user: dict = Depends(require_admin),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves chronological security audit events.
    """
    res = AuditService.list_logs(
        db=db,
        limit=limit,
        offset=offset,
        action=action,
        user_id=user_id
    )
    return AuditLogListResponse(**res)
