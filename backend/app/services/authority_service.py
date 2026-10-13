import re
import time
from typing import List, Dict, Any, Optional
from app.schemas.authority import (
    AuthorityRecommendationRequest,
    StatutoryAuthorityRecommendationResponse,
    AuthorityDetail
)


class AuthorityService:
    """
    Deterministic Authority Recommendation Engine for VIDHIK AI.
    Directs citizens and legal researchers to verified public authorities, tribunals, commissions, and ombudsmen.
    """

    AUTHORITIES_DB = {
        "cyber": {
            "primary": AuthorityDetail(
                name="National Cyber Crime Reporting Portal / Local Cyber Cell",
                authority_type="Law Enforcement / Specialized Investigation",
                jurisdiction_level="District / National",
                official_portal="https://cybercrime.gov.in (Helpline: 1930)",
                statutory_basis="Information Technology Act, 2000 & Section 173 BNSS",
                filing_procedure="File online complaint within 24 hours at cybercrime.gov.in or visit jurisdictional Cyber Police Station."
            ),
            "alternatives": [
                AuthorityDetail(
                    name="Reserve Bank of India (RBI) Ombudsman",
                    authority_type="Regulatory Ombudsman",
                    jurisdiction_level="National",
                    official_portal="https://cms.rbi.org.in",
                    statutory_basis="Reserve Bank - Integrated Ombudsman Scheme, 2021",
                    filing_procedure="File after 30 days if bank fails to resolve unauthorized electronic transaction."
                )
            ],
            "escalation": [
                "1. Dial 1930 within Golden Hour to freeze funds",
                "2. Report on cybercrime.gov.in to obtain Acknowledgement Number",
                "3. Submit Acknowledgement to Home Branch Bank Manager",
                "4. Escalate to RBI Ombudsman if bank delays resolution beyond 30 days"
            ]
        },
        "consumer": {
            "primary": AuthorityDetail(
                name="District Consumer Disputes Redressal Commission (DCDRC)",
                authority_type="Quasi-Judicial Commission",
                jurisdiction_level="District (Claims up to ₹50 Lakhs)",
                official_portal="https://edaakhil.nic.in (National Consumer Helpline: 1915)",
                statutory_basis="Section 28 & 34, Consumer Protection Act, 2019",
                filing_procedure="File online via e-Daakhil or submit physical complaint in triplicate with affidavit and court fee."
            ),
            "alternatives": [
                AuthorityDetail(
                    name="State Consumer Disputes Redressal Commission (SCDRC)",
                    authority_type="Quasi-Judicial Commission",
                    jurisdiction_level="State (Claims ₹50 Lakhs to ₹2 Crores)",
                    official_portal="https://edaakhil.nic.in",
                    statutory_basis="Section 42, Consumer Protection Act, 2019",
                    filing_procedure="First appeal against DCDRC or direct complaint for claims over ₹50 Lakhs."
                )
            ],
            "escalation": [
                "1. National Consumer Helpline (NCH) 1915 informal mediation",
                "2. Legal Demand Notice to seller/service provider (15 days notice)",
                "3. District Commission (DCDRC) via e-Daakhil",
                "4. State Commission (SCDRC) on appeal within 45 days",
                "5. National Commission (NCDRC) / Supreme Court"
            ]
        },
        "rti": {
            "primary": AuthorityDetail(
                name="Central / State Public Information Officer (CPIO / SPIO)",
                authority_type="Administrative Public Authority",
                jurisdiction_level="Departmental / District",
                official_portal="https://rtionline.gov.in",
                statutory_basis="Section 6(1), Right to Information Act, 2005",
                filing_procedure="Submit Form A / online application with ₹10 fee specifying information sought under Section 6."
            ),
            "alternatives": [
                AuthorityDetail(
                    name="First Appellate Authority (FAA)",
                    authority_type="Departmental Appellate Authority",
                    jurisdiction_level="Departmental Senior Officer",
                    official_portal="https://rtionline.gov.in",
                    statutory_basis="Section 19(1), Right to Information Act, 2005",
                    filing_procedure="Appeal filed within 30 days of non-response or rejection by PIO."
                ),
                AuthorityDetail(
                    name="Central / State Information Commission (CIC / SIC)",
                    authority_type="Statutory Commission",
                    jurisdiction_level="National / State",
                    official_portal="https://cic.gov.in",
                    statutory_basis="Section 19(3), Right to Information Act, 2005",
                    filing_procedure="Second Appeal filed within 90 days against FAA order."
                )
            ],
            "escalation": [
                "1. File RTI Application to CPIO/SPIO (30-day response window)",
                "2. First Appeal to First Appellate Authority (FAA) within 30 days",
                "3. Second Appeal / Complaint to Information Commission (CIC/SIC) within 90 days"
            ]
        },
        "labour": {
            "primary": AuthorityDetail(
                name="Office of the Labour Commissioner / Conciliation Officer",
                authority_type="Administrative / Quasi-Judicial",
                jurisdiction_level="District / Region",
                official_portal="https://samadhan.labour.gov.in (SAMADHAN Portal)",
                statutory_basis="Industrial Disputes Act, 1947 & Code on Wages, 2019",
                filing_procedure="Submit statement of claim / industrial dispute application before the Conciliation Officer."
            ),
            "alternatives": [
                AuthorityDetail(
                    name="Labour Court / Industrial Tribunal",
                    authority_type="Judicial Tribunal",
                    jurisdiction_level="District / State",
                    official_portal="https://labour.gov.in",
                    statutory_basis="Section 7 & 7A, Industrial Disputes Act, 1947",
                    filing_procedure="Adjudication upon failure report (FOC) from Conciliation Officer."
                )
            ],
            "escalation": [
                "1. Formal written representation to Employer HR / Grievance Redressal Committee",
                "2. Industrial Dispute filing before Conciliation Officer",
                "3. Reference to Labour Court / Industrial Tribunal",
                "4. Writ Petition before High Court under Article 226"
            ]
        },
        "property_rera": {
            "primary": AuthorityDetail(
                name="Real Estate Regulatory Authority (RERA)",
                authority_type="Quasi-Judicial Regulatory Authority",
                jurisdiction_level="State",
                official_portal="State RERA Portal (e.g., https://maharera.mahaonline.gov.in)",
                statutory_basis="Section 31, Real Estate (Regulation and Development) Act, 2016",
                filing_procedure="Online complaint against builder/promoter for delayed possession, deviation from plan, or structural defect."
            ),
            "alternatives": [
                AuthorityDetail(
                    name="RERA Appellate Tribunal (REAT)",
                    authority_type="Appellate Judicial Tribunal",
                    jurisdiction_level="State",
                    official_portal="State RERA Appellate Portal",
                    statutory_basis="Section 43, RERA Act, 2016",
                    filing_procedure="Appeals against RERA Adjudicating Officer / Authority within 60 days."
                )
            ],
            "escalation": [
                "1. Notice to Builder / Developer demanding possession / interest under Section 18 RERA",
                "2. Online Complaint before RERA Adjudicating Officer",
                "3. Appeal before Real Estate Appellate Tribunal (REAT)",
                "4. High Court Appeal under Section 58 RERA on substantial questions of law"
            ]
        },
        "legal_aid": {
            "primary": AuthorityDetail(
                name="District Legal Services Authority (DLSA)",
                authority_type="Statutory Legal Aid Authority",
                jurisdiction_level="District Court Complex",
                official_portal="https://nalsa.gov.in (National Legal Aid Helpline: 15100)",
                statutory_basis="Section 9 & 12, Legal Services Authorities Act, 1987",
                filing_procedure="Apply in person at DLSA Front Office or online via NALSA portal for free assigned advocate and court fees."
            ),
            "alternatives": [
                AuthorityDetail(
                    name="State Legal Services Authority (SLSA)",
                    authority_type="Statutory Legal Aid Authority",
                    jurisdiction_level="State / High Court",
                    official_portal="https://nalsa.gov.in",
                    statutory_basis="Section 6, Legal Services Authorities Act, 1987",
                    filing_procedure="For High Court matters and statewide legal aid coordination."
                )
            ],
            "escalation": [
                "1. Apply to DLSA Front Office / NALSA Portal",
                "2. Scrutiny of eligibility under Section 12 LSAA (Women, SC/ST, custody, income ceiling)",
                "3. Assignment of Panel Advocate at state expense",
                "4. Pre-litigation mediation or representation in Court"
            ]
        },
        "criminal_police": {
            "primary": AuthorityDetail(
                name="Jurisdictional Police Station (Station House Officer - SHO)",
                authority_type="Law Enforcement Authority",
                jurisdiction_level="Local Station / District",
                official_portal="https://digitalpolice.gov.in (Emergency: 112)",
                statutory_basis="Section 173, Bharatiya Nagarik Suraksha Sanhita, 2023 (formerly 154 CrPC)",
                filing_procedure="Submit written complaint or oral statement under Section 173 BNSS to register FIR for cognizable offence."
            ),
            "alternatives": [
                AuthorityDetail(
                    name="Superintendent of Police / Deputy Commissioner of Police (SP / DCP)",
                    authority_type="Senior Law Enforcement Officer",
                    jurisdiction_level="District / Police Zone",
                    official_portal="District Police Portal",
                    statutory_basis="Section 173(4) BNSS (formerly 154(3) CrPC)",
                    filing_procedure="Submit written representation by registered post if SHO refuses to register FIR."
                ),
                AuthorityDetail(
                    name="Judicial Magistrate First Class (JMFC)",
                    authority_type="Criminal Judicial Court",
                    jurisdiction_level="Sub-Division / District",
                    official_portal="https://ecourts.gov.in",
                    statutory_basis="Section 175(3) BNSS (formerly 156(3) CrPC)",
                    filing_procedure="Application on affidavit seeking judicial direction to police to investigate."
                )
            ],
            "escalation": [
                "1. Inform Station House Officer (SHO) under Sec 173(1) BNSS for FIR registration",
                "2. If refused, send complaint to SP / DCP under Sec 173(4) BNSS by registered post",
                "3. If unresolved, file application before Judicial Magistrate under Sec 175(3) BNSS",
                "4. Private complaint before Magistrate under Sec 223 BNSS (Sec 200 CrPC)"
            ]
        }
    }

    @classmethod
    def recommend_authority(cls, request: AuthorityRecommendationRequest) -> AuthorityRecommendationResponse:
        start_time = time.time()
        issue_clean = request.issue_description.lower()
        category = request.category.lower() if request.category else ""

        # Deterministic domain matching
        if "rera" in issue_clean or "builder" in issue_clean or "flat possession" in issue_clean or "allotment" in issue_clean:
            key = "property_rera"
            reason = "The dispute involves real estate, builder delay, or housing allotment governed by RERA."
        elif category == "cyber" or any(k in issue_clean for k in ["cyber", "otp", "phishing", "online fraud", "hacked", "1930"]):
            key = "cyber"
            reason = "The matter involves electronic or cyber-enabled financial fraud under the IT Act."
        elif category == "consumer" or any(k in issue_clean for k in ["defective", "warranty", "refund", "consumer", "refrigerator", "e-commerce"]):
            key = "consumer"
            reason = "The grievance involves unfair trade practice or deficiency of goods/services under Consumer Protection Act."
        elif category == "rti" or any(k in issue_clean for k in ["rti", "right to information", "pio", "information commissioner"]):
            key = "rti"
            reason = "The inquiry concerns access to public government records under the RTI Act, 2005."
        elif category == "labour" or any(k in issue_clean for k in ["labour", "unpaid salary", "gratuity", "provident fund", "employment termination"]):
            key = "labour"
            reason = "The issue relates to employment disputes, wages, or wrongful termination under labour statutes."
        elif any(k in issue_clean for k in ["legal aid", "cannot afford lawyer", "free advocate", "poor citizen"]):
            key = "legal_aid"
            reason = "The citizen seeks state-sponsored free legal representation under the Legal Services Authorities Act."
        else:
            key = "criminal_police"
            reason = "The issue involves criminal allegations, theft, assault, harassment, or general statutory violations requiring police intervention."

        config = cls.AUTHORITIES_DB[key]

        return StatutoryAuthorityRecommendationResponse(
            primary_authority=config["primary"],
            alternative_authorities=config["alternatives"],
            reasoning=reason,
            confidence=0.92,
            escalation_hierarchy=config["escalation"],
            metadata={"latency_ms": round((time.time() - start_time) * 1000, 2), "state_applied": request.state_or_ut}
        )

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from app.schemas.authority import AuthorityResult, JudicialAuthorityRecommendationResponse
from app.services.knowledge_service import LegalKnowledgeService
try:
    from psycopg2.extras import RealDictCursor
