"""
Vidhik Platform - Complaint / FIR Generator Schemas
====================================================
Pydantic models for structured, safe, and factual legal complaint generation:
- Citizen police complaints / requests for registration of FIR (BNSS Sec 173 / CrPC 154)
- Non-cognizable written complaints (BNSS Sec 174 / CrPC 155)
- Deterministic fact / legal provision separation
- Non-assertive statutory references and procedural guidance
- Safe DOCX export requests
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class ComplaintType(str, Enum):
    """Supported and reserved complaint document categories."""
    POLICE_FIR_REQUEST = "police_fir_request"
    POLICE_NC_COMPLAINT = "police_nc_complaint"
    # Reserved for future phases
    CONSUMER_GRIEVANCE = "consumer_grievance"
    LEGAL_DEMAND_NOTICE = "legal_demand_notice"
    RTI_APPLICATION = "rti_application"
    GENERAL_ADMINISTRATIVE = "general_administrative"


class SafetyStatus(str, Enum):
    """Safety and risk classification status of the generation request."""
    SAFE = "safe"
    EMERGENCY_INTERCEPT = "emergency_intercept"
    REFUSED_ABUSE_VIOLATION = "refused_abuse_violation"
    PROMPT_INJECTION_NEUTRALIZED = "prompt_injection_neutralized"


class AccusedPersonInfo(BaseModel):
    """Factual details of known accused persons or identifying descriptions."""
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Full name or known identifier of the accused person"
    )
    alias_or_nickname: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Known alias, pseudonym, or nickname"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Physical appearance, age, clothing, or distinguishing features if name unknown"
    )
    address_or_location: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Known residential address, workplace, or frequented location"
    )
    contact_or_phone: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Telephone number, social handle, or email if known"
    )


class WitnessInfo(BaseModel):
    """Details of eyewitnesses or persons with material knowledge of the incident."""
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Full name of the witness"
    )
    contact_or_address: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Contact telephone number, email, or address of the witness"
    )
    observation_summary: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Brief summary of what the witness saw, heard, or verified"
    )


class PotentiallyRelevantProvision(BaseModel):
    """
    Non-assertive statutory provision retrieved from the Vidhik legal database.
    Does NOT assert guilt or definitive applicability.
    """
    model_config = ConfigDict(from_attributes=True)

    act_name: str = Field(description="Official name of the governing statute (e.g. 'Bharatiya Nyaya Sanhita, 2023')")
    section_number: str = Field(description="Statutory section number (e.g. '303')")
    section_title: Optional[str] = Field(default=None, description="Official section title (e.g. 'Theft')")
    description: Optional[str] = Field(default=None, description="Statutory definition or legal excerpt")
    is_cognizable: Optional[str] = Field(default=None, description="Cognizable or Non-Cognizable classification")
    is_bailable: Optional[str] = Field(default=None, description="Bailable or Non-Bailable classification")
    triable_by: Optional[str] = Field(default=None, description="Competent court / magistrate having jurisdiction")
    compoundable_status: Optional[str] = Field(default=None, description="Compoundable or Non-Compoundable status")
    predecessor_reference: Optional[str] = Field(default=None, description="Corresponding previous law section (e.g. 'IPC Section 379')")
    source_reference: Optional[str] = Field(default=None, description="Primary legislative source citation in Vidhik")


class PartiesBlock(BaseModel):
    """Structured parties involved in the complaint draft."""
    model_config = ConfigDict(from_attributes=True)

    complainant_name: str = Field(description="Complainant full legal name")
    complainant_contact: str = Field(description="Complainant contact information")
    complainant_address: str = Field(description="Complainant residential or business address")
    accused_list: List[AccusedPersonInfo] = Field(default_factory=list, description="Accused individuals")
    witness_list: List[WitnessInfo] = Field(default_factory=list, description="Witnesses")
    accused_status: str = Field(
        default="Named accused person(s)",
        description="'Named accused person(s)' or 'Unknown person(s)'"
    )


class ComplaintGenerateRequest(BaseModel):
    """
    Request payload for generating a structured factual complaint / FIR request draft.
    Enforces strict length bounds and excludes sensitive credentials.
    """
    model_config = ConfigDict(from_attributes=True)

    complaint_type: ComplaintType = Field(
        default=ComplaintType.POLICE_FIR_REQUEST,
        description="Type of complaint to draft ('police_fir_request' or 'police_nc_complaint')"
    )
    complainant_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Full legal name of the person filing the complaint"
    )
    complainant_contact: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Contact telephone number or verified email address"
    )
    complainant_address: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Full postal address for official communication and jurisdiction"
    )
    incident_description: str = Field(
        ...,
        min_length=20,
        max_length=5000,
        description="Detailed factual description of what occurred, how it transpired, and the sequence of events"
    )
    incident_date: str = Field(
        ...,
        min_length=4,
        max_length=100,
        description="Date of occurrence (e.g., '2026-03-15' or '15th March 2026')"
    )
    incident_time: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Approximate or exact time of the incident (e.g., '14:30 hrs' or 'Around 2:30 PM')"
    )
    incident_location: str = Field(
        ...,
        min_length=2,
        max_length=300,
        description="Exact place, street, landmark, or premises where the incident occurred"
    )
    police_station_name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Name of the concerned Police Station if known"
    )
    jurisdiction_city_state: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="City, District, and State having territorial jurisdiction"
    )
    accused_details: Optional[List[AccusedPersonInfo]] = Field(
        default=None,
        description="List of known accused persons. If omitted, draft specifies 'Unknown person(s)'"
    )
    witnesses: Optional[List[WitnessInfo]] = Field(
        default=None,
        description="List of eyewitnesses or material witnesses"
    )
    evidence_list: Optional[List[str]] = Field(
        default=None,
        description="List of available evidence (e.g., CCTV footage, medical report, photographs, bank statement)"
    )
    financial_loss_amount: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Direct monetary loss, fraud amount, or value of stolen property in INR (₹)"
    )
    injuries_sustained: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Details of physical injuries sustained by complainant or others"
    )
    threats_received: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Specific verbal, physical, or written threats communicated"
    )
    requested_relief: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Specific action requested (e.g., 'Registration of FIR and recovery of stolen property')"
    )
    language: Optional[str] = Field(
        default="en",
        description="Drafting language: 'en' (English), 'mr' (Marathi), 'hi' (Hindi)"
    )


class ComplaintGenerateResponse(BaseModel):
    """
    Structured response containing the formal complaint draft, non-assertive statutory provisions,
    and statutory citizen guidance.
    """
    model_config = ConfigDict(from_attributes=True)

    complaint_id: Optional[str] = Field(
        default=None,
        description="Unique reference identifier for this generated draft"
    )
    complaint_type: ComplaintType = Field(
        description="Category of complaint generated"
    )
    document_title: str = Field(
        description="Formal title of the legal document"
    )
    recipient_header: str = Field(
        description="Formatted authority recipient address block"
    )
    subject_line: str = Field(
        description="Formal subject line of the complaint"
    )
    facts_narrative: str = Field(
        description="Chronological, objective factual narrative synthesized strictly from user-provided facts"
    )
    parties: PartiesBlock = Field(
        description="Structured complainant, accused, and witness information"
    )
    evidence_annexures: List[str] = Field(
        default_factory=list,
        description="List of attached documents, electronic evidence, and suggested statutory annexures"
    )
    prayer: str = Field(
        description="Formal prayer and requested action from the competent authority"
    )
    potentially_relevant_provisions: List[PotentiallyRelevantProvision] = Field(
        default_factory=list,
        description="Statutory provisions retrieved from Vidhik knowledge base (Non-assertive guidance only)"
    )
    procedural_guidance: List[str] = Field(
        default_factory=list,
        description="Statutory citizen rights and step-by-step procedure under Bharatiya Nagarik Suraksha Sanhita, 2023"
    )
    plain_text_draft: str = Field(
        description="Complete, ready-to-print formatted plain-text legal document"
    )
    disclaimer: str = Field(
        description="Mandatory statutory disclaimer regarding automated drafting and police authority"
    )
    safety_status: SafetyStatus = Field(
        default=SafetyStatus.SAFE,
        description="Safety status of the request ('safe', 'emergency_intercept', 'refused_abuse_violation')"
    )
    safety_message: Optional[str] = Field(
        default=None,
        description="Explanatory message if safety or abuse policy was triggered"
    )
    emergency_guidance: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Immediate emergency helpline numbers if urgent physical danger is detected"
    )
    grounding_status: str = Field(
        default="grounded_in_vidhik_knowledge",
        description="Provenance status of legal context and provisions"
    )
    source_references: List[str] = Field(
        default_factory=list,
        description="Statutes and authoritative legislative sources consulted"
    )


class ComplaintExportDocxRequest(BaseModel):
    """
    Request model for exporting an existing generated draft or new complaint payload into a Word (.docx) document.
    """
    model_config = ConfigDict(from_attributes=True)

    draft: Optional[ComplaintGenerateResponse] = Field(
        default=None,
        description="Pre-generated complaint draft response to convert to Word (.docx)"
    )
    request_data: Optional[ComplaintGenerateRequest] = Field(
        default=None,
        description="Raw complaint request data to generate and export directly"
    )
