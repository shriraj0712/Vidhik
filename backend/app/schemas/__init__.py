"""
Vidhik Platform - Pydantic Response & Request Schemas
"""

from .law import LawResponse, LawSummaryResponse, LawListResponse
from .section import SectionResponse, SectionSummaryResponse, SectionListResponse
from .search import SearchResponse, SearchResultItem
from .query import LegalQueryAnalysis, MatchedTerm, MatchedConcept, MatchedSynonym
from .documentation import (
    DocumentRequirement,
    ProcedureSummary,
    ProcedureDetail,
    ChecklistResponse,
    CategoryResponse,
    ProcedureListResponse
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

from .resolution import (
    RecommendationType,
    RiskLevel,
    TriggeredRuleInfo,
    RelevantProcedureRef,
    ResolutionEvaluationRequest,
    ResolutionEvaluationResponse
)

__all__ = [
    "LawResponse",
    "LawSummaryResponse",
    "LawListResponse",
    "SectionResponse",
    "SectionSummaryResponse",
    "SectionListResponse",
    "SearchResponse",
    "SearchResultItem",
    "LegalQueryAnalysis",
    "MatchedTerm",
    "MatchedConcept",
    "MatchedSynonym",
    "DocumentRequirement",
    "ProcedureSummary",
    "ProcedureDetail",
    "ChecklistResponse",
    "CategoryResponse",
    "ProcedureListResponse",
    "RegisterRequest",
    "CitizenProfileResponse",
    "CitizenProfileUpdate",
    "CitizenDashboardMetrics",
    "CitizenCaseResponse",
    "CitizenCaseDetailResponse",
    "CitizenCaseCreate",
    "CitizenDocumentResponse",
    "CitizenDocumentUpload",
    "BookmarkCreate",
    "BookmarkResponse",
    "BookmarkListResponse",
    "SearchHistoryCreate",
    "SearchHistoryResponse",
    "NotificationResponse",
    "NotificationListResponse",
    "ProcedureTrackerResponse",
    "ProcedureTrackerToggle",
    "RecommendationType",
    "RiskLevel",
    "TriggeredRuleInfo",
    "RelevantProcedureRef",
    "ResolutionEvaluationRequest",
    "ResolutionEvaluationResponse"
]
