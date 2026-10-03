"""
Vidhik Platform - Legal RAG Schemas
===================================
Pydantic data models for structured legal RAG queries, statutory context
packing, citation tracking, and grounded generation responses.
"""

from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class LegalSourceCitation(BaseModel):
    """
    Authoritative statutory legal citation referencing ground-truth database records.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    law_id: int = Field(description="Unique database identifier of the parent statutory law")
    law_name: str = Field(description="Official statutory act name / title")
    section_id: int = Field(description="Unique database identifier of the section record")
    section_number: str = Field(description="Statutory section number (e.g. '144', '302', '10A')")
    section_title: Optional[str] = Field(default=None, description="Title or heading of the section")
    section_uid: Optional[str] = Field(default=None, description="Canonical legal section slug/UID")
    source_pdf: Optional[str] = Field(default=None, description="Authoritative PDF gazette/act document")
    source_page_start: Optional[int] = Field(default=None, description="Starting page in authoritative source document")
    source_page_end: Optional[int] = Field(default=None, description="Ending page in authoritative source document")
    jurisdiction: Optional[str] = Field(default=None, description="Jurisdiction (e.g. 'India', 'Maharashtra')")


class RetrievedSectionContext(BaseModel):
    """
    Full statutory section context packaged for grounded synthesis and UI inspection.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    law_id: int = Field(description="Identifier of parent statutory act")
    law_name: str = Field(description="Official act title")
    section_id: int = Field(description="Identifier of statutory section")
    section_number: str = Field(description="Section number")
    section_title: Optional[str] = Field(default=None, description="Section heading")
    section_text: str = Field(description="Exact unmodified statutory text from the database")
    relevance_rank: int = Field(description="1-based deterministic relevance rank order")
    relevance_explanation: Optional[str] = Field(default=None, description="Deterministic ranking evidence trigger")
    is_truncated: bool = Field(default=False, description="True if text was excerpted due to length limits")
    source: LegalSourceCitation = Field(description="Traceable citation metadata")


class RetrievalMetadata(BaseModel):
    """
    Telemetry and audit metadata for statutory retrieval and lexicon alignment.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    total_candidates_found: int = Field(description="Total candidate provisions matching initial search query")
    sections_used: int = Field(description="Number of highest-relevance provisions supplied to context builder")
    query_terms_matched: List[str] = Field(default_factory=list, description="Statutory lexicon terms matched")
    concept_categories: List[str] = Field(default_factory=list, description="Legal concept domains identified")
    multilingual_synonyms_applied: List[str] = Field(default_factory=list, description="Multilingual expansion terms applied")
    retrieval_strategy: str = Field(default="deterministic_lexicon_ranked", description="Retrieval methodology name")


class RAGQueryRequest(BaseModel):
    """
    Request payload for grounded legal question answering.
    """
    model_config = ConfigDict(from_attributes=True)

    query: str = Field(
        ...,
        min_length=1,
        description="Natural-language or statutory legal question (e.g. 'What is the penalty for breach of contract?')"
    )
    language: Optional[str] = Field(
        default="en",
        description="Preferred response language: 'en' (English), 'mr' (Marathi), 'hi' (Hindi)"
    )
    jurisdiction: Optional[str] = Field(
        default=None,
        description="Optional filter by jurisdiction (e.g. 'India', 'Maharashtra')"
    )
    law_id: Optional[int] = Field(
        default=None,
        gt=0,
        description="Optional filter targeting a specific parent statute ID"
    )
    max_sections: Optional[int] = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of authoritative statutory sections to include in retrieval context"
    )
    temperature: Optional[float] = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Generation temperature (low value ensures deterministic, factual adherence)"
    )


class RAGResponse(BaseModel):
    """
    Strictly grounded legal answer response with verified source citations.
    """
    model_config = ConfigDict(from_attributes=True)

    query: str = Field(description="The user's original legal question")
    language: str = Field(description="Language of the generated response ('en', 'mr', 'hi')")
    answer: str = Field(description="Grounded AI response citing verified statutory provisions")
    confidence: str = Field(
        description="Grounding status: 'grounded_high', 'grounded_medium', 'insufficient_context', 'no_context'"
    )
    is_grounded: bool = Field(description="Boolean indicating whether answer is anchored to verified statutory text")
    sources: List[LegalSourceCitation] = Field(default_factory=list, description="Traceable database citations")
    retrieved_sections: List[RetrievedSectionContext] = Field(default_factory=list, description="Authoritative provisions retrieved")
    retrieval_metadata: RetrievalMetadata = Field(description="Audit telemetry of query analysis and retrieval")
    disclaimer: str = Field(
        default="This response is strictly grounded in Indian statutory law retrieved from the Vidhik legal database. It is intended for legal research and educational reference only and does not constitute formal legal counsel.",
        description="Mandatory legal information disclaimer"
    )
