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

from .complaint_generator import (
    ComplaintType,
    SafetyStatus,
    AccusedPersonInfo,
    WitnessInfo,
    PotentiallyRelevantProvision,
    PartiesBlock,
    ComplaintGenerateRequest,
    ComplaintGenerateResponse,
    ComplaintExportDocxRequest
)

from .ai_safety import (
    SafetyCheckRequest,
    SafetyViolation,
    SafetyCheckResponse
)

from .legal_classifier import (
    LegalClassificationRequest,
    AreaScore,
    LegalClassificationResponse
)

from .intent_router import (
    IntentRoutingRequest,
    IntentRoutingResponse
)

from .emergency import (
    EmergencyEvaluationRequest,
    HelplineInfo,
    EmergencyEvaluationResponse
)

from .element_verification import (
    ElementVerificationRequest,
    ElementMatch,
    ElementVerificationResponse
)

from .constitutional import (
    ConstitutionalAnalysisRequest,
    ConstitutionalRightMatch,
    ConstitutionalAnalysisResponse
)

from .traffic import (
    TrafficAnalysisRequest,
    TrafficOffenceDetail,
    TrafficAnalysisResponse
)

from .authority import (
    AuthorityRecommendationRequest,
    AuthorityDetail,
    AuthorityRecommendationResponse
)

from .voice import (
    VoiceTranscriptionRequest,
    VoiceTranscriptionResponse
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
    "ResolutionEvaluationResponse",
    "ComplaintType",
    "SafetyStatus",
    "AccusedPersonInfo",
    "WitnessInfo",
    "PotentiallyRelevantProvision",
    "PartiesBlock",
    "ComplaintGenerateRequest",
    "ComplaintGenerateResponse",
    "ComplaintExportDocxRequest",
    "SafetyCheckRequest",
    "SafetyViolation",
    "SafetyCheckResponse",
    "LegalClassificationRequest",
    "AreaScore",
    "LegalClassificationResponse",
    "IntentRoutingRequest",
    "IntentRoutingResponse",
    "EmergencyEvaluationRequest",
    "HelplineInfo",
    "EmergencyEvaluationResponse",
    "ElementVerificationRequest",
    "ElementMatch",
    "ElementVerificationResponse",
    "ConstitutionalAnalysisRequest",
    "ConstitutionalRightMatch",
    "ConstitutionalAnalysisResponse",
    "TrafficAnalysisRequest",
    "TrafficOffenceDetail",
    "TrafficAnalysisResponse",
    "AuthorityRecommendationRequest",
    "AuthorityDetail",
    "AuthorityRecommendationResponse",
    "VoiceTranscriptionRequest",
    "VoiceTranscriptionResponse"
]
