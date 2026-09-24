"""
Vidhik Platform - Documentation Support Schemas
================================================
Pydantic validation and serialization models for Phase 12:
Procedures, Required Document Checklists, Preparation Guidance,
and Statutory Authority References.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DocumentRequirement(BaseModel):
    """Schema for an individual document requirement within a checklist."""
    model_config = ConfigDict(from_attributes=True)

    doc_req_id: int
    procedure_id: int
    document_name: str
    document_type: str
    is_mandatory: bool
    purpose: str
    preparation_guidance: Optional[str] = None
    statutory_reference_id: Optional[int] = None
    order_index: int = 1
    
    # Joined statutory reference metadata
    section_number: Optional[str] = None
    section_title: Optional[str] = None
    law_id: Optional[int] = None
    law_name: Optional[str] = None


class ProcedureSummary(BaseModel):
    """Compact summary schema for a legal procedure."""
    model_config = ConfigDict(from_attributes=True)

    procedure_id: int
    procedure_name: str
    procedure_slug: str
    category: str
    description: str
    jurisdiction: str
    authority_type: str
    estimated_processing_days: Optional[int] = None
    official_portal_url: Optional[str] = None
    
    # Governing statutory reference
    governing_law_id: Optional[int] = None
    governing_law_name: Optional[str] = None
    governing_section_id: Optional[int] = None
    governing_section_number: Optional[str] = None
    governing_section_title: Optional[str] = None
    
    # Computed metrics
    total_documents_count: int = 0
    mandatory_documents_count: int = 0
    supporting_documents_count: int = 0


class ProcedureDetail(ProcedureSummary):
    """Detailed procedure schema including partitioned document requirements."""
    mandatory_documents: List[DocumentRequirement] = []
    supporting_documents: List[DocumentRequirement] = []
    all_documents: List[DocumentRequirement] = []


class ChecklistResponse(BaseModel):
    """Schema for structured checklist retrieval."""
    model_config = ConfigDict(from_attributes=True)

    procedure_id: int
    procedure_name: str
    category: str
    jurisdiction: str
    authority_type: str
    governing_law_name: Optional[str] = None
    governing_section_number: Optional[str] = None
    total_count: int
    mandatory_count: int
    supporting_count: int
    mandatory_documents: List[DocumentRequirement] = []
    supporting_documents: List[DocumentRequirement] = []


class CategoryResponse(BaseModel):
    """Category listing with procedure counts."""
    model_config = ConfigDict(from_attributes=True)

    category: str
    procedures_count: int


class ProcedureListResponse(BaseModel):
    """Paginated or filtered list of legal procedures."""
    model_config = ConfigDict(from_attributes=True)

    total: int
    procedures: List[ProcedureSummary]
    categories: List[str] = []
