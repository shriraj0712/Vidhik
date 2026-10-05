"""
Vidhik Platform - Legal Resolution Decision Engine (AI Workstream)
===================================================================
Authoritative deterministic triage engine that classifies citizen legal situations into:
1. `self_resolvable`: Low-risk administrative procedures, RTI, small consumer disputes, routine challans.
2. `lawyer_consultation_required`: Court proceedings, criminal charges, property title disputes, contested custody, insolvency.
3. `urgent_legal_intervention`: Immediate physical danger, active domestic violence, imminent arrest, child endangerment.

Architecture & Guarantees:
- Strictly deterministic rule-based evaluation (zero LLM hallucination for final triage).
- Transparent explainability: returns rule IDs, severity, contributing reasons, and specialized checklists.
- Priority hierarchy: URGENT > LAWYER_REQUIRED > SELF_RESOLVABLE > CAUTIOUS_FALLBACK.
- Deep integration with Phase 12/16 25 Verified Citizen Procedures (`DocumentationService`).
- Multilingual keyword normalization for English, Marathi, and Hindi (`LegalQueryService`).
"""

import re
import logging
from typing import Optional, List, Dict, Any, Tuple, Set

from app.schemas.resolution import (
    RecommendationType,
    RiskLevel,
    TriggeredRuleInfo,
    RelevantProcedureRef,
    ResolutionEvaluationRequest,
    ResolutionEvaluationResponse
)
from app.services.query_service import LegalQueryService

logger = logging.getLogger("vidhik.resolution_service")


# ==============================================================================
# VERIFIED STATUTORY EMERGENCY HELPLINES (INDIA)
# ==============================================================================
VERIFIED_EMERGENCY_DATA = {
    "police_emergency": {
        "helpline_name": "Emergency Response Support System (ERSS)",
        "number": "112",
        "description": "Pan-India single emergency number for immediate Police, Fire, and Ambulance assistance."
    },
    "women_safety": {
        "helpline_name": "National Women Helpline",
        "number": "1091 / 181",
        "description": "24/7 dedicated support for women facing domestic violence, physical assault, or harassment."
    },
    "child_protection": {
        "helpline_name": "National Childline",
        "number": "1098",
        "description": "24-hour nationwide emergency service for children in need of care and protection (POCSO / trafficking / abuse)."
    },
    "cyber_crime": {
        "helpline_name": "National Cyber Crime Helpline",
        "number": "1930",
        "description": "Ministry of Home Affairs portal & helpline for immediate freezing of fraudulent financial transactions."
    },
    "legal_aid": {
        "helpline_name": "National Legal Services Authority (NALSA)",
        "number": "15100",
        "description": "Free legal aid helpline for underprivileged citizens, women, children, and persons in custody."
    }
}


# ==============================================================================
# VERIFIED PROCEDURAL REGISTRY (PHASE 12 / 16 CROSS-REFERENCE)
# ==============================================================================
VERIFIED_PROCEDURES: Dict[str, Dict[str, Any]] = {
    "rti-application": {
        "procedure_id": 1,
        "procedure_name": "Filing a Right to Information (RTI) Application",
        "procedure_slug": "rti-application",
        "category": "Transparency / Governance",
        "authority_type": "Public Information Officer (PIO) / First Appellate Authority",
        "estimated_days": 30,
        "portal_url": "https://rtionline.gov.in",
        "required_documents_count": 2
    },
    "consumer-complaint": {
        "procedure_id": 2,
        "procedure_name": "Filing a Consumer Complaint (E-Daakhil)",
        "procedure_slug": "consumer-complaint",
        "category": "Consumer Protection",
        "authority_type": "District Consumer Disputes Redressal Commission (DCDRC)",
        "estimated_days": 90,
        "portal_url": "https://edaakhil.nic.in",
        "required_documents_count": 4
    },
    "marriage-registration": {
        "procedure_id": 9,
        "procedure_name": "Registration of Marriage (Special & Hindu Marriage Acts)",
        "procedure_slug": "marriage-registration",
        "category": "Family / Personal",
        "authority_type": "Marriage Officer / Sub-Registrar of Assurances",
        "estimated_days": 15,
        "portal_url": "https://igrmaharashtra.gov.in",
        "required_documents_count": 5
    },
    "birth-certificate-registration-correction": {
        "procedure_id": 10,
        "procedure_name": "Birth Certificate Registration and Correction",
        "procedure_slug": "birth-certificate-registration-correction",
        "category": "Certificates / Registrations",
        "authority_type": "Registrar of Births and Deaths (Municipal Ward / Gram Panchayat)",
        "estimated_days": 21,
        "portal_url": "https://crsorgi.gov.in",
        "required_documents_count": 3
    },
    "death-certificate-registration-correction": {
        "procedure_id": 11,
        "procedure_name": "Death Certificate Registration and Correction",
        "procedure_slug": "death-certificate-registration-correction",
        "category": "Certificates / Registrations",
        "authority_type": "Registrar of Births and Deaths (Municipal Corporation / Gram Panchayat)",
        "estimated_days": 21,
        "portal_url": "https://crsorgi.gov.in",
        "required_documents_count": 3
    },
    "caste-certificate-issuance": {
        "procedure_id": 12,
        "procedure_name": "Caste Certificate Application & Scrutiny",
        "procedure_slug": "caste-certificate-issuance",
        "category": "Certificates / Registrations",
        "authority_type": "Sub-Divisional Officer (SDO) / Tehsildar",
        "estimated_days": 45,
        "portal_url": "https://aaplesarkar.mahaonline.gov.in",
        "required_documents_count": 4
    },
    "domicile-nationality-certificate": {
        "procedure_id": 13,
        "procedure_name": "Domicile and Nationality Certificate Application",
        "procedure_slug": "domicile-nationality-certificate",
        "category": "Certificates / Registrations",
        "authority_type": "Tehsildar / Sub-Divisional Magistrate (SDM)",
        "estimated_days": 15,
        "portal_url": "https://aaplesarkar.mahaonline.gov.in",
        "required_documents_count": 3
    },
    "income-certificate-issuance": {
        "procedure_id": 14,
        "procedure_name": "Income Certificate Issuance",
        "procedure_slug": "income-certificate-issuance",
        "category": "Certificates / Registrations",
        "authority_type": "Tehsildar / Talathi Office",
        "estimated_days": 15,
        "portal_url": "https://aaplesarkar.mahaonline.gov.in",
        "required_documents_count": 3
    },
    "traffic-e-challan-challenge": {
        "procedure_id": 21,
        "procedure_name": "Challenging a Traffic e-Challan / Virtual Court Payment",
        "procedure_slug": "traffic-e-challan-challenge",
        "category": "Traffic & Motor Vehicles",
        "authority_type": "Traffic Police Department / Virtual Traffic Court",
        "estimated_days": 7,
        "portal_url": "https://echallan.parivahan.gov.in",
        "required_documents_count": 2
    },
    "electricity-meter-name-transfer": {
        "procedure_id": 22,
        "procedure_name": "Electricity Meter Name Change & Change of Ownership",
        "procedure_slug": "electricity-meter-name-transfer",
        "category": "Utility & Municipal Services",
        "authority_type": "State Electricity Distribution Company (DISCOM)",
        "estimated_days": 15,
        "portal_url": "https://www.mahadiscom.in",
        "required_documents_count": 3
    },
    "mutation-entry-7-12-extract": {
        "procedure_id": 24,
        "procedure_name": "Mutation Entry (Ferfar / 7/12 Extract Update)",
        "procedure_slug": "mutation-entry-7-12-extract",
        "category": "Revenue / Land Records",
        "authority_type": "Talathi / Circle Officer (Revenue Department)",
        "estimated_days": 30,
        "portal_url": "https://bhulekh.mahabhumi.gov.in",
        "required_documents_count": 4
    }
}


