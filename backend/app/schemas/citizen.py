"""
Vidhik Platform - Citizen / User Module Pydantic Schemas
=========================================================
Pydantic v2 schemas for the Citizen Workspace:
- User Registration & Authentication
- Citizen Profile & Contact Details
- Citizen Personal Dashboard KPIs
- Citizen Cases & Case Details
- Citizen Documents & Uploads
- Bookmarked Statutory Sections
- Legal Search History
- Citizen Notifications
- Persistent Procedure Trackers & Checklists
"""

from typing import Optional, List, Any, Dict
from datetime import datetime, date, time
from pydantic import BaseModel, Field, EmailStr


# -------------------------------------------------------------
# 1. AUTHENTICATION & REGISTRATION
# -------------------------------------------------------------

class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=200, description="Full Name of citizen")
    email: str = Field(..., min_length=5, max_length=150, description="Valid email address")
    password: str = Field(..., min_length=6, max_length=100, description="Password (min 6 characters)")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")


# -------------------------------------------------------------
# 2. CITIZEN PROFILE SCHEMAS
# -------------------------------------------------------------

class CitizenProfileResponse(BaseModel):
    user_id: int
    username: str
    email: str
    full_name: str
    phone: Optional[str] = None
    role: str = "user"
    date_of_birth: Optional[date] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    preferred_language: str = "en"
    profile_image_url: Optional[str] = None
    occupation: Optional[str] = None
    emergency_contact: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class CitizenProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[date] = None
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    pincode: Optional[str] = Field(None, max_length=10)
    preferred_language: Optional[str] = Field(None, max_length=50)
    occupation: Optional[str] = Field(None, max_length=150)
    emergency_contact: Optional[str] = Field(None, max_length=100)


# -------------------------------------------------------------
# 3. CITIZEN DASHBOARD SCHEMAS
# -------------------------------------------------------------

class CitizenDashboardMetrics(BaseModel):
    active_cases: int
    total_cases: int
    documents_count: int
    upcoming_hearings_count: int
    unread_notifications_count: int
    recent_analyses_count: int
    saved_sections_count: int
    tracked_procedures_count: int
    metrics: Optional[Dict[str, Any]] = None
    recent_cases: List[Dict[str, Any]] = []
    upcoming_hearings: List[Dict[str, Any]] = []
    recent_documents: List[Dict[str, Any]] = []
    recent_analyses: List[Dict[str, Any]] = []
    recent_notifications: List[Dict[str, Any]] = []
    notifications: List[Dict[str, Any]] = []


# -------------------------------------------------------------
# 4. CITIZEN CASE SCHEMAS
# -------------------------------------------------------------

class CitizenCaseResponse(BaseModel):
    case_id: int
    case_title: str
    title: Optional[str] = None
    case_number: Optional[str] = None
    case_type: Optional[str] = None
    court_name: Optional[str] = None
    court: Optional[str] = None
    opposite_party: Optional[str] = None
    status: str
    filing_date: Optional[date] = None
    incident_date: Optional[date] = None
    location: Optional[str] = None
    police_station: Optional[str] = None
    case_description: Optional[str] = None
    description: Optional[str] = None
    assigned_lawyer_id: Optional[int] = None
    assigned_lawyer_name: Optional[str] = None
    lawyer_name: Optional[str] = None
    assigned_lawyer_phone: Optional[str] = None
    assigned_lawyer_email: Optional[str] = None
    documents_count: int = 0
    hearings_count: int = 0
    created_at: datetime
    updated_at: datetime


class CitizenCaseDetailResponse(BaseModel):
    case_id: int
    case_title: str
    title: Optional[str] = None
    case_number: Optional[str] = None
    case_type: Optional[str] = None
    court_name: Optional[str] = None
    court: Optional[str] = None
    opposite_party: Optional[str] = None
    status: str
    filing_date: Optional[date] = None
    incident_date: Optional[date] = None
    location: Optional[str] = None
    police_station: Optional[str] = None
    case_description: Optional[str] = None
    description: Optional[str] = None
    assigned_lawyer_id: Optional[int] = None
    assigned_lawyer_name: Optional[str] = None
    lawyer_name: Optional[str] = None
    assigned_lawyer_phone: Optional[str] = None
    assigned_lawyer_email: Optional[str] = None
    assigned_lawyer_specialization: Optional[str] = None
    lawyer: Optional[Dict[str, Any]] = None
    documents: List[Dict[str, Any]] = []
    hearings: List[Dict[str, Any]] = []
    updates: List[Dict[str, Any]] = []
    legal_sections: List[Dict[str, Any]] = []
    created_at: datetime
    updated_at: datetime


