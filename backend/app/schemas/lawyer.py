"""
Vidhik Platform - Lawyer Module Pydantic Schemas
=================================================
Pydantic v2 schemas for the Lawyer Workspace:
- Dashboard Metrics
- Client Management
- Case Management & Details
- Document Management
- Hearing Scheduling
- Case Notes
- Legal Research Association
- Lawyer Profile
"""

from typing import Optional, List, Any
from datetime import datetime, date, time
from pydantic import BaseModel, Field


# -------------------------------------------------------------
# 1. AUTH & USER SCHEMAS
# -------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str = Field(..., description="Lawyer or User email address")
    password: str = Field(..., min_length=4, description="Plaintext password")


class AuthUserResponse(BaseModel):
    user_id: int
    username: str
    email: str
    full_name: str
    phone: Optional[str] = None
    role: str
    lawyer_id: Optional[int] = None
    token: str
    is_active: bool


# -------------------------------------------------------------
# 2. DASHBOARD SCHEMAS
# -------------------------------------------------------------

class DashboardMetricsResponse(BaseModel):
    total_clients: int
    active_cases: int
    upcoming_hearings: int
    recent_documents_count: int
    recent_cases: List[dict]
    upcoming_hearings_list: List[dict]
    recent_documents: List[dict]
    recent_activity: List[dict]


# -------------------------------------------------------------
# 3. CLIENT SCHEMAS
# -------------------------------------------------------------

class ClientBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=200)
    email: str = Field(..., min_length=5, max_length=150)
    phone: Optional[str] = Field(None, max_length=20)


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = None


class ClientResponse(ClientBase):
    user_id: int
    role: str = "user"
    is_active: bool = True
    created_at: datetime
    active_cases_count: int = 0
    cases: Optional[List[dict]] = None


class ClientListResponse(BaseModel):
    total: int
    clients: List[ClientResponse]


# -------------------------------------------------------------
# 4. CASE SCHEMAS
# -------------------------------------------------------------

class CaseCreate(BaseModel):
    user_id: int = Field(..., description="Client User ID")
    case_title: str = Field(..., min_length=3, max_length=300)
    case_number: Optional[str] = Field(None, max_length=100)
    case_type: Optional[str] = Field(None, max_length=100)
    court_name: Optional[str] = Field(None, max_length=300)
    opposite_party: Optional[str] = Field(None, max_length=250)
    status: str = Field("active", description="active, pending, resolved, closed, withdrawn")
    filing_date: Optional[date] = None
    incident_date: Optional[date] = None
    location: Optional[str] = Field(None, max_length=300)
    police_station: Optional[str] = Field(None, max_length=300)
    case_description: Optional[str] = None


class CaseUpdate(BaseModel):
    case_title: Optional[str] = None
    case_number: Optional[str] = None
    case_type: Optional[str] = None
    court_name: Optional[str] = None
    opposite_party: Optional[str] = None
    status: Optional[str] = None
    filing_date: Optional[date] = None
    incident_date: Optional[date] = None
    location: Optional[str] = None
    police_station: Optional[str] = None
    case_description: Optional[str] = None


class CaseSummaryResponse(BaseModel):
    case_id: int
    user_id: int
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    assigned_lawyer_id: Optional[int] = None
    lawyer_name: Optional[str] = None
    case_title: str
    case_number: Optional[str] = None
    case_type: Optional[str] = None
    court_name: Optional[str] = None
    opposite_party: Optional[str] = None
    status: str
    filing_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime


class CaseListResponse(BaseModel):
    total: int
    cases: List[CaseSummaryResponse]


class CaseDetailResponse(CaseSummaryResponse):
    incident_date: Optional[date] = None
    location: Optional[str] = None
    police_station: Optional[str] = None
    case_description: Optional[str] = None
    client_email: Optional[str] = None
    documents: List[dict] = []
    hearings: List[dict] = []
    notes: List[dict] = []
    legal_sections: List[dict] = []
    updates: List[dict] = []


# -------------------------------------------------------------
# 5. DOCUMENT SCHEMAS
# -------------------------------------------------------------

