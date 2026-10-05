from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TrafficAnalysisRequest(BaseModel):
    violation_description: str = Field(..., min_length=3, max_length=5000, description="Description of the traffic issue, challan, or citation")
    challan_number: Optional[str] = Field(None, description="Optional e-Challan number if available")
    vehicle_type: Optional[str] = Field("two_wheeler", description="Vehicle type (two_wheeler, four_wheeler, commercial)")
    state: Optional[str] = Field("General / Pan-India", description="State or Union Territory")


class TrafficOffenceDetail(BaseModel):
    offence_name: str = Field(..., description="Name of the traffic offence")
    mva_section: str = Field(..., description="Applicable section of the Motor Vehicles Act, 1988 (as amended)")
    statutory_penalty_range: str = Field(..., description="Prescribed penalty / fine range under the Act")
    license_consequence: Optional[str] = Field(None, description="Disqualification or suspension details if applicable")
    court_appearance_required: bool = Field(False, description="Whether compounding on spot/online is permitted or court appearance is mandatory")


class TrafficAnalysisResponse(BaseModel):
    primary_offence: TrafficOffenceDetail = Field(..., description="Primary identified traffic violation")
    related_offences: List[TrafficOffenceDetail] = Field(default_factory=list, description="Other potential or compound violations")
    mandatory_documents: List[str] = Field(default_factory=list, description="Mandatory documents to carry / produce (DigiLocker/mParivahan)")
    dispute_challenge_process: List[str] = Field(default_factory=list, description="Step-by-step procedure to challenge incorrect e-Challan")
    online_payment_portals: List[str] = Field(default_factory=list, description="Official government portals for payment/verification")
    disclaimer: str = Field(
        default="Fines are based on the central Motor Vehicles (Amendment) Act. Exact compoundable amounts may vary slightly by State Government notification.",
        description="Statutory penalty variation disclaimer"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata and latency info")
