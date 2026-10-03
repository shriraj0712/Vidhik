"""
Vidhik Platform - Citizen / User Module API Router
===================================================
Exposes RESTful endpoints for the Citizen Portal:
- Personal Dashboard KPI Aggregations & Activity Feed
- Citizen Case Management & Status Tracking
- Document Uploads & Case Attachments
- Court Hearing Schedule Monitoring
- User Profile & Contact Information
- Statutory Section Bookmarking
- Research Search History
- User Notifications & Alert State
- Persistent Procedure Checklists & Tracking
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg2.extras import RealDictCursor

from app.database import get_db
from app.services.auth_service import require_citizen
from app.services.citizen_service import CitizenService
from app.schemas.citizen import (
    CitizenDashboardMetrics,
    CitizenProfileResponse,
    CitizenProfileUpdate,
    CitizenCaseResponse,
    CitizenCaseDetailResponse,
    CitizenCaseCreate,
    CitizenDocumentResponse,
    CitizenDocumentUpload,
    BookmarkCreate,
    BookmarkResponse,
    BookmarkListResponse,
    SearchHistoryCreate,
    SearchHistoryResponse,
    NotificationResponse,
    NotificationListResponse,
    ProcedureTrackerResponse,
    ProcedureTrackerToggle
)

router = APIRouter(prefix="/api/citizen", tags=["Citizen Module"])


# -------------------------------------------------------------
# 1. CITIZEN DASHBOARD
# -------------------------------------------------------------
@router.get("/dashboard", response_model=CitizenDashboardMetrics, summary="Citizen Personal Dashboard")
def get_dashboard(
    current_citizen: dict = Depends(require_citizen),
    db: RealDictCursor = Depends(get_db)
):
    """
    Returns personal dashboard statistics for the authenticated citizen:
    - Active cases & total matters
    - Document counts & upcoming court hearings
    - Unread notification counts
    - Saved legal sections & recent document analyses
    - Recent matters & hearing schedule
    """
    user_id = current_citizen["user_id"]
    return CitizenService.get_dashboard_metrics(db, user_id)


# -------------------------------------------------------------
# 2. CITIZEN CASES
# -------------------------------------------------------------
@router.get("/cases", response_model=List[CitizenCaseResponse], summary="List Citizen Cases")
def list_cases(
    search: Optional[str] = Query(None, description="Search case title, case number, or court"),
    status: Optional[str] = Query(None, description="Filter by status (active, pending, resolved, closed)"),
    current_citizen: dict = Depends(require_citizen),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves all legal cases belonging to the authenticated citizen.
    Strictly isolated: returns only records where cases.user_id = current_user.
    """
    user_id = current_citizen["user_id"]
    return CitizenService.list_cases(db, user_id, search, status)


