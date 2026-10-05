import re
import time
from typing import List, Dict, Any, Optional
from app.schemas.traffic import (
    TrafficAnalysisRequest,
    TrafficAnalysisResponse,
    TrafficOffenceDetail
)


class TrafficService:
    """
    Traffic Legal Engine for VIDHIK AI.
    Grounds traffic issues and e-Challan disputes in the Motor Vehicles Act, 1988 (as amended by Act 32 of 2019).
    """

    OFFENCES_DB = [
        {
            "key": "helmet",
            "name": "Riding Without Helmet / Non-Standard Helmet",
            "section": "Section 194D, Motor Vehicles Act, 1988",
            "penalty": "₹1,000 fine and disqualification from holding driving licence for up to 3 months",
            "license_consequence": "Licence disqualification up to 3 months",
            "court_required": False,
            "patterns": [r"\b(helmet|no helmet|without helmet|हेल्मेट|विना हेल्मेट|बिना हेलमेट)\b"]
        },
        {
            "key": "seatbelt",
            "name": "Driving Without Seatbelt / Child Restraint",
            "section": "Section 194B, Motor Vehicles Act, 1988",
            "penalty": "₹1,000 fine",
            "license_consequence": None,
            "court_required": False,
            "patterns": [r"\b(seatbelt|seat belt|no seatbelt|सीटबेल्ट|बिना सीटबेल्ट)\b"]
        },
        {
            "key": "speeding",
            "name": "Over-speeding / Driving at Excessive Speed",
            "section": "Section 183, Motor Vehicles Act, 1988",
            "penalty": "₹1,000 to ₹2,000 for LMV; ₹2,000 to ₹4,000 for Medium/Heavy Passenger Vehicles",
            "license_consequence": "Licence impoundment for repeat offence",
            "court_required": False,
            "patterns": [r"\b(overspeeding|speeding|high speed|speed limit|वेग मर्यादा|जादा वेग|तेज़ रफ़्तार)\b"]
        },
        {
            "key": "signal",
            "name": "Dangerous Driving / Jumping Red Light / Using Mobile while Driving",
            "section": "Section 184, Motor Vehicles Act, 1988",
            "penalty": "₹1,000 to ₹5,000 and/or imprisonment up to 1 year for 1st offence; up to ₹10,000 for 2nd offence",
            "license_consequence": "Suspension of licence for serious violations",
            "court_required": False,
            "patterns": [r"\b(red light|signal jump|jumping signal|mobile while driving|phone call while driving|रॅश ड्रायव्हिंग|सिग्नल तोडला|लाल बत्ती)\b"]
        },
        {
            "key": "drunk_driving",
            "name": "Drunk Driving / Driving Under Influence of Alcohol or Drugs (>30mg/100ml BAC)",
            "section": "Section 185, Motor Vehicles Act, 1988",
            "penalty": "₹10,000 and/or imprisonment up to 6 months for 1st offence; ₹15,000 and/or imprisonment up to 2 years for 2nd offence",
            "license_consequence": "Mandatory suspension of driving licence",
            "court_required": True,
            "patterns": [r"\b(drunk driving|breathalyzer|alcohol test|drank alcohol|दारू पिऊन गाडी|शराब पीकर गाड़ी)\b"]
        },
        {
            "key": "no_license",
            "name": "Driving Without Valid Driving Licence",
            "section": "Section 181, Motor Vehicles Act, 1988",
            "penalty": "₹5,000 fine and/or community service",
            "license_consequence": "Vehicle may be impounded if no valid driver present",
            "court_required": False,
            "patterns": [r"\b(no licence|without licence|driving licence expired|no dl|विना परवाना|बिना लाइसेंस)\b"]
        },
        {
            "key": "insurance",
            "name": "Driving Uninsured Vehicle (Without Third-Party Insurance)",
            "section": "Section 196, Motor Vehicles Act, 1988",
            "penalty": "₹2,000 and/or imprisonment up to 3 months for 1st offence; ₹4,000 for 2nd offence",
            "license_consequence": "Vehicle impoundment until valid policy produced",
            "court_required": False,
            "patterns": [r"\b(no insurance|insurance expired|third party insurance|विना विमा|बिना बीमा)\b"]
        },
        {
            "key": "puc",
            "name": "Driving Without Valid PUC (Pollution Under Control Certificate)",
            "section": "Section 190(2), Motor Vehicles Act, 1988",
            "penalty": "₹10,000 fine and/or imprisonment up to 3 months; licence disqualification for 3 months",
            "license_consequence": "Licence disqualification for 3 months",
            "court_required": False,
            "patterns": [r"\b(puc|pollution certificate|puc expired|धूर प्रमाणपत्र|प्रदूषण प्रमाण पत्र)\b"]
        },
        {
            "key": "triple_riding",
            "name": "Pillion / Triple Riding on Two-Wheeler",
            "section": "Section 194C, Motor Vehicles Act, 1988",
            "penalty": "₹1,000 fine and disqualification of licence for 3 months",
            "license_consequence": "Licence disqualification for 3 months",
            "court_required": False,
            "patterns": [r"\b(triple riding|three people on bike|तीन जण गाडीवर|ट्रिपल राइडिंग)\b"]
        },
        {
            "key": "emergency_vehicle",
            "name": "Failure to Give Way to Emergency Vehicles (Ambulance/Fire Brigade)",
            "section": "Section 194E, Motor Vehicles Act, 1988",
            "penalty": "₹10,000 fine and/or imprisonment up to 6 months",
            "license_consequence": None,
            "court_required": False,
            "patterns": [r"\b(ambulance|blocked ambulance|fire brigade|emergency vehicle|रुग्णवाहिका|एम्बुलेंस)\b"]
        }
    ]

    DISPUTE_STEPS = [
        "1. Verify Challan on official Parivahan Portal (https://echallan.parivahan.gov.in) using Vehicle No or Challan No.",
        "2. Check the evidence photo/CCTV clip attached to the e-Challan to confirm vehicle registration plate and driver identity.",
        "3. If incorrectly issued (e.g. cloned plate, wrong location, camera glitch), click 'Grievance' / 'Dispute Challan' on the State Traffic Police portal.",
        "4. If disputed online without resolution, choose the 'Send to Virtual Court' option (https://vcourts.gov.in) to contest before a Metropolitan / Judicial Magistrate.",
        "5. Alternatively, compoundable challans can be settled with substantial rebates at the quarterly National Lok Adalat."
    ]

    @classmethod
    def analyze_traffic(cls, request: TrafficAnalysisRequest) -> TrafficAnalysisResponse:
        start_time = time.time()
        desc = request.violation_description.lower()

        matched_offences: List[TrafficOffenceDetail] = []

        for off in cls.OFFENCES_DB:
            is_match = False
            for pattern in off["patterns"]:
                if re.search(pattern, desc, re.IGNORECASE):
                    is_match = True
                    break
            if is_match:
                matched_offences.append(TrafficOffenceDetail(
                    offence_name=off["name"],
                    mva_section=off["section"],
                    statutory_penalty_range=off["penalty"],
                    license_consequence=off["license_consequence"],
                    court_appearance_required=off["court_required"]
                ))

        if not matched_offences:
            # Default General Offence under Section 177 MVA
            primary = TrafficOffenceDetail(
                offence_name="General Traffic Violation / Contravention of Rules",
                mva_section="Section 177, Motor Vehicles Act, 1988",
                statutory_penalty_range="₹500 for 1st offence; ₹1,500 for 2nd / subsequent offence",
                license_consequence=None,
                court_appearance_required=False
            )
            related = []
        else:
            primary = matched_offences[0]
            related = matched_offences[1:]

        mandatory_docs = [
            "Driving Licence (Valid and matching vehicle class)",
            "Vehicle Registration Certificate (RC)",
            "Valid Third-Party / Comprehensive Insurance Policy",
            "Valid Pollution Under Control (PUC) Certificate",
            "Commercial Permit and Fitness Certificate (if commercial vehicle)"
        ]

        online_portals = [
            "https://echallan.parivahan.gov.in (National e-Challan Portal)",
            "https://vcourts.gov.in (Virtual Courts for Traffic Challan Adjudication)",
            "https://parivahan.gov.in (Parivahan Sewa / mParivahan App)",
            "DigiLocker App / mParivahan (Legally valid digital documents under Rule 139 CMV Rules)"
        ]

        return TrafficAnalysisResponse(
            primary_offence=primary,
            related_offences=related,
            mandatory_documents=mandatory_docs,
            dispute_challenge_process=cls.DISPUTE_STEPS,
            online_payment_portals=online_portals,
            metadata={"latency_ms": round((time.time() - start_time) * 1000, 2), "state": request.state}
        )