class CitizenCaseCreate(BaseModel):
    case_title: Optional[str] = Field(None, max_length=300)
    title: Optional[str] = Field(None, max_length=300)
    case_type: Optional[str] = Field(None, max_length=100)
    court_name: Optional[str] = Field(None, max_length=300)
    court: Optional[str] = Field(None, max_length=300)
    opposite_party: Optional[str] = Field(None, max_length=250)
    case_description: Optional[str] = None
    description: Optional[str] = None
    incident_date: Optional[date] = None
    location: Optional[str] = Field(None, max_length=300)
    police_station: Optional[str] = Field(None, max_length=300)


# -------------------------------------------------------------
# 5. CITIZEN DOCUMENT SCHEMAS
# -------------------------------------------------------------

class CitizenDocumentResponse(BaseModel):
    document_id: int
    case_id: int
    case_title: Optional[str] = None
    document_name: str
    document_type: str
    file_path: str
    file_size_bytes: int
    mime_type: str
    upload_status: str
    description: Optional[str] = None
    created_at: datetime


class CitizenDocumentUpload(BaseModel):
    case_id: int
    document_name: str = Field(..., min_length=2, max_length=300)
    document_type: str = Field("General", max_length=100)
    description: Optional[str] = None
    file_size_bytes: Optional[int] = 0
    mime_type: Optional[str] = "application/pdf"
    file_path: Optional[str] = None


# -------------------------------------------------------------
# 6. BOOKMARKS (SAVED SECTIONS) SCHEMAS
# -------------------------------------------------------------

class BookmarkCreate(BaseModel):
    section_id: int = Field(..., description="Section ID from Vidhik legal database")
    notes: Optional[str] = Field(None, description="Personal citizen research note")
    tag: Optional[str] = Field("General", max_length=100, description="Custom label/folder tag")


class BookmarkResponse(BaseModel):
    bookmark_id: int
    user_id: int
    section_id: int
    section_number: str
    section_title: str
    law_id: int
    law_name: str
    notes: Optional[str] = None
    tag: str = "General"
    created_at: datetime


class BookmarkListResponse(BaseModel):
    total: int
    bookmarks: List[BookmarkResponse]


# -------------------------------------------------------------
# 7. SEARCH HISTORY SCHEMAS
# -------------------------------------------------------------

class SearchHistoryCreate(BaseModel):
    query_text: str = Field(..., min_length=1, max_length=500)
    filters: Optional[Dict[str, Any]] = None
    results_count: Optional[int] = 0


class SearchHistoryResponse(BaseModel):
    search_id: int
    query_text: str
    filters: Dict[str, Any] = {}
    results_count: int
    searched_at: datetime


# -------------------------------------------------------------
# 8. NOTIFICATION SCHEMAS
# -------------------------------------------------------------

class NotificationResponse(BaseModel):
    notification_id: int
    reminder_id: Optional[int] = None
    title: str
    message: str
    notification_type: Optional[str] = None
    is_read: bool
    sent_at: Optional[datetime] = None
    created_at: datetime


class NotificationListResponse(BaseModel):
    unread_count: int
    total: int
    notifications: List[NotificationResponse]


# -------------------------------------------------------------
# 9. PROCEDURE TRACKERS (CHECKLIST PROGRESS) SCHEMAS
# -------------------------------------------------------------

class ProcedureTrackerResponse(BaseModel):
    tracker_id: int
    procedure_id: int
    procedure_name: str
    category: str
    status: str
    completed_documents: List[str]
    total_documents_count: int
    completed_documents_count: int
    notes: Optional[str] = None
    updated_at: datetime


class ProcedureTrackerToggle(BaseModel):
    document_name: str = Field(..., min_length=1, max_length=300)
    completed: Optional[bool] = None
