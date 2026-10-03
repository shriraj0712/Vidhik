"""
Vidhik Platform - Legal Document Analysis Schemas (Phase 11)
============================================================
Pydantic v2 schemas for document analysis requests, structured extractions,
grounded statutory references, risk flags, and case associations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class DocumentParty(BaseModel):
    name: str = Field(..., description="Name or entity identifier of the party")
    role: str = Field(..., description="Role e.g. Plaintiff, Defendant, Lessor, Lessee, First Party, Second Party, Buyer, Seller")
    raw_text: Optional[str] = Field(None, description="Original text excerpt from document")


class DocumentDate(BaseModel):
    date_str: str = Field(..., description="Extracted date text")
    label: str = Field(..., description="Execution Date, Effective Date, Expiry Date, Filing Date, Hearing Date, Notice Date, etc.")
    context: Optional[str] = Field(None, description="Contextual excerpt containing the date")


class DocumentMonetaryValue(BaseModel):
    amount_text: str = Field(..., description="Original textual representation of the financial figure e.g. ₹5,00,000 / Rs. 50,000")
    label: str = Field(..., description="Consideration, Rent, Deposit, Penalty, Stamp Duty, Fees, Compensation, etc.")
    context: Optional[str] = Field(None, description="Surrounding contextual sentence")


class DocumentClause(BaseModel):
    category: str = Field(..., description="Termination, Indemnity, Arbitration, Jurisdiction, Governing Law, Confidentiality, Payment, Liability, Force Majeure, Notice, Dispute Resolution, etc.")
    title: str = Field(..., description="Heading or descriptive title of the clause")
    text_excerpt: str = Field(..., description="Verbatim excerpt from document")
    explanation: Optional[str] = Field(None, description="Objective interpretation of what this clause entails")


class DocumentObligationRight(BaseModel):
    party: str = Field(..., description="The party bearing the obligation or possessing the right")
    type: str = Field(..., description="obligation, right, or duty")
    description: str = Field(..., description="Specific duty or entitlement described in document")
    clause_reference: Optional[str] = Field(default=None, description="Associated clause category or number")


class DocumentRisk(BaseModel):
    severity: str = Field(..., description="High, Medium, or Low")
    title: str = Field(..., description="Short title of the detected potential issue")
    description: str = Field(..., description="Objective analysis of the concern using non-definitive wording")
    evidence_excerpt: Optional[str] = Field(None, description="Supporting excerpt from document text")
    recommendation: Optional[str] = Field(None, description="Recommended review action or mitigation")


class DocumentMissingInfo(BaseModel):
    item: str = Field(..., description="Specific missing component e.g. Execution Date, Schedule of Property, Witness Signatures")
    description: str = Field(..., description="Explanation of why this information is reasonably expected")
    why_expected: str = Field(..., description="Grounds based on document type")


class DocumentActionItem(BaseModel):
    task: str = Field(..., description="Actionable next step")
    responsible_party: Optional[str] = Field("Reviewing Advocate / Client", description="Entity responsible for action")
    deadline_or_trigger: Optional[str] = Field(None, description="Associated timeline or statutory limitation trigger")
    priority: str = Field("Medium", description="High, Medium, or Low")


class LegalReference(BaseModel):
    ref_id: Optional[int] = None
    citation_text: str = Field(..., description="Verbatim statutory citation found or inferred e.g. 'Section 138 of Negotiable Instruments Act'")
    reference_type: str = Field(..., description="'explicit_statutory_mention' or 'contextual_statute_match'")
    is_verified_in_db: bool = Field(False, description="True if matched with authentic record in Vidhik database")
    law_id: Optional[int] = None
    law_name: Optional[str] = None
    section_id: Optional[int] = None
    section_number: Optional[str] = None
    section_title: Optional[str] = None
    relevance_explanation: Optional[str] = None


class DocumentAnalysisResponse(BaseModel):
    analysis_id: Optional[int] = None
    document_name: str
    document_type: str = Field("Unknown / Unclassified", description="Classified legal document category")
    file_type: str = Field(..., description="pdf, docx, txt, pasted_text")
    file_size_bytes: int = 0
    file_hash_sha256: Optional[str] = None
    summary: str = Field(..., description="Comprehensive objective document summary")
    executive_takeaways: List[str] = Field(default_factory=list, description="3-5 bulleted core takeaways")
    parties: List[DocumentParty] = Field(default_factory=list)
    dates: List[DocumentDate] = Field(default_factory=list)
    monetary_values: List[DocumentMonetaryValue] = Field(default_factory=list)
    clauses: List[DocumentClause] = Field(default_factory=list)
    obligations_and_rights: List[DocumentObligationRight] = Field(default_factory=list)
    identified_risks: List[DocumentRisk] = Field(default_factory=list)
    missing_information: List[DocumentMissingInfo] = Field(default_factory=list)
    action_items: List[DocumentActionItem] = Field(default_factory=list)
    legal_references: List[LegalReference] = Field(default_factory=list)
    raw_text_excerpt: Optional[str] = None
    case_id: Optional[int] = None
    created_at: Optional[datetime] = None
    is_scanned_or_empty: bool = False
    warning_message: Optional[str] = None
    disclaimer: str = (
        "Vidhik AI Legal Document Analysis is an automated research and information tool. "
        "It does not constitute formal legal counsel, statutory certification, or advocate advice."
    )


class RawTextAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=10, description="Pasted legal document text or draft clauses")
    document_title: Optional[str] = Field("Pasted Legal Text", max_length=300)
    case_id: Optional[int] = Field(None, description="Optional associated lawyer case ID")


class AnalysisHistoryItem(BaseModel):
    analysis_id: int
    document_name: str
    document_type: str
    file_type: str
    summary_preview: str
    risks_count: int
    verified_references_count: int
    created_at: datetime
    case_id: Optional[int] = None
    case_title: Optional[str] = None


class AnalysisHistoryResponse(BaseModel):
    total: int
    analyses: List[AnalysisHistoryItem]


class SaveToCaseRequest(BaseModel):
    case_id: int = Field(..., description="Target case ID in lawyer workspace")
    save_as_document: bool = Field(True, description="Attach analysis record as a case document")
    save_summary_note: bool = Field(True, description="Save executive summary and risk review as a confidential case note")
    link_verified_sections: bool = Field(True, description="Link verified statutory provisions directly into case_legal_sections")


class SaveToCaseResponse(BaseModel):
    status: str
    message: str
    case_id: int
    saved_document_id: Optional[int] = None
    saved_note_id: Optional[int] = None
    linked_sections_count: int = 0