class DocumentCreate(BaseModel):
    case_id: int
    client_id: Optional[int] = None
    document_name: str = Field(..., min_length=2, max_length=300)
    document_type: str = Field("General", max_length=100)
    file_path: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    file_size_bytes: Optional[int] = 0
    mime_type: Optional[str] = "application/pdf"


class DocumentResponse(BaseModel):
    document_id: int
    case_id: int
    case_title: Optional[str] = None
    case_number: Optional[str] = None
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    lawyer_id: Optional[int] = None
    document_name: str
    document_type: str
    file_path: str
    file_size_bytes: int
    mime_type: str
    upload_status: str
    description: Optional[str] = None
    created_at: datetime


class DocumentListResponse(BaseModel):
    total: int
    documents: List[DocumentResponse]


# -------------------------------------------------------------
# 6. HEARING SCHEMAS
# -------------------------------------------------------------

class HearingCreate(BaseModel):
    case_id: int
    title: str = Field(..., min_length=3, max_length=300)
    description: Optional[str] = None
    reminder_date: date
    reminder_time: Optional[time] = None
    court_name: Optional[str] = None
    judge_name: Optional[str] = None
    status: str = Field("scheduled", description="scheduled, adjourned, completed, cancelled")
    priority: str = Field("normal", description="high, normal, low")
    notes: Optional[str] = None


class HearingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    reminder_date: Optional[date] = None
    reminder_time: Optional[time] = None
    court_name: Optional[str] = None
    judge_name: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None


class HearingResponse(BaseModel):
    reminder_id: int
    case_id: int
    case_title: Optional[str] = None
    case_number: Optional[str] = None
    lawyer_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    reminder_type: str = "hearing"
    reminder_date: date
    reminder_time: Optional[time] = None
    court_name: Optional[str] = None
    judge_name: Optional[str] = None
    status: str
    priority: str
    notes: Optional[str] = None
    created_at: datetime


class HearingListResponse(BaseModel):
    total: int
    upcoming: List[HearingResponse]
    past: List[HearingResponse]


# -------------------------------------------------------------
# 7. CASE NOTE SCHEMAS
# -------------------------------------------------------------

class NoteCreate(BaseModel):
    case_id: int
    title: Optional[str] = Field(None, max_length=300)
    content: str = Field(..., min_length=1)
    is_pinned: bool = False


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_pinned: Optional[bool] = None


class NoteResponse(BaseModel):
    note_id: int
    case_id: int
    case_title: Optional[str] = None
    lawyer_id: Optional[int] = None
    title: Optional[str] = None
    content: str
    is_pinned: bool
    created_at: datetime
    updated_at: datetime


# -------------------------------------------------------------
# 8. LEGAL RESEARCH SECTION LINK SCHEMAS
# -------------------------------------------------------------

class CaseSectionLinkRequest(BaseModel):
    section_id: int
    relevance_score: float = Field(85.0, ge=0.0, le=100.0)
    explanation: Optional[str] = None


class CaseSectionLinkResponse(BaseModel):
    case_id: int
    section_id: int
    section_number: str
    section_title: Optional[str] = None
    law_name: Optional[str] = None
    relevance_score: float
    explanation: Optional[str] = None
    created_at: datetime


# -------------------------------------------------------------
# 9. LAWYER PROFILE SCHEMAS
# -------------------------------------------------------------

class LawyerProfileResponse(BaseModel):
    lawyer_id: int
    user_id: int
    full_name: str
    email: str
    phone: Optional[str] = None
    bar_council_number: Optional[str] = None
    specialization: Optional[str] = None
    experience_years: int = 0
    bio: Optional[str] = None
    court_practice: Optional[str] = None
    office_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    is_verified: bool = True
    specializations_list: List[str] = []
    languages_list: List[str] = []
    locations_list: List[dict] = []
    created_at: datetime


class LawyerProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    bar_council_number: Optional[str] = None
    specialization: Optional[str] = None
    experience_years: Optional[int] = None
    bio: Optional[str] = None
    court_practice: Optional[str] = None
    office_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    specializations_list: Optional[List[str]] = None
    languages_list: Optional[List[str]] = None
