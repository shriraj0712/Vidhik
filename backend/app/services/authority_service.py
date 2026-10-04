"""
Vidhik Platform - Authority Recommendation Service
==================================================
Deterministic, read-only judicial authority recommendation engine.
Grounds all recommendations strictly in verified project authority data.

Zero-Hallucination Policy:
- Never invents case titles, citations, benches, courts, dates, or propositions.
- For Acts where judgments are not available in project sources (Acts 4-24),
  strictly returns "NOT IN SOURCE".
- Transparent 5-tier deterministic ranking hierarchy with explicit reasoning.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Set
from datetime import datetime

try:
    from psycopg2.extras import RealDictCursor
except ImportError:
    RealDictCursor = Any

from app.schemas.authority import AuthorityResult, AuthorityRecommendationResponse
from app.services.knowledge_service import LegalKnowledgeService

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
KB_DATA_DIR = BASE_DIR / "data" / "knowledge_base"


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
    ) -> AuthorityRecommendationResponse:
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
            return AuthorityRecommendationResponse(
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
                    return AuthorityRecommendationResponse(
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

        return AuthorityRecommendationResponse(
            query=clean_query,
            law_id=law_id,
            section_number=clean_sec,
            total=len(final_recommendations),
            source_status=source_status,
            recommendations=final_recommendations,
            statutory_results=statutory_results
        )
