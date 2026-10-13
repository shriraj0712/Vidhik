"""
Vidhik Platform - Lawyer Module API Router
===========================================
Exposes RESTful endpoints for the complete Lawyer Workspace:
- Dashboard KPI Aggregations & Activity
- Client Roster & Client Detail Management
- Case Lifecycle & Multi-Section Case Details
- Case-specific Legal Research Linking (case_legal_sections)
- Document Uploads & File Management
- Hearing Calendar & Status Updates
- Case-specific Legal Notes Management
- Professional Lawyer Profile & Credentials
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg2.extras import RealDictCursor

from app.database import get_db
from app.services.auth_service import require_lawyer
from app.services.lawyer_service import LawyerService
from app.schemas.lawyer import (
    DashboardMetricsResponse,
    ClientCreate, ClientUpdate, ClientResponse, ClientListResponse,
    CaseCreate, CaseUpdate, CaseSummaryResponse, CaseDetailResponse, CaseListResponse,
    HearingCreate, HearingUpdate, HearingResponse, HearingListResponse,
    DocumentCreate, DocumentResponse, DocumentListResponse,
    NoteCreate, NoteUpdate, NoteResponse,
    LawyerProfileResponse, LawyerProfileUpdate,
    CaseSectionLinkRequest, CaseSectionLinkResponse,
    CaseCourtReferenceUpdate
)

router = APIRouter(prefix="/api/lawyer", tags=["Lawyer Module"])


# -------------------------------------------------------------
# 1. LAWYER DASHBOARD
# -------------------------------------------------------------
@router.get("/dashboard", response_model=DashboardMetricsResponse, summary="Lawyer Dashboard Overview")
def get_dashboard(
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Returns high-level statistics for the authenticated lawyer:
    - Total clients
    - Active cases
    - Upcoming hearings
    - Recent documents & activity feed
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    return LawyerService.get_dashboard_metrics(db, lawyer_id)


# -------------------------------------------------------------
# 2. CLIENT MANAGEMENT
# -------------------------------------------------------------
@router.get("/clients", response_model=ClientListResponse, summary="List Clients")
def get_clients(
    search: Optional[str] = Query(None, description="Search client name, email, or phone"),
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves a list of clients associated with the lawyer.
    Filterable by name, email, or phone.
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    return LawyerService.list_clients(db, lawyer_id, search)


@router.post("/clients", response_model=ClientResponse, summary="Add New Client")
def create_client(
    payload: ClientCreate,
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Registers a new client profile into the platform.
    """
    return LawyerService.create_client(db, payload)