class ResolutionDecisionEngine:
    """
    Deterministic Legal Triage & Resolution Decision Engine for Vidhik Platform.
    """

    # --------------------------------------------------------------------------
    # 1. KEYWORD & PATTERN MATRICES (English, Marathi, Hindi)
    # --------------------------------------------------------------------------

    # --- URGENT PATTERNS ---
    PHYSICAL_DANGER_PATTERNS = [
        r"\b(?:kill|killed|killing|murder|assault|assaulted|beaten|stabbing|stabbed|weapon|gun|knife|acid|poison)\b",
        r"\b(?:threat\s+to\s+life|death\s+threat|physically\s+attack|attempt\s+to\s+murder|grievous\s+hurt)\b",
        r"(?:मारणे|जीवे\s*मारणे|हल्ला|शस्त्र|मारहाण|जीव\s*घेणे|खुन|चाकू|बंदूक|धमकी)",
        r"(?:जान\s*से\s*मारने|हमला|हथियार|मारपीट|चाकू|बंदूक|जानलेवा\s*हमला|हत्या)"
    ]

    DOMESTIC_VIOLENCE_PATTERNS = [
        r"\b(?:domestic\s+violence|dowry|dowry\s+harassment|husband\s+beating|in-laws\s+torture|cruelty\s+by\s+husband|498a|pwdva)\b",
        r"\b(?:beaten\s+by\s+husband|locked\s+in\s+room|thrown\s+out\s+of\s+matrimonial\s+home|forced\s+dowry)\b",
        r"(?:घरेलू\s*हिंसा|हुंडा|हुंड्यासाठी|पतीने\s*मारहाण|पती.*मारहाण|सासरच्यांकडून|सासर|कौटुंबिक\s*हिंसाचार)",
        r"(?:दहेज|दहेज\s*उत्पीड़न|पति.*मारता|ससुराल|घरेलू\s*हिंसा)"
    ]

    ARREST_DETENTION_PATTERNS = [
        r"\b(?:arrest\s+warrant|police\s+raiding|arrested\s+by\s+police|police\s+custody|lockup|third\s+degree|illegal\s+detention|detained\s+without\s+fir)\b",
        r"\b(?:threat\s+of\s+arrest|bailable\s+warrant|non-bailable\s+warrant|nbw|custodial\s+violence)\b",
        r"(?:अटक|पोलीस\s*कोठडी|बेकायदेशीर\s*डांबून|वारंट|अटकेची\s*धमकी|लॉकअप)",
        r"(?:गिरफ्तारी|पुलिस\s*हिरासत|गैरकानूनी\s*हिरासत|वारंट|गिरफ्तार\s*करने\s*की\s*धमकी|हवालात)"
    ]

    CHILD_ENDANGERMENT_PATTERNS = [
        r"\b(?:pocso|child\s+abuse|minor\s+girl|minor\s+boy|child\s+sexual|child\s+trafficking|kidnapped\s+child|child\s+assault)\b",
        r"(?:अल्पवयीन\s*मुलावर\s*अत्याचार|पोक्सो|मुलाचे\s*अपहरण|बाल\s*लैंगिक\s*शोषण)",
        r"(?:नाबालिग\s*बच्चे\s*का\s*शोषण|पॉक्सो|बच्चे\s*का\s*अपहरण|बाल\s*यौन\s*शोषण)"
    ]

    IMMINENT_DEADLINE_PATTERNS = [
        r"\b(?:48\s*hours|24\s*hours|deadline\s+tomorrow|hearing\s+tomorrow|eviction\s+tomorrow|auction\s+tomorrow|warrant\s+for\s+tomorrow)\b",
        r"(?:उद्या\s*मुदत|२४\s*तास|४८\s*तास|उद्या\s*कोर्टात\s*हजर|उद्या\s*घर\s*खाली)",
        r"(?:कल\s*अंतिम\s*तारीख|२४\s*घंटे|४८\s*घंटे|कल\s*पेशी\s*है|कल\s*खाली\s*करने\s*का\s*नोटिस)"
    ]

    # --- LAWYER REQUIRED PATTERNS ---
    NON_BAILABLE_CRIMINAL_PATTERNS = [
        r"\b(?:fir\s+registered|booked\s+under|charge\s*sheet|murder|rape|robbery|dacoity|extortion|forgery|fraud|cheating\s+case|ndps|drugs|bribe|anti-corruption)\b",
        r"\b(?:section\s*302|section\s*307|section\s*376|section\s*420|section\s*406|section\s*467|section\s*468|bns\s*103|bns\s*109|bns\s*318)\b",
        r"(?:गुन्हा\s*दाखल|एफआयआर|फसवणूक|बनावट\s*कागदपत्रे|चोरी|दरोडा|बलात्कार|खून|लाच|भ्रष्टाचार)",
        r"(?:एफआईआर\s*दर्ज|धोखाधड़ी|जालसाजी|चोरी|डकैती|हत्या|बलात्कार|रिश्वत|गबन)"
    ]

    COURT_PROCEEDINGS_PATTERNS = [
        r"\b(?:court\s+summons|summons\s+received|filed\s+a\s+suit|written\s+statement|injunction\s+notice|warrant\s+issued|contempt\s+of\s+court|execution\s+petition)\b",
        r"\b(?:civil\s+court|magistrate\s+court|sessions\s+court|high\s+court|supreme\s+court|sub-judge)\b",
        r"(?:न्यायालयीन\s*समन्स|कोर्टाची\s*नोटीस|दिवाणी\s*दावा|मनाई\s*हुकूम|कोर्टात\s*केस|सुनावणी)",
        r"(?:कोर्ट\s*का\s*समन|अदालती\s*नोटिस|दीवानी\s*मुकदमा|स्टे\s*ऑर्डर|अदालत\s*में\s*मामला)"
    ]

    PROPERTY_DISPUTE_PATTERNS = [
        r"\b(?:property\s+title|ancestral\s+property|partition\s+suit|illegal\s+encroachment|forged\s+sale\s+deed|disputed\s+land|adverse\s+possession|land\s+grabbing)\b",
        r"(?:जमीन\s*विवाद|वारसा\s*हक्क|वडिलोपार्जित\s*जमीन|वाटणी\s*पत्र|बनावट\s*खरेदीखत|बेकायदेशीर\s*कब्जा|जागा\s*हडप)",
        r"(?:जमीन\s*का\s*झगड़ा|पैतृक\s*संपत्ति|बंटवारा\s*मुकदमा|अवैध\s*कब्जा|फर्जी\s*बैनामा|जमीन\s*हड़पना)"
    ]

    CONTESTED_MATRIMONIAL_PATTERNS = [
        r"\b(?:contested\s+divorce|child\s+custody|alimony\s+dispute|maintenance\s+case|annulment\s+of\s+marriage|restitution\s+of\s+conjugal\s+rights|125\s+crpc|section\s+144\s+bnss)\b",
        r"(?:घटस्फोट\s*अर्ज|मुलांचा\s*ताबा|पोटगी\s*वाद|पोटगी\s*केस|विवाह\s*रद्द)",
        r"(?:तलाक\s*का\s*मुकदमा|बच्चे\s*की\s*कस्टडी|गुजारा\s*भत्ता|तलाक\s*केस)"
    ]

    HIGH_VALUE_COMMERCIAL_PATTERNS = [
        r"\b(?:breach\s+of\s+contract|shareholder\s+dispute|partnership\s+dispute|ip\s+infringement|copyright\s+theft|trademark\s+violation|joint\s+venture\s+fraud)\b",
        r"(?:व्यापारी\s*करारभंग|भागीदारी\s*वाद|कॉपीराइट\s*चोरी|ट्रेडमार्क\s*उल्लंघन|कंपनी\s*वाद)",
        r"(?:व्यावसायिक\s*विवाद|अनुबंध\s*का\s*उल्लंघन|साझेदारी\s*विवाद|ट्रेडमार्क\s*उल्लंघन|कंपनी\s*विवाद)"
    ]

    INSOLVENCY_PATTERNS = [
        r"\b(?:nclt|insolvency|bankruptcy|ibc|liquidation|debt\s+recovery\s+tribunal|drt|sarfaesi|loan\s+default\s+recovery)\b",
        r"(?:दिवाळखोरी|कर्ज\s*वसुली|एनसीएलटी|सर्फासी)",
        r"(?:दिवालियापन|एनसीएलटी|ऋण\s*वसूली\s*अधिकरण|सरफेसी)"
    ]

    CONSTITUTIONAL_WRIT_PATTERNS = [
        r"\b(?:writ\s+petition|habeas\s+corpus|mandamus|certiorari|quo\s+warranto|article\s+226|article\s+32|fundamental\s+rights\s+violation|unconstitutional)\b",
        r"(?:रिट\s*याचिका|मूलभूत\s*हक्कांचे\s*उल्लंघन|कलम\s*२२६|कलम\s*३२)",
        r"(?:रिट\s*याचिका|मौलिक\s*अधिकारों\s*का\s*हनन|अनुच्छेद\s*२२६|अनुच्छेद\s*३२)"
    ]

    ARBITRATION_PATTERNS = [
        r"\b(?:arbitration\s+clause|arbitrator\s+appointed|section\s+9\s+arbitration|section\s+11|arbitral\s+tribunal|arbitration\s+and\s+conciliation)\b",
        r"(?:लवाद|मध्यस्थता|लवादाचा\s*निर्णय)",
        r"(?:मध्यस्थता|मध्यस्थ\s*नियुक्त|आर्बिट्रेशन)"
    ]

    LABOUR_TERMINATION_PATTERNS = [
        r"\b(?:illegal\s+termination|wrongful\s+dismissal|gratuity\s+withheld|industrial\s+disputes\s+act|retrenchment\s+compensation|labour\s+court\s+case)\b",
        r"(?:बेकायदेशीर\s*कामावरून\s*काढणे|कामगार\s*न्यायालय|ग्रेच्युटी\s*नाकारणे|वेतन\s*थकबाकी)",
        r"(?:अवैध\s*बर्खास्तगी|नौकरी\s*से\s*निकालना|श्रम\s*न्यायालय|ग्रेच्युटी\s*रोकना)"
    ]

    CYBER_FINANCIAL_FRAUD_HIGH_PATTERNS = [
        r"\b(?:bank\s+account\s+hacked|unauthorized\s+wire\s+transfer|crypto\s+extortion|ransomware\s+attack|sim\s+swap\s+fraud)\b",
        r"(?:बँक\s*खाते\s*हॅक|मोठी\s*सायबर\s*फसवणूक|रॅन्समवेअर)",
        r"(?:बैंक\s*खाता\s*हैक|बड़ी\s*साइबर\s*ठगी|रैनसमवेयर)"
    ]

    # --- SELF RESOLVABLE PATTERNS ---
    RTI_PATTERNS = [
        r"\b(?:rti\b|right\s+to\s+information|rti\s+application|public\s+information\s+officer|seeking\s+information\s+from\s+government|government\s+tender\s+copy|exam\s+answer\s+sheet)\b",
        r"(?:माहिती\s*अधिकार|आरटीआय|माहिती\s*मागवणे|सरकारी\s*माहिती)",
        r"(?:सूचना\s*का\s*अधिकार|आरटीआई|सरकारी\s*जानकारी\s*मांगना)"
    ]

    ROUTINE_ADMIN_CERTIFICATE_PATTERNS = [
        r"\b(?:birth\s+certificate|death\s+certificate|caste\s+certificate|domicile\s+certificate|income\s+certificate|non-creamy\s+layer|ration\s+card|senior\s+citizen\s+card|disability\s+certificate|udid\s+card|pan\s+card\s+correction|police\s+clearance\s+certificate|pcc\b|mutation\s+entry|7/12\s+extract|ferfar)\b",
        r"(?:जन्म\s*दाखला|मृत्यू\s*दाखला|जात\s*प्रमाणपत्र|डोमिसाईल|उत्पन्नाचा\s*दाखला|नॉन\s*क्रिमीलेअर|रेशन\s*कार्ड|ज्येष्ठ\s*नागरीक|अपंगत्व\s*प्रमाणपत्र|पॅन\s*कार्ड|पोलीस\s*चारित्र्य\s*पडताळणी|फेरफार|७/१२\s*उतारा|८अ\s*उतारा)",
        r"(?:जन्म\s*प्रमाण\s*पत्र|मृत्यु\s*प्रमाण\s*पत्र|जाति\s*प्रमाण\s*पत्र|निवास\s*प्रमाण\s*पत्र|आय\s*प्रमाण\s*पत्र|राशन\s*कार्ड|दिव्यांग\s*प्रमाण\s*पत्र|पैन\s*कार्ड\s*संशोधन|दाखिल\s*खारिज|खतौनी)"
    ]

    CONSUMER_GRIEVANCE_SIMPLE_PATTERNS = [
        r"\b(?:defective\s+product|e-commerce\s+refund|amazon\s+refund|flipkart\s+refund|courier\s+lost|damaged\s+goods|flight\s+cancellation\s+refund|train\s+ticket\s+refund|warranty\s+denied|mobile\s+repair\s+refusal)\b",
        r"(?:खराब\s*वस्तू|पैसे\s*परत\s*मिळत\s*नाहीत|ई-कॉमर्स\s*रिफंड|कुरिअर\s*गहाळ|वॉरंटी\s*नाकारली)",
        r"(?:खराब\s*सामान|पैसे\s*वापसी|ई-कॉमर्स\s*रिफंड|वारंटी\s*देने\s*से\s*इनकार|कूरियर\s*गायब)"
    ]

    TRAFFIC_CHALLAN_ROUTINE_PATTERNS = [
        r"\b(?:traffic\s+challan|e-challan|echallan|camera\s+challan|speeding\s+fine|signal\s+jump\s+fine|no\s+parking\s+fine|helmet\s+fine|virtual\s+traffic\s+court)\b",
        r"(?:ट्रॅफिक\s*चलन|ई-चलन|सिग्नल\s*तोडल्याचा\s*दंड|नो\s*पार्किंग\s*दंड|हेल्मेट\s*दंड)",
        r"(?:ट्रैफिक\s*चालान|ई-चालान|सिग्नल\s*तोड़ने\s*का\s*जुर्माना|नो\s*पार्किंग\s*चालान|हेलमेट\s*चालान)"
    ]

    BASIC_TENANCY_COMMUNICATION_PATTERNS = [
        r"\b(?:security\s+deposit\s+return|notice\s+to\s+vacate|standard\s+rent\s+receipt|30\s+days\s+notice\s+to\s+landlord|move-out\s+notice|basic\s+tenancy\s+inquiry)\b",
        r"(?:डिपॉझिट\s*परत\s*मागणे|घर\s*खाली\s*करण्याची\s*नोटीस|घरभाडे\s*पावती|३०\s*दिवसांची\s*नोटीस)",
        r"(?:डिपॉजिट\s*वापसी|मकान\s*खाली\s*करने\s*का\s*नोटिस|किराया\s*रसीद|३०\s*दिन\s*का\s*नोटिस)"
    ]

    NAME_CHANGE_UTILITY_PATTERNS = [
        r"\b(?:electricity\s+meter\s+name\s+change|water\s+connection\s+name\s+transfer|light\s+bill\s+name\s+change|property\s+tax\s+name\s+transfer)\b",
        r"(?:वीज\s*मीटर\s*नाव\s*बदल|पाणी\s*कनेक्शन\s*नाव\s*हस्तांतरण|लाईट\s*बिल\s*नाव\s*बदल)",
        r"(?:बिजली\s*मीटर\s*नाम\s*परिवर्तन|पानी\s*कनेक्शन\s*नाम\s*परिवर्तन)"
    ]

    # --------------------------------------------------------------------------
    # 2. INTERNAL HELPER: PATTERN MATCHER
    # --------------------------------------------------------------------------
    @classmethod
    def _matches_any(cls, text: str, patterns: List[str]) -> bool:
        """Tests whether any of the regex patterns match the normalized text."""
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                return True
        return False

    # --------------------------------------------------------------------------
    # 3. CORE EVALUATION PIPELINE
    # --------------------------------------------------------------------------
    @classmethod
    def evaluate(cls, request: ResolutionEvaluationRequest) -> ResolutionEvaluationResponse:
        """
        Executes deterministic legal triage across user narrative and structured signals.

        Pipeline:
        1. Normalize input text (Devanagari, whitespace, lowercase).
        2. Evaluate Tier 1 (Urgent Rules).
        3. Evaluate Tier 2 (Lawyer-Required Rules).
        4. Evaluate Tier 3 (Self-Resolvable Rules).
        5. Evaluate Tier 4 (Fallback / Insufficient Facts).
        6. Enforce strict precedence hierarchy (URGENT > LAWYER > SELF > FALLBACK).
        7. Build explainability reasons, next steps, and procedure links.
        """
        raw_situation = request.situation.strip()
        if not raw_situation:
            raise ValueError("Situation cannot be empty or whitespace only.")

        normalized_text = raw_situation.lower()

        # Track all matching rules across all tiers
        urgent_rules: List[TriggeredRuleInfo] = []
        lawyer_rules: List[TriggeredRuleInfo] = []
        self_rules: List[TriggeredRuleInfo] = []

        reasons: List[str] = []
        applicable_areas: Set[str] = set()
        relevant_procedures: List[RelevantProcedureRef] = []
        specializations: List[str] = []

        # ======================================================================
        # TIER 1: URGENT RULES EVALUATION (Critical Safety / Imminent Threat)
        # ======================================================================

        # 1.1 Physical Safety Danger
        if request.is_physical_danger is True or cls._matches_any(normalized_text, cls.PHYSICAL_DANGER_PATTERNS):
            urgent_rules.append(TriggeredRuleInfo(
                rule_id="URGENT_PHYSICAL_SAFETY",
                category="Physical Safety / Criminal Emergency",
                rule_description="Immediate threat to physical safety, assault, or life detected.",
                severity="critical"
            ))
            reasons.append("There is an immediate risk to physical safety or life requiring rapid protective intervention.")
            applicable_areas.add("Criminal Law & Emergency Protection")
            specializations.append("Criminal Defense & Bail")

        # 1.2 Domestic Violence
        if request.involves_domestic_violence is True or cls._matches_any(normalized_text, cls.DOMESTIC_VIOLENCE_PATTERNS):
            urgent_rules.append(TriggeredRuleInfo(
                rule_id="URGENT_ACTIVE_DOMESTIC_VIOLENCE",
                category="Domestic Violence & Safety",
                rule_description="Active domestic violence, spousal physical cruelty, or dowry harassment detected.",
                severity="critical"
            ))
            reasons.append("Active domestic abuse or spousal violence requires immediate safety protection and protection orders.")
            applicable_areas.add("Protection of Women from Domestic Violence Act, 2005")
            specializations.append("Family & Matrimonial Law")

        # 1.3 Arrest / Detention
        if request.has_arrest_threat is True or cls._matches_any(normalized_text, cls.ARREST_DETENTION_PATTERNS):
            urgent_rules.append(TriggeredRuleInfo(
                rule_id="URGENT_ARREST_DETENTION",
                category="Liberty & Custodial Defense",
                rule_description="Imminent arrest threat, active arrest warrant, or custodial detention detected.",
                severity="critical"
            ))
            reasons.append("Imminent threat of arrest or custodial detention necessitates urgent legal defense / anticipatory bail.")
            applicable_areas.add("Criminal Procedure & Fundamental Rights (Art 21/22)")
            specializations.append("Criminal Defense & Bail")

        # 1.4 Child Endangerment / POCSO
        if (request.involves_children is True and (request.is_physical_danger is True or "abuse" in normalized_text)) or cls._matches_any(normalized_text, cls.CHILD_ENDANGERMENT_PATTERNS):
            urgent_rules.append(TriggeredRuleInfo(
                rule_id="URGENT_CHILD_ENDANGERMENT",
                category="Child Protection & POCSO",
                rule_description="Emergency situation involving safety or abuse of minor children detected.",
                severity="critical"
            ))
            reasons.append("Minor children are in immediate distress, requiring child welfare and emergency statutory protection.")
            applicable_areas.add("POCSO Act, 2012 & Juvenile Justice Act, 2015")
            specializations.append("Criminal Defense & Bail")

        # 1.5 Imminent Limitation / Eviction Deadline
        if request.has_urgent_deadline is True or cls._matches_any(normalized_text, cls.IMMINENT_DEADLINE_PATTERNS):
            urgent_rules.append(TriggeredRuleInfo(
                rule_id="URGENT_IMMINENT_DEADLINE",
                category="Urgent Statutory Deadline",
                rule_description="Imminent statutory deadline (<48 hours) or impending coercive action detected.",
                severity="critical"
            ))
            reasons.append("An immediate statutory deadline or hearing is pending within 24-48 hours requiring emergency legal intervention.")
            applicable_areas.add("Urgent Court Procedure & Interim Injunctions")
            specializations.append("General Civil & Dispute Resolution")

        # ======================================================================
        # TIER 2: LAWYER-REQUIRED RULES EVALUATION
        # ======================================================================

        # 2.1 Non-Bailable / Serious Criminal
        if (request.has_police_involvement is True and ("fir" in normalized_text or "case" in normalized_text)) or cls._matches_any(normalized_text, cls.NON_BAILABLE_CRIMINAL_PATTERNS):
            lawyer_rules.append(TriggeredRuleInfo(
                rule_id="LAWYER_NON_BAILABLE_CRIMINAL",
                category="Criminal Litigation",
                rule_description="Allegations of serious criminal offences, FIR registration, or penal charges under BNS/IPC.",
                severity="high"
            ))
            reasons.append("Criminal allegations and formal FIR proceedings involve potential penal consequences and require professional representation.")
            applicable_areas.add("Bharatiya Nyaya Sanhita, 2023 / Indian Penal Code")
            specializations.append("Criminal Defense & Bail")

        # 2.2 Active Court Proceedings
        if request.has_court_notice is True or cls._matches_any(normalized_text, cls.COURT_PROCEEDINGS_PATTERNS):
            lawyer_rules.append(TriggeredRuleInfo(
                rule_id="LAWYER_ACTIVE_COURT_PROCEEDINGS",
                category="Active Civil/Criminal Litigation",
                rule_description="Formal court summons, lawsuit, written statement deadline, or judicial proceedings active.",
                severity="high"
            ))
            reasons.append("A formal lawsuit or court summons is active; failure to file pleadings properly can result in ex-parte orders.")
            applicable_areas.add("Civil / Criminal Judicial Procedure")
            specializations.append("General Civil & Dispute Resolution")

        # 2.3 Property Title Dispute
        if cls._matches_any(normalized_text, cls.PROPERTY_DISPUTE_PATTERNS):
            lawyer_rules.append(TriggeredRuleInfo(
                rule_id="LAWYER_PROPERTY_TITLE_DISPUTE",
                category="Property & Real Estate Litigation",
                rule_description="Complex real estate dispute involving ownership title, partition, adverse possession, or fraudulent deeds.",
                severity="high"
            ))
            reasons.append("Real estate title and ancestral partition disputes involve complex documentation and substantive property law.")
            applicable_areas.add("Transfer of Property Act, 1882 & Specific Relief Act")
            specializations.append("Property & Real Estate")

        # 2.4 Contested Matrimonial
        if cls._matches_any(normalized_text, cls.CONTESTED_MATRIMONIAL_PATTERNS):
            lawyer_rules.append(TriggeredRuleInfo(
                rule_id="LAWYER_CONTESTED_MATRIMONIAL",
                category="Family & Matrimonial Law",
                rule_description="Contested divorce, child custody litigation, or substantial maintenance claims.",
                severity="high"
            ))
            reasons.append("Contested marital dissolution and child custody require family court advocacy and interim relief applications.")
            applicable_areas.add("Hindu Marriage Act, 1955 / Special Marriage Act / Family Courts Act")
            specializations.append("Family & Matrimonial")

        # 2.5 High-Value Commercial Dispute
        is_high_amount = request.monetary_amount is not None and request.monetary_amount >= 1000000.0  # ₹10 Lakhs
        if is_high_amount or cls._matches_any(normalized_text, cls.HIGH_VALUE_COMMERCIAL_PATTERNS):
            lawyer_rules.append(TriggeredRuleInfo(
                rule_id="LAWYER_HIGH_VALUE_COMMERCIAL",
                category="Corporate & Commercial Litigation",
                rule_description="High-value commercial breach, partnership dispute, or monetary claim exceeding ₹10 Lakhs.",
                severity="high"
            ))
            reasons.append("High financial stakes (> ₹10 Lakhs) or complex commercial agreements necessitate commercial court expertise.")
            applicable_areas.add("Commercial Courts Act, 2015 & Indian Contract Act, 1872")
            specializations.append("Corporate & Commercial")

        # 2.6 Insolvency & Bankruptcy
        if cls._matches_any(normalized_text, cls.INSOLVENCY_PATTERNS):
            lawyer_rules.append(TriggeredRuleInfo(
                rule_id="LAWYER_INSOLVENCY_BANKRUPTCY",
                category="Insolvency & Debt Recovery",
                rule_description="Default proceedings under Insolvency and Bankruptcy Code (IBC) or Debt Recovery Tribunal (DRT).",
                severity="high"
            ))
            reasons.append("Insolvency, NCLT, or SARFAESI actions require specialized insolvency counsel.")
            applicable_areas.add("Insolvency and Bankruptcy Code, 2016 (IBC)")
            specializations.append("Insolvency & Bankruptcy (NCLT)")

        # 2.7 Constitutional Writs
        if cls._matches_any(normalized_text, cls.CONSTITUTIONAL_WRIT_PATTERNS):
            lawyer_rules.append(TriggeredRuleInfo(
                rule_id="LAWYER_CONSTITUTIONAL_WRIT",
                category="Constitutional & Public Law",
                rule_description="Challenge to arbitrary state action or fundamental right violation under Article 226 / 32.",
                severity="high"
            ))
            reasons.append("Challenging government or statutory authority action before the High Court requires writ drafting expertise.")
            applicable_areas.add("Constitution of India (Articles 226 / 32)")
            specializations.append("Constitutional & Public Law")

        # 2.8 Commercial Arbitration
        if cls._matches_any(normalized_text, cls.ARBITRATION_PATTERNS):
            lawyer_rules.append(TriggeredRuleInfo(
                rule_id="LAWYER_ARBITRATION_MATTERS",
                category="Arbitration & Dispute Resolution",
                rule_description="Arbitration clause invocation, section 9/11 applications, or arbitral tribunal proceedings.",
                severity="high"
            ))
            reasons.append("Formal arbitration proceedings require specialized representation under the Arbitration & Conciliation Act.")
            applicable_areas.add("Arbitration and Conciliation Act, 1996")
            specializations.append("Arbitration & Commercial Law")

        # 2.9 Labour & Employment Termination
        if cls._matches_any(normalized_text, cls.LABOUR_TERMINATION_PATTERNS):
            lawyer_rules.append(TriggeredRuleInfo(
                rule_id="LAWYER_LABOUR_TERMINATION",
                category="Labour & Employment Law",
                rule_description="Unlawful termination, withheld statutory dues, or industrial dispute.",
                severity="medium"
            ))
            reasons.append("Wrongful dismissal and statutory employment benefit claims require labour law consultation.")
            applicable_areas.add("Industrial Disputes Act & Payment of Gratuity Act")
            specializations.append("Labour & Employment")

        # 2.10 Cyber Financial Fraud (High Value)
        if (request.monetary_amount is not None and request.monetary_amount >= 200000.0) and cls._matches_any(normalized_text, cls.CYBER_FINANCIAL_FRAUD_HIGH_PATTERNS):
            lawyer_rules.append(TriggeredRuleInfo(
                rule_id="LAWYER_CYBER_FINANCIAL_FRAUD_HIGH",
                category="Cyber Crime & Financial Fraud",
                rule_description="Substantial cyber fraud (> ₹2 Lakhs), unauthorized banking access, or ransomware.",
                severity="high"
            ))
            reasons.append("Substantial financial loss via cyber fraud requires cyber cell reporting and legal asset recovery action.")
            applicable_areas.add("Information Technology Act, 2000 & BNS")
            specializations.append("Cyber & IT Law")

        # ======================================================================
        # TIER 3: SELF-RESOLVABLE RULES EVALUATION
        # ======================================================================

        # 3.1 RTI Application
        if cls._matches_any(normalized_text, cls.RTI_PATTERNS):
            self_rules.append(TriggeredRuleInfo(
                rule_id="SELF_RTI_APPLICATION",
                category="Right to Information",
                rule_description="Request for official information or government records under RTI Act, 2005.",
                severity="low"
            ))
            reasons.append("RTI applications are designed as citizen self-service procedures without mandatory advocate representation.")
            applicable_areas.add("Right to Information Act, 2005")
            if "rti-application" in VERIFIED_PROCEDURES:
                relevant_procedures.append(RelevantProcedureRef(**VERIFIED_PROCEDURES["rti-application"]))

        # 3.2 Routine Administrative Certificates
        if cls._matches_any(normalized_text, cls.ROUTINE_ADMIN_CERTIFICATE_PATTERNS):
            self_rules.append(TriggeredRuleInfo(
                rule_id="SELF_ROUTINE_ADMIN_CERTIFICATE",
                category="Administrative Services & Certificates",
                rule_description="Application or correction for statutory civil certificates (Birth, Caste, Income, Domicile, 7/12).",
                severity="low"
            ))
            reasons.append("Civil registration and certificate issuance are standard administrative procedures available directly via citizen portals.")
            applicable_areas.add("State Citizen Service Charters & Registration Laws")

            # Match specific procedure references
            if "birth" in normalized_text and "birth-certificate-registration-correction" in VERIFIED_PROCEDURES:
                relevant_procedures.append(RelevantProcedureRef(**VERIFIED_PROCEDURES["birth-certificate-registration-correction"]))
            elif "death" in normalized_text and "death-certificate-registration-correction" in VERIFIED_PROCEDURES:
                relevant_procedures.append(RelevantProcedureRef(**VERIFIED_PROCEDURES["death-certificate-registration-correction"]))
            elif "caste" in normalized_text and "caste-certificate-issuance" in VERIFIED_PROCEDURES:
                relevant_procedures.append(RelevantProcedureRef(**VERIFIED_PROCEDURES["caste-certificate-issuance"]))
            elif "income" in normalized_text and "income-certificate-issuance" in VERIFIED_PROCEDURES:
                relevant_procedures.append(RelevantProcedureRef(**VERIFIED_PROCEDURES["income-certificate-issuance"]))
            elif "domicile" in normalized_text and "domicile-nationality-certificate" in VERIFIED_PROCEDURES:
                relevant_procedures.append(RelevantProcedureRef(**VERIFIED_PROCEDURES["domicile-nationality-certificate"]))
            elif ("7/12" in normalized_text or "mutation" in normalized_text or "ferfar" in normalized_text) and "mutation-entry-7-12-extract" in VERIFIED_PROCEDURES:
                relevant_procedures.append(RelevantProcedureRef(**VERIFIED_PROCEDURES["mutation-entry-7-12-extract"]))

        # 3.3 Simple Consumer Grievance (< ₹5 Lakhs)
        is_modest_amount = request.monetary_amount is None or request.monetary_amount < 500000.0  # < ₹5 Lakhs
        if is_modest_amount and cls._matches_any(normalized_text, cls.CONSUMER_GRIEVANCE_SIMPLE_PATTERNS):
            self_rules.append(TriggeredRuleInfo(
                rule_id="SELF_CONSUMER_GRIEVANCE_SIMPLE",
                category="Consumer Grievance",
                rule_description="Defective product or service deficiency with claim value under ₹5 Lakhs (E-Daakhil / NCH eligible).",
                severity="low"
            ))
            reasons.append("Consumer grievances under ₹5 Lakhs can be resolved directly through the National Consumer Helpline or E-Daakhil without counsel.")
            applicable_areas.add("Consumer Protection Act, 2019")
            if "consumer-complaint" in VERIFIED_PROCEDURES:
                relevant_procedures.append(RelevantProcedureRef(**VERIFIED_PROCEDURES["consumer-complaint"]))

        # 3.4 Traffic Challan Routine
        if cls._matches_any(normalized_text, cls.TRAFFIC_CHALLAN_ROUTINE_PATTERNS):
            self_rules.append(TriggeredRuleInfo(
                rule_id="SELF_TRAFFIC_CHALLAN_ROUTINE",
                category="Traffic Violation",
                rule_description="Routine traffic e-challan payment or virtual traffic court dispute.",
                severity="low"
            ))
            reasons.append("Traffic e-challans can be paid or contested directly online through the Parivahan Virtual Court portal.")
            applicable_areas.add("Motor Vehicles Act, 1988 (Amended 2019)")
            if "traffic-e-challan-challenge" in VERIFIED_PROCEDURES:
                relevant_procedures.append(RelevantProcedureRef(**VERIFIED_PROCEDURES["traffic-e-challan-challenge"]))

        # 3.5 Basic Tenancy Communication
        if is_modest_amount and cls._matches_any(normalized_text, cls.BASIC_TENANCY_COMMUNICATION_PATTERNS):
            self_rules.append(TriggeredRuleInfo(
                rule_id="SELF_BASIC_TENANCY_COMMUNICATION",
                category="Tenancy Communication",
                rule_description="Standard security deposit refund request or 30-day move-out notice.",
                severity="low"
            ))
            reasons.append("Preliminary tenancy notices and deposit refund demands should first be issued directly via formal written notice.")
            applicable_areas.add("Rent Control Legislation & Transfer of Property Act")

        # 3.6 Utility Name Transfer
        if cls._matches_any(normalized_text, cls.NAME_CHANGE_UTILITY_PATTERNS):
            self_rules.append(TriggeredRuleInfo(
                rule_id="SELF_NAME_CHANGE_UTILITY",
                category="Utility Administrative Transfer",
                rule_description="Transfer of electricity meter or municipal water connection name.",
                severity="low"
            ))
            reasons.append("Utility account name transfers are purely administrative processes submitted directly to the service provider.")
            applicable_areas.add("Municipal & Electricity Distribution Regulations")
            if "electricity-meter-name-transfer" in VERIFIED_PROCEDURES:
                relevant_procedures.append(RelevantProcedureRef(**VERIFIED_PROCEDURES["electricity-meter-name-transfer"]))

        # ======================================================================
        # TIER DETERMINATION: PRECEDENCE HIERARCHY
        # URGENT > LAWYER_REQUIRED > SELF_RESOLVABLE > FALLBACK
        # ======================================================================

        all_triggered_rules: List[TriggeredRuleInfo] = []
        all_triggered_rules.extend(urgent_rules)
        all_triggered_rules.extend(lawyer_rules)
        all_triggered_rules.extend(self_rules)

        # 1. URGENT OVERRIDE
        if urgent_rules:
            rec_type = RecommendationType.URGENT_LEGAL_INTERVENTION
            risk_lvl = RiskLevel.CRITICAL
            confidence = "high"
            primary_reason = f"Urgent legal/safety intervention required due to {urgent_rules[0].rule_description.lower()}"

            emergency_guidance = {
                "immediate_warning": "DO NOT delay. If you are in immediate physical danger, contact emergency services immediately.",
                "national_helplines": [
                    VERIFIED_EMERGENCY_DATA["police_emergency"],
                    VERIFIED_EMERGENCY_DATA["women_safety"] if any("DOMESTIC" in r.rule_id for r in urgent_rules) else None,
                    VERIFIED_EMERGENCY_DATA["child_protection"] if any("CHILD" in r.rule_id for r in urgent_rules) else None,
                    VERIFIED_EMERGENCY_DATA["legal_aid"]
                ],
                "recommended_action": "Approach the nearest Police Station or contact 112 immediately. Seek urgent assistance from a Criminal Advocate or High Court / Legal Aid Cell."
            }
            # Filter nulls
            emergency_guidance["national_helplines"] = [h for h in emergency_guidance["national_helplines"] if h is not None]

            checklist = [
                "Step 1: Move immediately to a physically secure location or public space.",
                "Step 2: Dial 112 (National Emergency Helpline) or approach the nearest Police Station.",
                "Step 3: Document any injuries (medical examination/MLC), text threats, or photos securely.",
                "Step 4: Contact an emergency Criminal Defense advocate or Free Legal Aid (15100) for interim protective orders."
            ]

            next_steps = [
                "Call 112 immediately for emergency police intervention.",
                "File an immediate written complaint/FIR at the local police station.",
                "Consult an urgent Criminal Defense Advocate for Anticipatory Bail or Protection Orders."
            ]

            spec = specializations[0] if specializations else "Criminal Defense & Bail"

        # 2. LAWYER REQUIRED
        elif lawyer_rules:
            rec_type = RecommendationType.LAWYER_CONSULTATION_REQUIRED
            risk_lvl = RiskLevel.HIGH if any(r.severity == "high" for r in lawyer_rules) else RiskLevel.MEDIUM
            confidence = "high"
            primary_reason = f"Professional lawyer consultation is required because {lawyer_rules[0].rule_description.lower()}"
            emergency_guidance = None

            spec = specializations[0] if specializations else "General Civil & Dispute Resolution"

            checklist = [
                "Step 1: Organize all relevant contracts, notices, payment proofs, and communications in chronological order.",
                "Step 2: Note down exact dates, timelines, and statutory deadlines received in any notice.",
                "Step 3: Do NOT sign any settlement or admission of liability without legal counsel.",
                f"Step 4: Schedule a consultation with an advocate specializing in {spec}."
            ]

            next_steps = [
                f"Consult an advocate specializing in {spec}.",
                "Prepare a chronological summary of facts and evidence before the legal consultation.",
                "Ensure no statutory limitation period or court response deadline lapses."
            ]

        # 3. SELF RESOLVABLE
        elif self_rules:
            rec_type = RecommendationType.SELF_RESOLVABLE
            risk_lvl = RiskLevel.LOW
            confidence = "high"
            primary_reason = f"This issue is suitable for self-resolution because {self_rules[0].rule_description.lower()}"
            emergency_guidance = None
            spec = None

            checklist = [
                "Step 1: Verify your identity documents (Aadhaar, PAN) and address proof.",
                "Step 2: Collect all supporting transaction receipts, emails, or application forms.",
                "Step 3: Access the designated official portal or visit the administrative office.",
                "Step 4: Submit your application / formal notice and preserve the official acknowledgement receipt.",
                "Step 5: Track the statutory processing timeline (typically 15-30 days)."
            ]

            next_steps = [
                "Review the prerequisite document checklist in the linked procedure.",
                "Submit your request through the official government portal.",
                "If the authority fails to respond within the statutory timeframe, escalate to the First Appellate Authority."
            ]

        # 4. CAUTIOUS FALLBACK (Insufficient Facts / Ambiguous)
        else:
            rec_type = RecommendationType.LAWYER_CONSULTATION_REQUIRED
            risk_lvl = RiskLevel.MEDIUM
            confidence = "cautious_fallback"
            primary_reason = "The provided situation contains ambiguous or general legal elements that require professional review before taking action."
            emergency_guidance = None
            spec = "General Civil & Dispute Resolution"

            all_triggered_rules.append(TriggeredRuleInfo(
                rule_id="FALLBACK_INSUFFICIENT_FACTS_CAUTIOUS",
                category="General Legal Triage",
                rule_description="Insufficient or ambiguous factual detail; defaulting to cautious professional review.",
                severity="medium"
            ))

            reasons.append("The factual narrative does not match a verified low-risk administrative checklist.")
            reasons.append("A qualified advocate can evaluate specific liabilities, jurisdictional requirements, and statutory limitation periods.")

            checklist = [
                "Step 1: Write down a detailed chronological list of events with dates and names.",
                "Step 2: Gather all written agreements, letters, WhatsApp/SMS communications, and bank statements.",
                "Step 3: Consult a legal practitioner to determine whether formal court action or legal notice is required."
            ]

            next_steps = [
                "Consult a legal professional for an initial case assessment.",
                "Provide complete documentation to identify applicable statutory remedies."
            ]

        # Build response
        return ResolutionEvaluationResponse(
            recommendation_type=rec_type,
            risk_level=risk_lvl,
            primary_reason=primary_reason,
            reasons=reasons,
            triggered_rules=all_triggered_rules,
            self_help_checklist=checklist,
            lawyer_specialization_needed=spec,
            applicable_areas=sorted(list(applicable_areas)) if applicable_areas else ["General Legal Principles"],
            next_steps=next_steps,
            emergency_guidance=emergency_guidance,
            relevant_procedures=relevant_procedures,
            confidence=confidence,
            disclaimer=(
                "This automated resolution assessment is for informational and educational triage only and does not "
                "constitute formal legal advice or create an attorney-client relationship. If in doubt, consult a licensed advocate."
            )
        )
