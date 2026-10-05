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
from .case_intelligence import (
    FactItem,
    LegalIssue,
    RankedLegalProvision,
    AuthorityRecommendation,
    LawyerRequirement,
    LawyerMatch,
    CaseAction,
    DocumentRequirementItem,
    FurtherProcedureStage,
    EmotionalIndicator,
    MissingInformation,
    CaseContext,
    CaseAnalyzeRequest,
    CaseClarificationRequest,
    CaseSwitchResponse
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
    "FactItem",
    "LegalIssue",
    "RankedLegalProvision",
    "AuthorityRecommendation",
    "LawyerRequirement",
    "LawyerMatch",
    "CaseAction",
    "DocumentRequirementItem",
    "FurtherProcedureStage",
    "EmotionalIndicator",
    "MissingInformation",
    "CaseContext",
    "CaseAnalyzeRequest",
    "CaseClarificationRequest",
    "CaseSwitchResponse"
]