@router.get("/clients/{client_id}", response_model=ClientResponse, summary="Get Client Details")
def get_client_details(
    client_id: int,
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves full details for a client, including all associated cases.
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    client = LawyerService.get_client(db, client_id, lawyer_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with ID {client_id} not found."
        )
    return client


@router.put("/clients/{client_id}", response_model=ClientResponse, summary="Update Client Profile")
def update_client_profile(
    client_id: int,
    payload: ClientUpdate,
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Updates client contact and personal information.
    """
    client = LawyerService.update_client(db, client_id, payload)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with ID {client_id} not found or no changes supplied."
        )
    return client


# -------------------------------------------------------------
# 3. CASE MANAGEMENT
# -------------------------------------------------------------
@router.get("/cases", response_model=CaseListResponse, summary="List Cases")
def get_cases(
    search: Optional[str] = Query(None, description="Search case title, case number, or court"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (active, pending, resolved, closed)"),
    case_type: Optional[str] = Query(None, description="Filter by case type"),
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves a list of cases assigned to the lawyer.
    Filterable by status, case type, and search keyword.
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    return LawyerService.list_cases(db, lawyer_id, search, status_filter, case_type)


@router.post("/cases", response_model=CaseSummaryResponse, summary="Create New Case")
def create_case(
    payload: CaseCreate,
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Creates and registers a new case associated with a client and the authenticated lawyer.
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    return LawyerService.create_case(db, lawyer_id, payload)


@router.get("/cases/{case_id}", response_model=CaseDetailResponse, summary="Get Case Details Workspace")
def get_case_detail(
    case_id: int,
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves complete workspace details for a case:
    - Overview, Client Info, Court & Opposite Party
    - Documents
    - Scheduled Hearings
    - Case Notes
    - Linked Statutory Sections
    - Activity Updates
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    case = LawyerService.get_case_detail(db, case_id, lawyer_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID {case_id} not found or not assigned to you."
        )
    return case


@router.put("/cases/{case_id}", response_model=CaseDetailResponse, summary="Update Case Details")
def update_case(
    case_id: int,
    payload: CaseUpdate,
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Updates case parameters (status, court, opposite party, case number, etc.).
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    case = LawyerService.update_case(db, case_id, lawyer_id, payload)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID {case_id} not found or update failed."
        )
    return case


@router.patch("/cases/{case_id}/court-reference", response_model=CaseDetailResponse, summary="Update Official Court Reference")
def update_court_reference(
    case_id: int,
    payload: CaseCourtReferenceUpdate,
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Updates or records user-verified official eCourts reference information for a case.
    Does not scrape eCourts; saves manually verified reference data (CNR, stage, hearing date).
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    case = LawyerService.update_court_reference(db, case_id, lawyer_id, payload)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID {case_id} not found or not assigned to you."
        )
    return case


# -------------------------------------------------------------
# 4. LEGAL RESEARCH SECTION ASSOCIATION
# -------------------------------------------------------------
@router.post("/cases/{case_id}/sections", response_model=CaseSectionLinkResponse, summary="Link Legal Section to Case")
def link_section_to_case(
    case_id: int,
    payload: CaseSectionLinkRequest,
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Associates a statutory provision discovered in Legal Research directly
    with the given case in the `case_legal_sections` database table.
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    try:
        return LawyerService.link_section_to_case(db, case_id, lawyer_id, payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/cases/{case_id}/sections/{section_id}", summary="Unlink Legal Section from Case")
def unlink_section_from_case(
    case_id: int,
    section_id: int,
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Removes a statutory section association from the case.
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    success = LawyerService.unlink_section_from_case(db, case_id, section_id, lawyer_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section not linked to this case or case not found."
        )
    return {"status": "success", "message": "Section unlinked successfully"}


# -------------------------------------------------------------
# 5. DOCUMENT MANAGEMENT
# -------------------------------------------------------------
@router.get("/documents", response_model=DocumentListResponse, summary="List Case Documents")
def get_documents(
    case_id: Optional[int] = Query(None, description="Optional case ID filter"),
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves all documents associated with the lawyer's cases.
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    return LawyerService.list_documents(db, lawyer_id, case_id)


@router.post("/documents", response_model=DocumentResponse, summary="Catalog & Upload Document")
def create_document(
    payload: DocumentCreate,
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Registers a new document associated with a case and client.
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    return LawyerService.create_document(db, lawyer_id, payload)


@router.delete("/documents/{document_id}", summary="Delete Document")
def delete_document(
    document_id: int,
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Removes a document record from the platform.
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    if not LawyerService.delete_document(db, document_id, lawyer_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found."
        )
    return {"status": "success", "message": "Document deleted successfully"}


# -------------------------------------------------------------
# 6. HEARING MANAGEMENT
# -------------------------------------------------------------
@router.get("/hearings", response_model=HearingListResponse, summary="List Scheduled & Past Hearings")
def get_hearings(
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves upcoming and previous court hearings for the lawyer.
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    return LawyerService.list_hearings(db, lawyer_id)


@router.post("/hearings", response_model=HearingResponse, summary="Schedule Court Hearing")
def schedule_hearing(
    payload: HearingCreate,
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Schedules a new court hearing for a case.
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    return LawyerService.create_hearing(db, lawyer_id, payload)


@router.put("/hearings/{hearing_id}", response_model=HearingResponse, summary="Update Hearing Details")
def update_hearing(
    hearing_id: int,
    payload: HearingUpdate,
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Updates hearing date, time, court, judge, priority, or status.
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    updated = LawyerService.update_hearing(db, hearing_id, lawyer_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hearing with ID {hearing_id} not found."
        )
    return updated


# -------------------------------------------------------------
# 7. CASE NOTES
# -------------------------------------------------------------
@router.get("/cases/{case_id}/notes", response_model=List[NoteResponse], summary="List Case Notes")
def get_notes(
    case_id: int,
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves all notes associated with a case. Pinned notes appear first.
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    return LawyerService.list_notes(db, case_id, lawyer_id)


@router.post("/cases/{case_id}/notes", response_model=NoteResponse, summary="Add Case Note")
def add_note(
    case_id: int,
    payload: NoteCreate,
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Adds a confidential legal note to a case.
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    payload.case_id = case_id
    return LawyerService.create_note(db, lawyer_id, payload)


@router.put("/notes/{note_id}", response_model=NoteResponse, summary="Edit Case Note")
def edit_note(
    note_id: int,
    payload: NoteUpdate,
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Modifies title, content, or pin status of a note.
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    updated = LawyerService.update_note(db, note_id, lawyer_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found."
        )
    return updated


@router.delete("/notes/{note_id}", summary="Delete Case Note")
def delete_note(
    note_id: int,
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Permanently deletes a case note.
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    if not LawyerService.delete_note(db, note_id, lawyer_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found."
        )
    return {"status": "success", "message": "Note deleted successfully"}


# -------------------------------------------------------------
# 8. LAWYER PROFILE
# -------------------------------------------------------------
@router.get("/profile", response_model=LawyerProfileResponse, summary="Get Lawyer Profile")
def get_lawyer_profile(
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves the authenticated lawyer's verified credentials and practice details.
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    profile = LawyerService.get_profile(db, lawyer_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lawyer profile not found."
        )
    return profile


@router.put("/profile", response_model=LawyerProfileResponse, summary="Update Lawyer Profile")
def update_lawyer_profile(
    payload: LawyerProfileUpdate,
    current_lawyer: dict = Depends(require_lawyer),
    db: RealDictCursor = Depends(get_db)
):
    """
    Updates lawyer practice details, Bar Council registration, and specializations.
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    updated = LawyerService.update_profile(db, lawyer_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lawyer profile not found or update failed."
        )
    return updated


# -------------------------------------------------------------
# 9. PUBLIC LAWYER DIRECTORY
# -------------------------------------------------------------
@router.get("/directory", summary="Browse Verified Lawyer Directory")
def get_lawyer_directory(
    specialization: Optional[str] = Query(None, description="Filter by legal specialization"),
    city: Optional[str] = Query(None, description="Filter by city"),
    q: Optional[str] = Query(None, description="Search lawyer name or practice area"),
    limit: int = Query(20, ge=1, le=50, description="Max lawyers to return"),
    db: RealDictCursor = Depends(get_db)
):
    """
    Publicly browsable directory of verified advocates in Maharashtra and India.
    Accessible to citizens, litigants, and fellow legal practitioners.
    """
    return LawyerService.list_directory(
        db=db,
        specialization=specialization,
        city=city,
        search=q,
        limit=limit
    )