@router.get("/cases/{case_id}", response_model=CitizenCaseDetailResponse, summary="Get Case Details")
def get_case_detail(
    case_id: int,
    current_citizen: dict = Depends(require_citizen),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves complete case details for the citizen:
    - Overview, court, opposite party
    - Assigned lawyer contact info
    - Attached documents & upcoming hearings
    - Procedural timeline updates
    - Linked statutory sections
    Confidential lawyer notes are strictly excluded.
    """
    user_id = current_citizen["user_id"]
    case = CitizenService.get_case_detail(db, user_id, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID {case_id} not found or unauthorized."
        )
    return case


@router.post("/cases", response_model=CitizenCaseResponse, status_code=status.HTTP_201_CREATED, summary="Register New Case")
def create_case(
    payload: CitizenCaseCreate,
    current_citizen: dict = Depends(require_citizen),
    db: RealDictCursor = Depends(get_db)
):
    """
    Allows a citizen to record or register a new legal matter into the platform.
    """
    user_id = current_citizen["user_id"]
    return CitizenService.create_case(db, user_id, payload)


# -------------------------------------------------------------
# 3. CITIZEN DOCUMENTS
# -------------------------------------------------------------
@router.get("/documents", response_model=List[CitizenDocumentResponse], summary="List Citizen Documents")
def list_documents(
    case_id: Optional[int] = Query(None, description="Optional case ID filter"),
    current_citizen: dict = Depends(require_citizen),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves documents uploaded by or belonging to the authenticated citizen.
    """
    user_id = current_citizen["user_id"]
    return CitizenService.list_documents(db, user_id, case_id)


@router.post("/documents", response_model=CitizenDocumentResponse, status_code=status.HTTP_201_CREATED, summary="Upload Case Document")
def upload_document(
    payload: CitizenDocumentUpload,
    current_citizen: dict = Depends(require_citizen),
    db: RealDictCursor = Depends(get_db)
):
    """
    Attaches a document to an active case owned by the citizen.
    """
    user_id = current_citizen["user_id"]
    return CitizenService.upload_document(db, user_id, payload)


# -------------------------------------------------------------
# 4. CITIZEN HEARINGS
# -------------------------------------------------------------
@router.get("/hearings", summary="List Scheduled Hearings")
def list_hearings(
    current_citizen: dict = Depends(require_citizen),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves court hearing dates, times, and courtroom details for the citizen.
    """
    user_id = current_citizen["user_id"]
    return CitizenService.list_hearings(db, user_id)


# -------------------------------------------------------------
# 5. CITIZEN PROFILE
# -------------------------------------------------------------
@router.get("/profile", response_model=CitizenProfileResponse, summary="Get Citizen Profile")
def get_profile(
    current_citizen: dict = Depends(require_citizen),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves authenticated citizen user credentials and personal profile.
    """
    user_id = current_citizen["user_id"]
    return CitizenService.get_profile(db, user_id)


@router.put("/profile", response_model=CitizenProfileResponse, summary="Update Citizen Profile")
def update_profile(
    payload: CitizenProfileUpdate,
    current_citizen: dict = Depends(require_citizen),
    db: RealDictCursor = Depends(get_db)
):
    """
    Updates address, city, state, pincode, phone, and preferred language.
    """
    user_id = current_citizen["user_id"]
    return CitizenService.update_profile(db, user_id, payload)


# -------------------------------------------------------------
# 6. BOOKMARKS (SAVED SECTIONS)
# -------------------------------------------------------------
@router.get("/bookmarks", response_model=List[BookmarkResponse], summary="List Bookmarked Sections")
def list_bookmarks(
    current_citizen: dict = Depends(require_citizen),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves all statutory provisions saved by the authenticated citizen.
    """
    user_id = current_citizen["user_id"]
    return CitizenService.list_bookmarks(db, user_id)


@router.post("/bookmarks", response_model=BookmarkResponse, status_code=status.HTTP_201_CREATED, summary="Bookmark Statutory Section")
def create_bookmark(
    payload: BookmarkCreate,
    current_citizen: dict = Depends(require_citizen),
    db: RealDictCursor = Depends(get_db)
):
    """
    Saves a statutory section from the Vidhik legal database to personal bookmarks.
    """
    user_id = current_citizen["user_id"]
    return CitizenService.create_bookmark(db, user_id, payload)


@router.delete("/bookmarks/{section_id}", summary="Remove Bookmark")
def delete_bookmark(
    section_id: int,
    current_citizen: dict = Depends(require_citizen),
    db: RealDictCursor = Depends(get_db)
):
    """
    Removes a bookmarked section from the citizen profile.
    """
    user_id = current_citizen["user_id"]
    deleted = CitizenService.delete_bookmark(db, user_id, section_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found."
        )
    return {"status": "success", "message": "Bookmark removed successfully."}


# -------------------------------------------------------------
# 7. SEARCH HISTORY
# -------------------------------------------------------------
@router.get("/search-history", response_model=List[SearchHistoryResponse], summary="Get Legal Search History")
def get_search_history(
    limit: int = Query(default=20, ge=1, le=50),
    current_citizen: dict = Depends(require_citizen),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves recent legal searches performed by the authenticated citizen.
    """
    user_id = current_citizen["user_id"]
    return CitizenService.list_search_history(db, user_id, limit)


@router.post("/search-history", response_model=SearchHistoryResponse, status_code=status.HTTP_201_CREATED, summary="Record Search Query")
def record_search(
    payload: SearchHistoryCreate,
    current_citizen: dict = Depends(require_citizen),
    db: RealDictCursor = Depends(get_db)
):
    """
    Records a research search query for the citizen.
    """
    user_id = current_citizen["user_id"]
    return CitizenService.record_search(
        db, user_id, payload.query_text, payload.filters, payload.results_count or 0
    )


@router.delete("/search-history", summary="Clear Search History")
def clear_search_history(
    current_citizen: dict = Depends(require_citizen),
    db: RealDictCursor = Depends(get_db)
):
    """
    Clears all search history records for the citizen.
    """
    user_id = current_citizen["user_id"]
    CitizenService.clear_search_history(db, user_id)
    return {"status": "success", "message": "Search history cleared."}


# -------------------------------------------------------------
# 8. NOTIFICATIONS
# -------------------------------------------------------------
@router.get("/notifications", response_model=NotificationListResponse, summary="List Notifications")
def list_notifications(
    current_citizen: dict = Depends(require_citizen),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves all notifications and alerts for the authenticated citizen.
    """
    user_id = current_citizen["user_id"]
    return CitizenService.list_notifications(db, user_id)


@router.patch("/notifications/{notification_id}/read", response_model=NotificationResponse, summary="Mark Notification as Read")
def mark_read(
    notification_id: int,
    current_citizen: dict = Depends(require_citizen),
    db: RealDictCursor = Depends(get_db)
):
    """
    Marks an individual notification as read.
    """
    user_id = current_citizen["user_id"]
    return CitizenService.mark_notification_read(db, user_id, notification_id)


@router.post("/notifications/read-all", summary="Mark All Notifications as Read")
def mark_all_read(
    current_citizen: dict = Depends(require_citizen),
    db: RealDictCursor = Depends(get_db)
):
    """
    Marks all notifications as read for the authenticated citizen.
    """
    user_id = current_citizen["user_id"]
    count = CitizenService.mark_all_read(db, user_id)
    return {"status": "success", "marked_read_count": count}


# -------------------------------------------------------------
# 9. PROCEDURE TRACKERS & CHECKLISTS
# -------------------------------------------------------------
@router.get("/procedures", response_model=List[ProcedureTrackerResponse], summary="List Tracked Procedures")
def list_procedures(
    current_citizen: dict = Depends(require_citizen),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves procedure checklist progress and document readiness states.
    """
    user_id = current_citizen["user_id"]
    return CitizenService.list_procedures(db, user_id)


@router.post("/procedures/{procedure_id}/toggle-doc", response_model=ProcedureTrackerResponse, summary="Toggle Checklist Document")
def toggle_procedure_doc(
    procedure_id: int,
    payload: ProcedureTrackerToggle,
    current_citizen: dict = Depends(require_citizen),
    db: RealDictCursor = Depends(get_db)
):
    """
    Persists document check state for an authoritative procedure checklist.
    """
    user_id = current_citizen["user_id"]
    return CitizenService.toggle_procedure_doc(
        db, user_id, procedure_id, payload.document_name, payload.completed
    )
