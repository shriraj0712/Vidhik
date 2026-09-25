"""
Vidhik Platform - Pydantic Response & Request Schemas
=====================================================
Unified export of schemas across all modules: statutory laws,
sections, search, query analysis, RAG, AI assistant, documentation,
document analysis, lawyer workspace, citizen portal, and authentication/security.
"""

from .law import LawResponse, LawSummaryResponse, LawListResponse
from .section import SectionResponse, SectionSummaryResponse, SectionListResponse
from .search import SearchResponse, SearchResultItem
from .query import LegalQueryAnalysis, MatchedTerm, MatchedConcept, MatchedSynonym
from .rag import (
    LegalSourceCitation,
    RetrievedSectionContext,
    RetrievalMetadata,
    RAGQueryRequest,
    RAGResponse
)
from .assistant import (
    ChatMessage,
    AssistantChatRequest,
    AssistantChatResponse
)
from .documentation import (
    DocumentRequirement,
    ProcedureSummary,
    ProcedureDetail,
    ChecklistResponse,
    CategoryResponse,
    ProcedureListResponse
)
from .document_analysis import (
    DocumentParty,
    DocumentDate,
    DocumentMonetaryValue,
    DocumentClause,
    DocumentObligationRight,
    DocumentRisk,
    DocumentMissingInfo,
    DocumentActionItem,
    LegalReference,
    DocumentAnalysisResponse,
    RawTextAnalysisRequest,
    AnalysisHistoryItem,
    AnalysisHistoryResponse,
    SaveToCaseRequest,
    SaveToCaseResponse
)
from .lawyer import (
    LoginRequest,
    AuthUserResponse,
    DashboardMetricsResponse,
    ClientBase,
    ClientCreate,
    ClientUpdate,
    ClientResponse,
    ClientListResponse,
    CaseCreate,
    CaseUpdate,
    CaseSummaryResponse,
    CaseListResponse,
    CaseDetailResponse,
    DocumentCreate,
    DocumentResponse,
    DocumentListResponse,
    HearingCreate,
    HearingUpdate,
    HearingResponse,
    HearingListResponse,
    NoteCreate,
    NoteUpdate,
    NoteResponse,
    CaseSectionLinkRequest,
    CaseSectionLinkResponse,
    LawyerProfileResponse,
    LawyerProfileUpdate
)
from .citizen import (
    RegisterRequest,
    CitizenProfileResponse,
    CitizenProfileUpdate,
    CitizenDashboardMetrics,
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
from .auth import (
    TokenResponse,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    AdminUserResponse,
    AdminUserListResponse,
    AdminUserStatusUpdateRequest,
    AuditLogResponse,
    AuditLogListResponse
)

__all__ = [
    # Law & Section
    "LawResponse", "LawSummaryResponse", "LawListResponse",
    "SectionResponse", "SectionSummaryResponse", "SectionListResponse",
    "SearchResponse", "SearchResultItem",
    # Query Analysis
    "LegalQueryAnalysis", "MatchedTerm", "MatchedConcept", "MatchedSynonym",
    # RAG & Assistant (Phase 9 & 10)
    "LegalSourceCitation", "RetrievedSectionContext", "RetrievalMetadata",
    "RAGQueryRequest", "RAGResponse",
    "ChatMessage", "AssistantChatRequest", "AssistantChatResponse",
    # Documentation Support (Phase 12)
    "DocumentRequirement", "ProcedureSummary", "ProcedureDetail",
    "ChecklistResponse", "CategoryResponse", "ProcedureListResponse",
    # Document Analysis (Phase 11)
    "DocumentParty", "DocumentDate", "DocumentMonetaryValue", "DocumentClause",
    "DocumentObligationRight", "DocumentRisk", "DocumentMissingInfo", "DocumentActionItem",
    "LegalReference", "DocumentAnalysisResponse", "RawTextAnalysisRequest",
    "AnalysisHistoryItem", "AnalysisHistoryResponse", "SaveToCaseRequest", "SaveToCaseResponse",
    # Lawyer Module (Phase 13)
    "LoginRequest", "AuthUserResponse", "DashboardMetricsResponse",
    "ClientBase", "ClientCreate", "ClientUpdate", "ClientResponse", "ClientListResponse",
    "CaseCreate", "CaseUpdate", "CaseSummaryResponse", "CaseListResponse", "CaseDetailResponse",
    "DocumentCreate", "DocumentResponse", "DocumentListResponse",
    "HearingCreate", "HearingUpdate", "HearingResponse", "HearingListResponse",
    "NoteCreate", "NoteUpdate", "NoteResponse", "CaseSectionLinkRequest", "CaseSectionLinkResponse",
    "LawyerProfileResponse", "LawyerProfileUpdate",
    # Citizen Module (Phase 14)
    "RegisterRequest", "CitizenProfileResponse", "CitizenProfileUpdate",
    "CitizenDashboardMetrics", "CitizenCaseResponse", "CitizenCaseDetailResponse",
    "CitizenCaseCreate", "CitizenDocumentResponse", "CitizenDocumentUpload",
    "BookmarkCreate", "BookmarkResponse", "BookmarkListResponse",
    "SearchHistoryCreate", "SearchHistoryResponse",
    "NotificationResponse", "NotificationListResponse",
    "ProcedureTrackerResponse", "ProcedureTrackerToggle",
    # Auth & Security (Phase 15)
    "TokenResponse", "RefreshTokenRequest", "ForgotPasswordRequest",
    "ResetPasswordRequest", "ChangePasswordRequest",
    "AdminUserResponse", "AdminUserListResponse", "AdminUserStatusUpdateRequest",
    "AuditLogResponse", "AuditLogListResponse"
]