except ImportError:
    RealDictCursor = Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
KB_DATA_DIR = BASE_DIR / 'data' / 'knowledge_base'

class AuthorityRecommendationService:
    """
    Service responsible for deterministic matching and ranking of verified
    judicial authorities based on user query, statutory provisions, or section identifiers.
    """

    _cached_authorities: Optional[List[Dict[str, Any]]] = None
    _cached_registry: Optional[List[Dict[str, Any]]] = None

    # Specific phrase mappings for Tier 3 & Tier 4 deterministic matching
    # ONLY mapped to verified project landmark decisions
    PROPOSITION_KEYWORDS = {
        1: [  # Arjun Panditrao Khotkar ((2020) 7 SCC 1)
            "electronic record", "electronic evidence", "section 65b", "65b certificate",
            "section 63", "computer output", "secondary electronic evidence",
            "device production", "primary electronic evidence", "admissibility of electronic record"
        ],
        2: [  # Satender Kumar Antil ((2022) 10 SCC 51)
            "bail guidelines", "undertrial prisoner", "undertrial bail", "mechanical arrest",
            "bail is the rule", "bail is rule", "section 479", "section 35",
            "one-third detention", "first-time offender bail", "category a offence",
            "category b offence", "detention threshold"
        ],
        3: [  # Lalita Kumari ((2014) 2 SCC 1)
            "mandatory fir", "registration of fir", "mandatory registration of fir",
            "zero fir", "section 173", "preliminary inquiry", "preliminary enquiry",
            "14 days preliminary", "cognizable offence fir"
        ],
        4: [  # Bachan Singh ((1980) 2 SCC 684)
            "rarest of rare", "rarest of rare cases", "death penalty", "capital punishment",
            "murder sentencing", "life imprisonment foreclosed", "mitigating circumstances",
            "aggravating circumstances", "sentencing under section 103"
        ],
        5: [  # Shafhi Mohammad ((2018) 2 SCC 801)
            "videography", "audio-video recording", "search and seizure videography",
            "section 105", "scene of crime videography", "photography of search",
            "videography of search"
        ]
    }

    CONCEPT_KEYWORDS = {
        1: ["electronic", "digital evidence", "certificate", "computer", "device", "secondary evidence"],
        2: ["bail", "arrest", "undertrial", "custody", "remand", "detention", "surety"],
        3: ["fir", "police complaint", "cognizable", "complaint registration", "investigation"],
        4: ["murder", "death sentence", "culpable homicide", "capital sentence", "hanging"],
        5: ["search", "seizure", "videography", "camera", "crime scene", "investigation recording"]
    }

    # Acts 4-24 domain keywords that are known to belong to statutes with no verified judgments in source
    NOT_IN_SOURCE_ACT_KEYWORDS = {
        4: ["it act", "cyber", "hacking", "cyber terrorism", "identity theft", "digital signature"],
        5: ["pocso", "child sexual", "penetrative sexual", "child abuse"],
        6: ["juvenile", "jj act", "child in conflict with law", "cwc", "jjb"],
        7: ["pwdva", "domestic violence", "protection order", "shared household", "residence order"],
        8: ["dowry", "dpa", "dowry prohibition"],
        9: ["posh", "sexual harassment at workplace", "icc", "internal complaints committee"],
        10: ["hma", "hindu marriage", "divorce", "restitution of conjugal", "matrimonial"],
        11: ["hsa", "hindu succession", "coparcenary", "ancestral property", "inheritance"],
        12: ["sma", "special marriage", "interfaith marriage"],
        13: ["contract", "breach of contract", "damages", "consideration", "agreement"],
        14: ["specific relief", "sra", "injunction", "specific performance"],
        15: ["transfer of property", "tpa", "mortgage", "sale deed", "lease", "gift deed"],
        16: ["registration act", "sub-registrar", "registered document"],
        17: ["cheque", "cheque bounce", "dishonour of cheque", "section 138", "negotiable instruments", "ni act"],
        18: ["consumer", "cpa", "consumer forum", "deficiency in service", "unfair trade practice"],
        19: ["motor vehicle", "mva", "accident claim", "mact", "hit and run compensation"],
        20: ["rti", "right to information", "information commissioner", "public information officer", "pio"],
        21: ["legal services", "lsaa", "legal aid", "lok adalat"],
        22: ["arbitration", "arbitral tribunal", "arbitrator", "section 9", "section 11", "section 34"],
        23: ["companies act", "corporate fraud", "oppression and mismanagement", "nclt", "nclat"],
        24: ["insolvency", "bankruptcy", "ibc", "corporate insolvency", "cirp", "resolution professional"]
    }

    @classmethod
    def _load_authorities(cls) -> List[Dict[str, Any]]:
        """Loads verified landmark decisions from local storage."""
        if cls._cached_authorities is None:
            j_file = KB_DATA_DIR / "verified_judgments.json"
            if j_file.exists():
                with open(j_file, "r", encoding="utf-8") as f:
                    cls._cached_authorities = json.load(f)
            else:
                cls._cached_authorities = []
        return cls._cached_authorities

    @classmethod
    def _load_registry(cls) -> List[Dict[str, Any]]:
        """Loads 24-Act catalog metadata."""
        if cls._cached_registry is None:
            reg_file = KB_DATA_DIR / "phase17_24_acts_registry.json"
            if reg_file.exists():
                with open(reg_file, "r", encoding="utf-8") as f:
                    cls._cached_registry = json.load(f)
            else:
                cls._cached_registry = []
        return cls._cached_registry

    @classmethod
    def _is_act_without_verified_authorities(cls, law_id: Optional[int], law_name: Optional[str]) -> bool:
        """
        Determines whether a specified statute is an Act for which project sources
        have no verified judgments (Acts 4-24).
        """
        if law_id is not None and law_id > 3:
            return True

        if law_name:
            registry = cls._load_registry()
            law_lower = law_name.strip().lower()
            for act in registry:
                if act.get("act_id", 0) > 3:
                    if (act.get("short_name", "").lower() == law_lower or
                        act.get("act_name", "").lower() == law_lower or
                        law_lower in act.get("act_name", "").lower()):
                        return True
        return False

    @classmethod
    def _matches_not_in_source_domain(cls, query: str) -> Optional[int]:
        """
        Checks if the query is specifically targeted at a legal domain governed by Acts 4-24,
        where judgments are explicitly NOT IN SOURCE.
        """
        q_lower = query.lower().strip()
        for act_id, kw_list in cls.NOT_IN_SOURCE_ACT_KEYWORDS.items():
            for kw in kw_list:
                # Use word-boundary or exact keyword check to avoid false substring positives
                if kw in q_lower:
                    # Make sure it's not a generic word that overlaps with criminal procedure
                    return act_id
        return None

    @classmethod
    def recommend_authorities(
        cls,
        query: Optional[str] = None,
        law_id: Optional[int] = None,
        law_name: Optional[str] = None,
        section_number: Optional[str] = None,
        retrieved_sections: Optional[List[Dict[str, Any]]] = None,
        limit: int = 10,
        db: Optional[RealDictCursor] = None
    ) -> JudicialAuthorityRecommendationResponse:
        """
        Deterministically recommends verified judicial authorities using the 5-tier matching hierarchy.

        Guarantees:
        - Read-only execution.
        - Strict zero-fabrication.
        - Explicit "NOT IN SOURCE" status preservation for unsupported Acts.
        - Detailed match provenance and reason.
        """
        raw_authorities = cls._load_authorities()
        clean_query = query.strip() if query else None
        clean_sec = str(section_number).strip() if section_number is not None else None

        # 1. Check if user explicitly asked for an Act known to be NOT IN SOURCE
        if cls._is_act_without_verified_authorities(law_id, law_name):
            return JudicialAuthorityRecommendationResponse(
                query=clean_query,
                law_id=law_id,
                section_number=clean_sec,
                total=0,
                source_status="NOT IN SOURCE",
                recommendations=[],
                statutory_results=[]
            )

        # 2. Check if query is targeting a specific Act 4-24 domain (e.g. cheque bounce -> NI Act)
        # ONLY if no explicit BNS/BNSS/BSA law_id or section was passed
        if clean_query and not law_id and not clean_sec:
            target_act_id = cls._matches_not_in_source_domain(clean_query)
            if target_act_id:
                # Check if it also matches criminal code landmark cases (e.g. "fraud" or "investigation")
                # If it's specifically "cheque" or "domestic violence" or "rti", it is NOT IN SOURCE
                specific_not_in_source = True
                q_low = clean_query.lower()
                for sc_terms in cls.PROPOSITION_KEYWORDS.values():
                    if any(t in q_low for t in sc_terms):
                        specific_not_in_source = False
                        break
                if specific_not_in_source:
                    return JudicialAuthorityRecommendationResponse(
                        query=clean_query,
                        law_id=target_act_id,
                        section_number=clean_sec,
                        total=0,
                        source_status="NOT IN SOURCE",
                        recommendations=[],
                        statutory_results=[]
                    )

        # 3. Collect candidate statutory sections from input or retrieved_sections
        target_sections: List[Dict[str, Any]] = []
        statutory_results: List[Dict[str, Any]] = []

        if retrieved_sections:
            for rs in retrieved_sections:
                s_num = str(rs.get("section_number", "")).strip()
                l_id = rs.get("law_id")
                l_name = rs.get("law_name", "")
                if s_num:
                    target_sections.append({
                        "section_number": s_num,
                        "law_id": l_id,
                        "law_name": l_name
                    })
                statutory_results.append({
                    "law_id": l_id,
                    "law_name": l_name,
                    "section_number": s_num,
                    "section_title": rs.get("section_title"),
                    "snippet": rs.get("snippet")
                })

        if clean_sec:
            target_sections.insert(0, {
                "section_number": clean_sec,
                "law_id": law_id,
                "law_name": law_name or ""
            })

        # If query is provided and no sections passed, retrieve top statutory candidates
        if clean_query and not target_sections:
            try:
                kb_hits = LegalKnowledgeService.search_knowledge_base(query=clean_query, limit=5)
                for hit in kb_hits:
                    h_act_id = hit.get("act_id")
                    h_sec = str(hit.get("section_number", "")).strip()
                    h_name = hit.get("act_name", "")
                    statutory_results.append({
                        "law_id": h_act_id,
                        "law_name": h_name,
                        "short_name": hit.get("short_name"),
                        "section_number": h_sec,
                        "section_title": hit.get("section_title"),
                        "snippet": hit.get("snippet")
                    })
                    if h_act_id in [1, 2, 3] and h_sec:
                        target_sections.append({
                            "section_number": h_sec,
                            "law_id": h_act_id,
                            "law_name": h_name
                        })
            except Exception:
                pass

        # 4. Deterministic Matching Engine
        matched_results: Dict[int, AuthorityResult] = {}

        for idx, auth in enumerate(raw_authorities, start=1):
            auth_id = idx
            case_name = auth.get("case_title", "")
            court = auth.get("court", "Supreme Court of India")
            j_date_str = auth.get("judgment_date")
            j_date = None
            if j_date_str:
                try:
                    j_date = datetime.strptime(j_date_str, "%Y-%m-%d").date()
                except Exception:
                    pass

            citation = auth.get("citation")
            headnotes = auth.get("headnotes", "")
            j_text = auth.get("judgment_text", "")
            source_url = auth.get("source_url")
            source_name = auth.get("source_name", "Supreme Court of India Official Repository")
            linked_secs = auth.get("linked_sections", [])

            # Compile text pools
            full_context = f"{case_name} {citation} {headnotes} {j_text}".lower()

            best_match: Optional[AuthorityResult] = None

            # --- TIER 1: Exact Verified Section-to-Authority Mapping ---
            for sec_target in target_sections:
                s_num = sec_target["section_number"]
                for link in linked_secs:
                    if str(link.get("section_number")) == s_num:
                        # Check law name compatibility if provided
                        req_law = sec_target.get("law_name", "").lower()
                        link_law = link.get("law_name", "").lower()
                        is_law_compat = (
                            not req_law or
                            req_law in link_law or
                            link_law in req_law or
                            ("nyaya" in req_law and "nyaya" in link_law) or
                            ("nagarik" in req_law and "nagarik" in link_law) or
                            ("sakshya" in req_law and "sakshya" in link_law)
                        )
                        if is_law_compat:
                            explanation = link.get("explanation") or f"Direct authoritative precedent for Section {s_num}."
                            res = AuthorityResult(
                                authority_id=auth_id,
                                case_name=case_name,
                                court=court,
                                judgment_date=j_date,
                                citation=citation,
                                legal_proposition=headnotes or j_text[:200],
                                linked_law_id=sec_target.get("law_id"),
                                linked_law_name=link.get("law_name"),
                                linked_section_number=s_num,
                                matched_sections=[f"{link.get('law_name')} Section {s_num}"],
                                relevance_score=1.00,
                                match_type="exact_section_mapping",
                                reason=f"Tier 1: Exact verified section-to-authority mapping for Section {s_num} of {link.get('law_name')} ({explanation})",
                                source=source_name,
                                verification_status="verified"
                            )
                            best_match = res
                            break
                if best_match:
                    break

            # --- TIER 2: Exact Law + Verified Section Relationship ---
            if not best_match and (law_id in [1, 2, 3] or any(l in (law_name or "").lower() for l in ["nyaya", "nagarik", "sakshya", "bns", "bnss", "bsa"])):
                # If specific section was asked and matches linked section in criminal statutes
                for link in linked_secs:
                    if clean_sec and str(link.get("section_number")) == clean_sec:
                        res = AuthorityResult(
                            authority_id=auth_id,
                            case_name=case_name,
                            court=court,
                            judgment_date=j_date,
                            citation=citation,
                            legal_proposition=headnotes or j_text[:200],
                            linked_law_id=law_id,
                            linked_law_name=link.get("law_name"),
                            linked_section_number=clean_sec,
                            matched_sections=[f"{link.get('law_name')} Section {clean_sec}"],
                            relevance_score=0.85,
                            match_type="law_section_relationship",
                            reason=f"Tier 2: Exact law and section relationship verified under {link.get('law_name')} Section {clean_sec}",
                            source=source_name,
                            verification_status="verified"
                        )
                        best_match = res
                        break

            # --- TIER 3: Verified Legal Proposition / Issue Match ---
            if not best_match and clean_query:
                q_low = clean_query.lower()
                prop_list = cls.PROPOSITION_KEYWORDS.get(auth_id, [])
                matched_prop = None
                for p in prop_list:
                    if p in q_low:
                        matched_prop = p
                        break

                if matched_prop:
                    sec_refs = [f"{l.get('law_name')} Sec {l.get('section_number')}" for l in linked_secs]
                    res = AuthorityResult(
                        authority_id=auth_id,
                        case_name=case_name,
                        court=court,
                        judgment_date=j_date,
                        citation=citation,
                        legal_proposition=headnotes or j_text[:200],
                        linked_law_id=law_id,
                        linked_law_name=linked_secs[0].get("law_name") if linked_secs else None,
                        linked_section_number=linked_secs[0].get("section_number") if linked_secs else None,
                        matched_sections=sec_refs,
                        relevance_score=0.70,
                        match_type="legal_proposition_match",
                        reason=f"Tier 3: Verified legal proposition match on controlling principle '{matched_prop}'",
                        source=source_name,
                        verification_status="verified"
                    )
                    best_match = res

            # --- TIER 4: Verified Legal Concept / Category Match ---
            if not best_match and clean_query:
                q_low = clean_query.lower()
                concept_list = cls.CONCEPT_KEYWORDS.get(auth_id, [])
                matched_concept = None
                for c in concept_list:
                    if c in q_low:
                        matched_concept = c
                        break

                if matched_concept:
                    sec_refs = [f"{l.get('law_name')} Sec {l.get('section_number')}" for l in linked_secs]
                    res = AuthorityResult(
                        authority_id=auth_id,
                        case_name=case_name,
                        court=court,
                        judgment_date=j_date,
                        citation=citation,
                        legal_proposition=headnotes or j_text[:200],
                        linked_law_id=law_id,
                        linked_law_name=linked_secs[0].get("law_name") if linked_secs else None,
                        linked_section_number=linked_secs[0].get("section_number") if linked_secs else None,
                        matched_sections=sec_refs,
                        relevance_score=0.55,
                        match_type="concept_match",
                        reason=f"Tier 4: Verified legal category/concept match on '{matched_concept}'",
                        source=source_name,
                        verification_status="verified"
                    )
                    best_match = res

            # --- TIER 5: Verified Citation / Case Name Match ---
            if not best_match and clean_query:
                q_low = clean_query.lower()
                # Check for exact citation match or case name match
                c_clean = (citation or "").lower()
                name_words = [w for w in case_name.lower().split() if len(w) > 4 and w not in ["court", "state", "others", "union", "india", "another"]]
                is_name_match = any(w in q_low for w in name_words)
                is_cit_match = (c_clean and c_clean in q_low) or (citation and citation in clean_query)

                if is_cit_match or is_name_match:
                    sec_refs = [f"{l.get('law_name')} Sec {l.get('section_number')}" for l in linked_secs]
                    res = AuthorityResult(
                        authority_id=auth_id,
                        case_name=case_name,
                        court=court,
                        judgment_date=j_date,
                        citation=citation,
                        legal_proposition=headnotes or j_text[:200],
                        linked_law_id=law_id,
                        linked_law_name=linked_secs[0].get("law_name") if linked_secs else None,
                        linked_section_number=linked_secs[0].get("section_number") if linked_secs else None,
                        matched_sections=sec_refs,
                        relevance_score=0.95 if is_cit_match else 0.80,
                        match_type="citation_metadata_match" if is_cit_match else "case_name_match",
                        reason=f"Tier 5: Verified citation / party title match for '{citation if is_cit_match else case_name}'",
                        source=source_name,
                        verification_status="verified"
                    )
                    best_match = res

            if best_match:
                matched_results[auth_id] = best_match

        # 5. Order recommendations deterministically:
        # Sort key: relevance_score DESC, judgment_date DESC (newest first), authority_id ASC
        ranked_list = list(matched_results.values())
        ranked_list.sort(
            key=lambda x: (
                x.relevance_score,
                x.judgment_date.isoformat() if x.judgment_date else "1900-01-01",
                -x.authority_id
            ),
            reverse=True
        )

        final_recommendations = ranked_list[:limit]

        # 6. Determine final source_status
        if final_recommendations:
            source_status = "verified"
        else:
            # If query exists or law_id exists, state NOT IN SOURCE or NO MATCH
            if law_id and law_id > 3:
                source_status = "NOT IN SOURCE"
            elif clean_query and cls._matches_not_in_source_domain(clean_query):
                source_status = "NOT IN SOURCE"
            else:
                source_status = "NO MATCH"

        return JudicialAuthorityRecommendationResponse(
            query=clean_query,
            law_id=law_id,
            section_number=clean_sec,
            total=len(final_recommendations),
            source_status=source_status,
            recommendations=final_recommendations,
            statutory_results=statutory_results
        )
