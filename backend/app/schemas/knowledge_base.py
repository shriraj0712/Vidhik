"""
Vidhik Platform - Advanced Legal Knowledge Base Schemas (Phase 17)
==================================================================
Pydantic response models for BNS, BNSS, BSA knowledge layers,
including structured offences, punishments, procedural rules,
evidence provisions, predecessor correlations, and verified judgments.
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field


class OffenceResponse(BaseModel):
    offence_id: int
    law_id: int
    law_name: str
    section_id: int
    section_number: str
    section_title: str
    offence_name: str
    description: Optional[str] = None
    section_reference: Optional[str] = None
    cognizable_status: Optional[str] = "Cognizable"
    bailable_status: Optional[str] = "Non-Bailable"
    compoundable_status: Optional[str] = "Non-Compoundable"
    triable_by: Optional[str] = "Court of Session"
    source: Optional[str] = "Official Bharatiya Nyaya Sanhita, 2023"


class PunishmentResponse(BaseModel):
    punishment_id: int
    law_id: int
    law_name: str
    section_id: int
    section_number: str
    section_title: str
    offence_id: Optional[int] = None
    offence_name: Optional[str] = None
    punishment_type: str
    description: str
    minimum_punishment: Optional[str] = None
    maximum_punishment: Optional[str] = None
    fine_details: Optional[str] = None
    imprisonment_details: Optional[str] = None
    community_service: bool = False
    other_penalty: Optional[str] = None
    source: Optional[str] = "Official Statutory Source"


class ProcedureResponse(BaseModel):
    procedure_id: int
    law_id: int
    law_name: str
    section_id: int
    section_number: str
    section_title: str
    procedure_category: str
    title: str
    description: Optional[str] = None
    statutory_steps: List[str] = Field(default_factory=list)
    safeguards: List[str] = Field(default_factory=list)
    timeline_days: Optional[int] = None
    source: Optional[str] = "Official Bharatiya Nagarik Suraksha Sanhita, 2023"


class EvidenceProvisionResponse(BaseModel):
    evidence_provision_id: int
    law_id: int
    law_name: str
    section_id: int
    section_number: str
    section_title: str
    provision_type: str
    rule_statement: str
    statutory_condition: Optional[str] = None
    admissibility_criteria: List[str] = Field(default_factory=list)
    source: Optional[str] = "Official Bharatiya Sakshya Adhiniyam, 2023"


class PredecessorMappingResponse(BaseModel):
    mapping_id: int
    new_law_id: int
    new_law_name: str
    new_section_id: int
    new_section_number: str
    new_section_title: Optional[str] = None
    old_law_name: str
    old_section_number: str
    correspondence_type: str
    key_changes_summary: Optional[str] = None
    source: Optional[str] = "Official Comparative Correlation Table"


class JudgmentSectionLinkResponse(BaseModel):
    law_name: str
    section_number: str
    relationship_type: str
    relevance: str
    explanation: Optional[str] = None


class JudgmentResponse(BaseModel):
    judgment_id: int
    case_title: str
    case_number: Optional[str] = None
    court: str
    bench: Optional[str] = None
    judgment_date: Optional[date] = None
    citation: Optional[str] = None
    judgment_text: Optional[str] = None
    headnotes: Optional[str] = None
    source_url: Optional[str] = None
    source_name: str = "Supreme Court of India Official Repository"
    source_type: str = "Supreme Court of India"
    linked_sections: List[JudgmentSectionLinkResponse] = Field(default_factory=list)


class KnowledgeOverviewResponse(BaseModel):
    status: str = "active"
    corpus: str = "Vidhik Advanced Legal Knowledge Base (Phase 17)"
    supported_statutes: List[str]
    total_new_statutes: int
    total_offences: int
    total_punishments: int
    total_procedures: int
    total_evidence_provisions: int
    total_predecessor_mappings: int
    total_verified_judgments: int
    categories: Dict[str, int]


class SectionFullContextResponse(BaseModel):
    law_id: int
    law_name: str
    section_id: int
    section_number: str
    section_title: str
    full_text: Optional[str] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    offence: Optional[OffenceResponse] = None
    punishment: Optional[PunishmentResponse] = None
    procedures: List[ProcedureResponse] = Field(default_factory=list)
    evidence_provisions: List[EvidenceProvisionResponse] = Field(default_factory=list)
    predecessor_mappings: List[PredecessorMappingResponse] = Field(default_factory=list)
    judgments: List[JudgmentResponse] = Field(default_factory=list)
