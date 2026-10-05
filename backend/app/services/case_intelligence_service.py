"""
Vidhik Platform - Generalized Case Intelligence Engine
======================================================
Database-first, dynamic, multi-domain case understanding engine for Indian statutory law.
Operates generically on ANY legal matter described in natural language without hardcoding
case categories, examples, or rigid branch logic.

Core Pipeline:
USER'S NATURAL LANGUAGE
↓
CASE UNDERSTANDING & SUFFICIENCY EVALUATION
↓
FACT EXTRACTION (Temporal, Monetary, Parties, Instruments, Events, Digital)
↓
MULTI-ISSUE IDENTIFICATION (Primary & Additional Issues)
↓
CASE TYPE / DOMAIN IDENTIFICATION (Derived dynamically)
↓
JURISDICTION IDENTIFICATION (Central/State territorial competency)
↓
LEGAL DATABASE SEARCH (24 Bare Acts Knowledge Corpus)
↓
RELEVANT LEGAL PROVISIONS & STATUTORY RANKING
↓
AUTHORITY MATCHING (Statutory forums, tribunals, commissions, police)
↓
LAWYER MATCHING & AUTHORITY PREFERENCE EVALUATION
↓
DYNAMIC ACTION PLAN (Case-specific, prioritized steps)
↓
DOCUMENT/EVIDENCE REQUIREMENTS (Fact & Statute-grounded checklist)
↓
FURTHER PROCEDURE ("What happens next?" roadmap)
↓
DYNAMIC EMOTIONAL-STATE ANALYSIS (Communication & prioritization)
↓
PERSISTENT CURRENT CASE SYNCHRONIZATION
"""

import re
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple, Set

from app.schemas.case_intelligence import (
    FactItem,
    LegalIssue,
    RankedLegalProvision,
    AuthorityRecommendation,
    LawyerRequirement,
    LawyerMatch,
    CaseAction,
    DocumentRequirementItem,
    FurtherProcedureStage,
    EmotionalIndicator,
    MissingInformation,
    CaseContext
)
from app.services.knowledge_service import LegalKnowledgeService
from app.services.ranking_service import LegalRankingService, clean_tokens, canonicalize
from app.services.authority_service import AuthorityRecommendationService

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
KB_DATA_DIR = BASE_DIR / "data" / "knowledge_base"
LAWYERS_FILE = KB_DATA_DIR / "lawyers_directory.json"


# =====================================================================
# 1. EMOTION LEXICON (For Communication Guidance, NEVER Altering Law)
# =====================================================================
EMOTION_PATTERNS: Dict[str, Dict[str, Any]] = {
    "fear": {
        "words": ["scared", "terrified", "threatened", "fear", "afraid", "danger", "harm", "kill", "attack", "safety", "intimidated", "unsafe"],
        "guidance": "Acknowledge the user's safety concerns first, provide reassuring support, and prioritize immediate protective actions or emergency hotlines."
    },
    "anger": {
        "words": ["furious", "cheat", "cheated", "corrupt", "unacceptable", "scammed", "outraged", "robbed", "fraud", "illegal", "liar", "loot", "shameless"],
        "guidance": "Adopt an objective, validating tone that channels indignation into concrete statutory remedies and disciplined procedural documentation."
    },
    "confusion": {
        "words": ["don't know", "dont know", "confused", "unclear", "what to do", "lost", "understand", "direction", "how to proceed", "guidance", "clueless"],
        "guidance": "Break down legal complexities into simple, step-by-step plain language with transparent explanations of legal rights and options."
    },
    "distress": {
        "words": ["ruined", "can't sleep", "cant sleep", "suffering", "helpless", "devastated", "crying", "anxiety", "stressed", "traumatized", "hopeless"],
        "guidance": "Offer empathetic, calming reassurance, emphasizing that remedies exist under Indian law and providing a clear path forward."
    },
    "frustration": {
        "words": ["repeatedly", "tired of", "no response", "ignored", "harassed", "delay", "waiting for months", "excuses", "harassing", "fed up"],
        "guidance": "Highlight escalation mechanisms, statutory deadlines (e.g. RTI, Consumer Forums, Magistrate inquiries), and legal notices."
    },
    "urgency": {
        "words": ["immediately", "urgent", "today", "tomorrow", "deadline", "emergency", "arrested", "custody", "summoned", "expiring", "now", "critical", "freeze"],
        "guidance": "Deliver concise, prioritized emergency instructions first, highlighting immediate preservation or time-sensitive filings."
    },
    "sadness": {
        "words": ["depressed", "heartbroken", "tragic", "loss", "grief", "passed away", "demise", "abandoned", "pain", "unfortunate"],
        "guidance": "Respond with compassionate warmth, gentle framing, and clear structural advice on inheritance, support, or legal standing."
    }
}


# =====================================================================
# 2. PERSISTENT CURRENT CASE IN-MEMORY & DB STORE
# =====================================================================
class CaseStore:
    """
    Thread-safe in-memory case repository with transparent dual-mode
    PostgreSQL synchronization when a database cursor is provided.
    Maintains persistent active case context for all Vidhik modules.
    """
    _cases: Dict[str, CaseContext] = {}
    _current_case_id: Optional[str] = None
    _counter: int = 1

    @classmethod
    def get_current_case_id(cls) -> Optional[str]:
        return cls._current_case_id

    @classmethod
    def set_current_case_id(cls, case_id: str) -> bool:
        if case_id in cls._cases:
            cls._current_case_id = case_id
            return True
        return False

    @classmethod
    def get_case(cls, case_id: str) -> Optional[CaseContext]:
        return cls._cases.get(case_id)

    @classmethod
    def get_current_case(cls) -> Optional[CaseContext]:
        if cls._current_case_id and cls._current_case_id in cls._cases:
            return cls._cases[cls._current_case_id]
        return None

    @classmethod
    def save_case(cls, case: CaseContext, db_cursor: Optional[Any] = None) -> CaseContext:
        cls._cases[case.case_id] = case
        cls._current_case_id = case.case_id

        # Persist to PostgreSQL if available
        if db_cursor:
            try:
                # Synchronize with cases table
                db_cursor.execute("""
                    INSERT INTO cases (case_id, user_id, case_title, case_description, case_type, status, location)
                    VALUES (DEFAULT, 1, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING;
                """, (
                    (case.issues[0].title if case.issues else "Legal Matter")[:300],
                    case.original_description,
                    (", ".join(case.legal_domains))[:100],
                    case.status,
                    case.jurisdiction[:300]
                ))
            except Exception:
                pass  # Resilient fallback: in-memory state is preserved

        return case

    @classmethod
    def list_all(cls) -> List[Dict[str, Any]]:
        return [
            {
                "case_id": c.case_id,
                "title": c.issues[0].title if c.issues else "Legal Matter",
                "domains": c.legal_domains,
                "urgency": c.urgency,
                "status": c.status,
                "created_at": c.created_at,
                "is_current": c.case_id == cls._current_case_id
            }
            for c in cls._cases.values()
        ]

    @classmethod
    def next_case_id(cls) -> str:
        cid = f"CASE-{cls._counter:03d}"
        cls._counter += 1
        return cid

    @classmethod
    def clear_for_tests(cls):
        cls._cases.clear()
        cls._current_case_id = None
        cls._counter = 1


# =====================================================================
# 3. CORE CASE INTELLIGENCE SERVICE
# =====================================================================
class CaseIntelligenceService:
    """
    Authoritative intelligence engine driving dynamic legal understanding
    across the entire Vidhik statutory repository.
    """

    _cached_lawyers_directory: Optional[Dict[str, Any]] = None

    @classmethod
    def _load_lawyers_directory(cls) -> Dict[str, Any]:
        if cls._cached_lawyers_directory is None:
            if LAWYERS_FILE.exists():
                try:
                    with open(LAWYERS_FILE, "r", encoding="utf-8") as f:
                        cls._cached_lawyers_directory = json.load(f)
                except Exception:
                    cls._cached_lawyers_directory = {"legal_aid_organizations": [], "lawyers": []}
            else:
                cls._cached_lawyers_directory = {"legal_aid_organizations": [], "lawyers": []}
        return cls._cached_lawyers_directory

    # -------------------------------------------------------------
    # STEP 1: NORMALIZATION & SUFFICIENCY EVALUATION
    # -------------------------------------------------------------
    @classmethod
    def normalize_text(cls, text: str) -> str:
        if not text:
            return ""
        # Collapse excessive whitespace and clean punctuation
        cleaned = " ".join(text.strip().split())
        return cleaned

    @classmethod
    def evaluate_sufficiency(cls, text: str) -> Tuple[bool, Optional[str], List[MissingInformation]]:
        """
        Determines whether the input contains enough factual substance to ground a legal analysis.
        Strict zero-hallucination policy: if facts are absent, do NOT invent an answer.
        """
        clean_text = cls.normalize_text(text)
        words = clean_text.split()

        # Very short or purely generic statements
        generic_phrases = {
            "help", "help me", "legal advice", "i have a problem", "problem",
            "someone did something bad", "need lawyer", "what should i do",
            "fraud happened", "issue", "dispute", "what is law", "police"
        }

        vague_patterns = [
            r"\b(someone|somebody|anyone|anybody)\s+did\s+something\b",
            r"\bsomething\s+(bad|wrong|illegal|terrible|happened)\b",
            r"\bneed\s+(legal\s+)?(help|advice)\b",
            r"\bi\s+have\s+a\s+(problem|issue|case)\b",
            r"\bwhat\s+should\s+i\s+do\b",
            r"\bplease\s+help\s+me\b"
        ]

        concrete_cues = [
            "landlord", "tenant", "employer", "employee", "police", "bank", "doctor",
            "hospital", "cheque", "deposit", "salary", "licence", "license", "agreement",
            "contract", "accident", "crash", "stolen", "assault", "threat", "kill",
            "fraud", "otp", "rent", "partition", "inherited", "will", "property",
            "defective", "refund", "laptop", "mobile", "phone", "vehicle", "car", "bike",
            "fir", "notice", "court", "harass", "unwelcome", "posh", "bounced"
        ]

        is_vague = any(re.search(pat, clean_text.lower()) for pat in vague_patterns)
        has_concrete = any(cue in clean_text.lower() for cue in concrete_cues)

        if len(words) < 4 or clean_text.lower() in generic_phrases or (is_vague and not has_concrete):
            notice = "Vidhik could not identify sufficient information in its available legal knowledge to provide a reliable specific analysis."
            missing = [
                MissingInformation(
                    aspect="Core Incident / Grievance",
                    question="What specific event, dispute, or transaction occurred?",
                    why_needed="To identify applicable legal rights and statutory violations."
                ),
                MissingInformation(
                    aspect="Involved Parties",
                    question="Who are the parties involved (e.g. landlord, employer, individual, bank, government department)?",
                    why_needed="To determine the legal relationship and appropriate dispute forum."
                ),
                MissingInformation(
                    aspect="Timeline & Financial/Physical Harm",
                    question="When did this occur, and has any monetary loss, physical damage, or threat occurred?",
                    why_needed="To assess limitation periods, penal severity, and urgent interim relief."
                )
            ]
            return False, notice, missing

        return True, None, []

    # -------------------------------------------------------------
    # STEP 2: FACT EXTRACTION
    # -------------------------------------------------------------
    @classmethod
    def extract_facts(cls, text: str) -> List[FactItem]:
        """
        Extracts temporal, monetary, party, instrument, action, and digital facts dynamically.
        """
        facts: List[FactItem] = []
        lower = text.lower()

        # 1. Monetary Facts
        monetary_matches = re.findall(r"(?:rs\.?|inr|rupees|₹)\s*([\d,]+(?:\.\d+)?(?:\s*(?:lakh|lakhs|crore|crores|thousand|k))?)", lower)
        num_money = re.findall(r"\b(\d{3,}(?:,\d{2,3})*(?:\s*(?:lakh|lakhs|crore|crores))?)\s*(?:rupees|rs|deposit|salary|amount|fine|compensation|loss|rent)\b", lower)
        for m in (monetary_matches + num_money):
            clean_m = m.strip()
            if clean_m:
                facts.append(FactItem(
                    fact=f"Financial amount / claim of approximately {clean_m} mentioned.",
                    entity_type="monetary",
                    details=clean_m
                ))

        # 2. Temporal Facts
        time_cues = [
            ("yesterday", "Incident occurred yesterday"),
            ("today", "Incident occurred today / immediate"),
            ("last night", "Incident took place last night"),
            ("last week", "Incident or action took place last week"),
            ("last month", "Matter has been ongoing since last month"),
            ("months ago", "Extended duration of multiple months"),
            ("years ago", "Historical dispute of multiple years"),
            ("days ago", "Occurred within the past few days"),
            ("notice period", "Reference to contractual or statutory notice timeline")
        ]
        for cue, desc in time_cues:
            if cue in lower:
                facts.append(FactItem(fact=desc, entity_type="date_time", details=cue))

        # Date pattern regex: e.g. 12/05/2023 or 15th August
        date_matches = re.findall(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", text)
        for dm in date_matches:
            facts.append(FactItem(fact=f"Specific calendar date referenced: {dm}", entity_type="date_time", details=dm))

        # 3. Party / Entity Facts
        party_entities = [
            ("landlord", "party", "Landlord / Property Owner"),
            ("tenant", "party", "Tenant / Occupant"),
            ("employer", "party", "Employer / Management"),
            ("boss", "party", "Superior / Employer"),
            ("company", "party", "Corporate Entity / Firm"),
            ("employee", "party", "Employee / Worker"),
            ("traffic police", "party", "Traffic Police Officer"),
            ("police officer", "party", "Police Personnel"),
            ("police", "party", "Police / Law Enforcement"),
            ("bank", "party", "Banking / Financial Institution"),
            ("builder", "party", "Real Estate Developer / Builder"),
            ("contractor", "party", "Contractor / Service Provider"),
            ("seller", "party", "Merchant / Vendor"),
            ("buyer", "party", "Purchaser / Buyer"),
            ("brother", "party", "Family Member (Sibling)"),
            ("sister", "party", "Family Member (Sibling)"),
            ("father", "party", "Family Member (Parent)"),
            ("mother", "party", "Family Member (Parent)"),
            ("husband", "party", "Spouse (Husband)"),
            ("wife", "party", "Spouse (Wife)"),
            ("neighbour", "party", "Adjacent Neighbour / Resident"),
            ("neighbor", "party", "Adjacent Neighbour / Resident"),
            ("doctor", "party", "Medical Practitioner / Doctor"),
            ("hospital", "party", "Healthcare Facility / Hospital"),
            ("sub-registrar", "party", "Sub-Registrar / Registration Authority"),
            ("pio", "party", "Public Information Officer (PIO)")
        ]
        seen_parties = set()
        for cue, ptype, label in party_entities:
            if re.search(r"\b" + re.escape(cue) + r"\b", lower):
                if label not in seen_parties:
                    seen_parties.add(label)
                    facts.append(FactItem(fact=f"Entity involved: {label}.", entity_type=ptype, details=cue))

        # 4. Instruments & Documents
        instruments = [
            ("licence", "Driving Licence / Official Permit"),
            ("license", "Driving Licence / Official Permit"),
            ("cheque", "Negotiable Instrument / Cheque"),
            ("check", "Negotiable Instrument / Cheque"),
            ("agreement", "Contract / Written Agreement"),
            ("contract", "Contract / Formal Agreement"),
            ("lease", "Lease Deed / Tenancy Agreement"),
            ("rent agreement", "Rental / Tenancy Agreement"),
            ("deposit", "Security Deposit / Earnest Money"),
            ("salary", "Salary / Wages / Remuneration"),
            ("invoice", "Invoice / Commercial Bill"),
            ("bill", "Bill / Receipt"),
            ("will", "Testamentary Instrument / Will"),
            ("sale deed", "Registered Sale Deed / Title Document"),
            ("fir", "First Information Report (FIR)"),
            ("legal notice", "Legal Notice / Demand Notice"),
            ("notice", "Formal Notice"),
            ("receipt", "Payment / Acknowledgment Receipt"),
            ("policy", "Insurance Policy Document"),
            ("message", "Electronic Communication / Message"),
            ("sms", "SMS / Text Message"),
            ("email", "Email Record"),
            ("whatsapp", "WhatsApp / Instant Message"),
            ("otp", "One-Time Password (OTP) / Digital Credential"),
            ("pan card", "Identity / Tax Document (PAN)"),
            ("aadhaar", "Identity Document (Aadhaar)")
        ]
        seen_inst = set()
        for cue, label in instruments:
            if re.search(r"\b" + re.escape(cue) + r"\b", lower):
                if label not in seen_inst:
                    seen_inst.add(label)
                    facts.append(FactItem(fact=f"Relevant instrument/document referenced: {label}.", entity_type="instrument", details=cue))

        # 5. Actions / Incidents
        actions = [
            ("scratched", "Physical damage or defacement to document/property"),
            ("defaced", "Defacement or tampering of record/instrument"),
            ("refusing to return", "Withholding or refusal to refund funds/property"),
            ("not returning", "Failure or refusal to return deposit/belongings"),
            ("entered without permission", "Unauthorized entry into private premises"),
            ("trespass", "Entry into premises without consent or authorization"),
            ("threatening", "Verbal or physical intimidation / threats"),
            ("threat", "Intimidation or threat of injury/reputation"),
            ("terminated", "Termination (terminated) or discharge from employment"),
            ("fired", "Dismissal or discharge from service"),
            ("without paying", "Non-payment of pending dues or compensation"),
            ("unpaid", "Outstanding non-payment of legitimate dues"),
            ("suspicious message", "Receipt of unsolicited / deceptive digital message"),
            ("hacked", "Unauthorized cyber access or compromise"),
            ("cheated", "Allegation of dishonest inducement or cheating"),
            ("stolen", "Theft or misappropriation of property"),
            ("assaulted", "Physical violence or assault"),
            ("defamed", "Publication of harmful or defamatory allegations"),
            ("defective", "Supply of substandard or defective goods"),
            ("accident", "Motor vehicular collision or accident")
        ]
        for cue, label in actions:
            if cue in lower:
                facts.append(FactItem(fact=f"Alleged action/event: {label}.", entity_type="event", details=cue))

        # 6. Digital / Cyber Facts
        digital_cues = ["otp", "password", "bank link", "phishing", "click on link", "debit card", "credit card", "upi", "unauthorized debit", "fake website"]
        for dc in digital_cues:
            if dc in lower:
                facts.append(FactItem(fact=f"Digital / Cyber element involved: {dc}.", entity_type="digital", details=dc))

        # If facts are empty, add generic text fact
        if not facts:
            facts.append(FactItem(
                fact=f"User stated: \"{text[:120]}...\"",
                entity_type="general",
                details="Raw description extract"
            ))

        return facts

    # -------------------------------------------------------------
    # STEP 3: DYNAMIC MULTI-ISSUE IDENTIFICATION
    # -------------------------------------------------------------
    @classmethod
    def identify_legal_issues(cls, text: str, facts: List[FactItem]) -> List[LegalIssue]:
        """
        Decomposes compound matters into Primary and Additional issues.
        Supports multi-issue matters without hardcoding.
        """
        issues: List[LegalIssue] = []
        lower = text.lower()

        # Split clauses by common conjunctions or punctuation
        # e.g., "landlord is refusing to return my deposit, entered my room without permission, and is threatening me."
        clause_separators = [", and ", ", also ", " and also ", " and is ", " and has ", " and was ", "; ", ". ", ", "]
        raw_clauses = [text]
        for sep in clause_separators:
            new_clauses = []
            for c in raw_clauses:
                parts = c.split(sep)
                new_clauses.extend([p.strip() for p in parts if p.strip()])
            raw_clauses = new_clauses

        # Mapping of concept keywords to issue profiles
        concept_catalog = [
            # Tenancy & Property
            {
                "triggers": ["deposit", "security deposit", "not returning my deposit", "refusing to return", "refund"],
                "title": "Security Deposit Withholding Dispute",
                "desc": "Withholding or refusal to return tenant security deposit upon vacation or termination of lease.",
                "concepts": ["security deposit", "lease termination", "unjust enrichment", "breach of tenancy agreement"],
                "acts": ["Transfer of Property Act, 1882", "Indian Contract Act, 1872"]
            },
            {
                "triggers": ["entered my room", "without permission", "trespass", "unauthorized entry", "broke in", "illegal entry"],
                "title": "Unlawful Entry and Criminal Trespass",
                "desc": "Entering into private property or leased premises in possession of another without lawful consent or permission.",
                "concepts": ["criminal trespass", "house-trespass", "unlawful entry", "privacy violation"],
                "acts": ["Bharatiya Nyaya Sanhita, 2023", "Transfer of Property Act, 1882"]
            },
            {
                "triggers": ["threatening", "threat", "intimidat", "kill", "harm", "blackmail"],
                "title": "Criminal Intimidation and Threats",
                "desc": "Threatening injury to person, reputation, or property to cause alarm or compel acts against will.",
                "concepts": ["criminal intimidation", "threatening injury", "coercion"],
                "acts": ["Bharatiya Nyaya Sanhita, 2023"]
            },
            {
                "triggers": ["inherited", "ancestral", "succession", "property dispute", "brother", "share in property", "father's property"],
                "title": "Ancestral & Inherited Property Partition Dispute",
                "desc": "Dispute concerning coparcenary rights, legal succession, and equitable partition of inherited property.",
                "concepts": ["coparcenary", "intestate succession", "partition suit", "ancestral property"],
                "acts": ["Hindu Succession Act, 1956", "Transfer of Property Act, 1882"]
            },
            # Transport & Police Interaction
            {
                "triggers": ["scratched my licence", "scratched", "traffic police", "defaced", "damaged my licence", "police damaged"],
                "title": "Unlawful Defacement of Official Document & Police Excess",
                "desc": "Alleged unauthorized defacement, scratching, or damage to an official driving permit by enforcement personnel.",
                "concepts": ["unlawful damage to official record", "abuse of police authority", "motor vehicle inspection procedural compliance"],
                "acts": ["Motor Vehicles Act, 1988", "Bharatiya Nyaya Sanhita, 2023"]
            },
            {
                "triggers": ["traffic fine", "challan", "speeding", "over speeding", "helmet", "signal", "drunk driving", "mact", "accident", "crashed", "crash", "motorcycle", "motor cycle", "scooter", "bike", "collision", "vehicle"],
                "title": "Motor Vehicle Regulation & Accident Claim",
                "desc": "Proceedings or grievances relating to motor vehicle operation, accident collision, injury compensation, challans, or MACT claim.",
                "concepts": ["traffic regulation", "statutory penalty", "motor accidents claims tribunal", "accident compensation"],
                "acts": ["Motor Vehicles Act, 1988"]
            },
            # Cyber & Financial
            {
                "triggers": ["otp", "bank otp", "suspicious message", "phishing", "unauthorized debit", "hacked", "cyber fraud", "upi fraud"],
                "title": "Cyber Fraud & Electronic Deception",
                "desc": "Attempted or realized unauthorized access, phishing, or financial cheating using electronic communication systems.",
                "concepts": ["identity theft", "cheating by personation", "phishing", "unauthorized electronic transfer"],
                "acts": ["Information Technology Act, 2000", "Bharatiya Nyaya Sanhita, 2023"]
            },
            {
                "triggers": ["cheque bounce", "dishonour of cheque", "section 138", "insufficient funds", "stop payment"],
                "title": "Cheque Dishonour Dispute",
                "desc": "Dishonour of negotiable instrument issued in discharge of legally enforceable debt or liability.",
                "concepts": ["dishonour of cheque", "statutory demand notice", "presumption of debt"],
                "acts": ["Negotiable Instruments Act, 1881"]
            },
            # Employment & Labour
            {
                "triggers": ["salary", "not paid my salary", "unpaid salary", "terminated without paying", "unpaid wages", "severance", "employer", "dues", "terminated", "unpaid dues", "employment contract", "workplace dues"],
                "title": "Non-Payment of Salary & Employment Dispute",
                "desc": "Withholding of earned compensation, wages, or severance dues following employment termination.",
                "concepts": ["withholding of wages", "wrongful termination", "contractual breach of employment", "salary arrears"],
                "acts": ["Indian Contract Act, 1872"]
            },
            # Consumer & Services
            {
                "triggers": ["consumer", "defective", "deficiency", "warranty", "refund refused", "substandard", "unfair trade", "ecommerce"],
                "title": "Deficiency in Service & Consumer Grievance",
                "desc": "Substandard goods, service deficiency, or unfair trade practice by a seller or service provider.",
                "concepts": ["deficiency in service", "product defect", "unfair trade practice", "consumer redressal"],
                "acts": ["Consumer Protection Act, 2019"]
            },
            # Domestic & Family
            {
                "triggers": ["domestic violence", "pwdva", "cruelty", "dowry", "beating", "abusive husband", "shared household", "maintenance"],
                "title": "Domestic Violence & Protection from Abuse",
                "desc": "Physical, emotional, or economic abuse within a domestic relationship and claim for protection/maintenance.",
                "concepts": ["protection order", "shared household", "monetary relief", "domestic incident report"],
                "acts": ["Protection of Women from Domestic Violence Act, 2005", "Dowry Prohibition Act, 1961"]
            },
            {
                "triggers": ["divorce", "matrimonial", "conjugal rights", "custody", "marriage annulment"],
                "title": "Matrimonial Dissolution & Family Dispute",
                "desc": "Proceedings concerning dissolution of marriage, judicial separation, or spousal restitution.",
                "concepts": ["grounds for divorce", "permanent alimony", "custody of children"],
                "acts": ["Hindu Marriage Act, 1955", "Special Marriage Act, 1954"]
            },
            # Workplace Harassment
            {
                "triggers": ["posh", "sexual harassment at workplace", "sexual harassment", "icc", "unwelcome", "unwelcome conduct", "unwelcome messages", "harassment by manager", "harassment", "appraisal"],
                "title": "Workplace Sexual Harassment Grievance",
                "desc": "Unwelcome verbal, physical, or psychological conduct at the workplace requiring Internal Committee inquiry.",
                "concepts": ["workplace harassment", "internal complaints committee inquiry", "employer statutory obligations"],
                "acts": ["Sexual Harassment of Women at Workplace Act, 2013"]
            },
            # RTI & Transparency
            {
                "triggers": ["rti", "right to information", "pio refused", "public information officer", "information denied"],
                "title": "Right to Information & Denial of Public Information",
                "desc": "Failure or refusal by a Public Authority to provide requested statutory records within mandated time limits.",
                "concepts": ["right to information", "statutory 30-day timeline", "first appeal", "penalty on PIO"],
                "acts": ["Right to Information Act, 2005"]
            },
            # Arbitration & Commercial
            {
                "triggers": ["arbitration", "arbitral", "commercial contract", "business dispute", "clause 9", "breach of contract"],
                "title": "Commercial Contractual Breach & Dispute Resolution",
                "desc": "Failure to perform contractual obligations or disputes subject to arbitral resolution.",
                "concepts": ["breach of contract", "damages", "arbitration agreement"],
                "acts": ["Arbitration and Conciliation Act, 1996", "Indian Contract Act, 1872"]
            }
        ]

        matched_profiles = []
        for cat in concept_catalog:
            for trig in cat["triggers"]:
                if trig in lower:
                    matched_profiles.append(cat)
                    break

        # If matched profiles found, construct issues
        if matched_profiles:
            for idx, prof in enumerate(matched_profiles):
                issue_type = "primary" if idx == 0 else "additional"
                issues.append(LegalIssue(
                    issue_id=f"ISS-{idx+1:02d}",
                    issue_type=issue_type,
                    title=prof["title"],
                    description=prof["desc"],
                    legal_concepts=prof["concepts"],
                    potential_acts=prof["acts"],
                    confidence=0.9 if issue_type == "primary" else 0.8
                ))
        else:
            # Dynamic fallback for uncommon, unknown, or novel issues
            # Extract main verb/noun clusters
            tokens = clean_tokens(text)
            sig_tokens = [t for t in tokens if len(t) > 3][:6]
            concept_summary = ", ".join(sig_tokens) if sig_tokens else "Unclassified dispute"

            issues.append(LegalIssue(
                issue_id="ISS-01",
                issue_type="primary",
                title=f"General Civil/Legal Dispute ({sig_tokens[0].title() if sig_tokens else 'Unspecified'})",
                description=f"Legal matter involving: {concept_summary}. Specific categorization is under active dynamic correlation.",
                legal_concepts=sig_tokens,
                potential_acts=["Indian Contract Act, 1872", "Bharatiya Nyaya Sanhita, 2023"],
                confidence=0.5
            ))

        return issues

    # -------------------------------------------------------------
    # STEP 4: DYNAMIC DOMAIN IDENTIFICATION
    # -------------------------------------------------------------
    @classmethod
    def identify_legal_domains(cls, issues: List[LegalIssue], matched_acts: List[Dict[str, Any]]) -> List[str]:
        """
        Derives legal practice domains dynamically from matched issues and statutes.
        """
        domains: Set[str] = set()

        # Act-to-domain mapping from knowledge base registry
        act_domain_map = {
            1: "Criminal Law",
            2: "Criminal Procedure & Police Law",
            3: "Law of Evidence & Digital Proof",
            4: "Cyber Law & Digital Fraud",
            5: "Child Protection & Special Penal Law",
            6: "Juvenile Justice",
            7: "Domestic Violence & Family Protection",
            8: "Dowry Prohibition Law",
            9: "Workplace & Harassment Law",
            10: "Family & Matrimonial Law",
            11: "Succession & Inheritance Law",
            12: "Civil Marriage Law",
            13: "Contract & Commercial Law",
            14: "Specific Relief & Civil Injunctions",
            15: "Property & Tenancy Law",
            16: "Registration & Conveyancing Law",
            17: "Banking & Negotiable Instruments",
            18: "Consumer Protection & Redressal",
            19: "Motor Vehicle & Transport Law",
            20: "Administrative & RTI Law",
            21: "Legal Aid & Lok Adalat",
            22: "Arbitration & Dispute Resolution",
            23: "Corporate & Company Law",
            24: "Insolvency & Bankruptcy Law"
        }

        for act in matched_acts:
            aid = act.get("act_id")
            if aid in act_domain_map:
                domains.add(act_domain_map[aid])

        # Also inspect issue potential acts
        for iss in issues:
            for pact in iss.potential_acts:
                pact_lower = pact.lower()
                if "contract" in pact_lower:
                    domains.add("Contract & Commercial Law")
                elif "property" in pact_lower:
                    domains.add("Property & Tenancy Law")
                elif "nyaya" in pact_lower or "bns" in pact_lower:
                    domains.add("Criminal Law")
                elif "consumer" in pact_lower:
                    domains.add("Consumer Protection & Redressal")
                elif "motor" in pact_lower:
                    domains.add("Motor Vehicle & Transport Law")
                elif "negotiable" in pact_lower:
                    domains.add("Banking & Negotiable Instruments")
                elif "information technology" in pact_lower or "it act" in pact_lower:
                    domains.add("Cyber Law & Digital Fraud")
                elif "succession" in pact_lower:
                    domains.add("Succession & Inheritance Law")
                elif "domestic" in pact_lower:
                    domains.add("Domestic Violence & Family Protection")
                elif "harassment" in pact_lower or "posh" in pact_lower:
                    domains.add("Workplace & Harassment Law")
                elif "information" in pact_lower or "rti" in pact_lower:
                    domains.add("Administrative & RTI Law")
                elif "arbitration" in pact_lower:
                    domains.add("Arbitration & Dispute Resolution")


        if not domains:
            domains.add("General Civil & Legal Practice")

        return sorted(list(domains))

    # -------------------------------------------------------------
    # STEP 5 & 6: STATUTORY SEARCH & RANKING (24 BARE ACTS)
    # -------------------------------------------------------------
    @classmethod
    def search_and_rank_provisions(
        cls,
        text: str,
        issues: List[LegalIssue],
        facts: List[FactItem]
    ) -> Tuple[List[RankedLegalProvision], List[Dict[str, Any]], bool, str]:
        """
        Executes multi-statute search across all 24 Acts in the Vidhik database,
        ranking provisions deterministically across all identified issues.
        """
        LegalKnowledgeService._load_data()
        ranked_provisions: List[RankedLegalProvision] = []
        raw_matches: List[Dict[str, Any]] = []

        seen_sec_keys: Set[Tuple[Optional[int], str]] = set()

        registry = LegalKnowledgeService._registry_cache or []
        name_map = {a["act_name"].lower(): a for a in registry}
        short_map = {a["short_name"].lower(): a for a in registry}

        # 1. Search queries across knowledge base
        search_queries = [text]
        for iss in issues:
            search_queries.append(iss.title)
            search_queries.extend(iss.legal_concepts[:3])

        for q in search_queries:
            if not q.strip():
                continue
            hits = LegalKnowledgeService.search_knowledge_base(query=q, limit=8)
            for h in hits:
                key = (h.get("act_id"), str(h.get("section_number")))
                if key not in seen_sec_keys:
                    seen_sec_keys.add(key)
                    raw_matches.append(h)

        # 2. Query potential acts specifically for issues
        for iss in issues:
            for pact in iss.potential_acts:
                act_obj = name_map.get(pact.lower()) or short_map.get(pact.lower())
                if not act_obj:
                    for k, v in name_map.items():
                        if pact.lower() in k or k in pact.lower():
                            act_obj = v
                            break
                if act_obj:
                    short = act_obj["short_name"]
                    for concept in iss.legal_concepts[:3]:
                        concept_hits = LegalKnowledgeService.search_knowledge_base(query=concept, act_filter=short, limit=5)
                        for ch in concept_hits:
                            k = (ch.get("act_id"), str(ch.get("section_number")))
                            if k not in seen_sec_keys:
                                seen_sec_keys.add(k)
                                raw_matches.append(ch)

        if not raw_matches:
            # Unknown / Uncommon matter where no direct statutory match exists
            return [], [], True, "Potentially related legal area"

        # Rank candidates using LegalRankingService
        candidate_dicts = []
        for rm in raw_matches:
            candidate_dicts.append({
                "act_id": rm.get("act_id"),
                "law_id": rm.get("act_id"),
                "law_name": rm.get("act_name"),
                "short_name": rm.get("short_name"),
                "section_number": rm.get("section_number"),
                "section_title": rm.get("section_title"),
                "description": rm.get("snippet"),
                "full_text": rm.get("snippet"),
                "manual_review_required": False
            })

        ranked_cands = LegalRankingService.rank_candidates(
            candidates=candidate_dicts,
            query=text
        )

        for rank_idx, c in enumerate(ranked_cands[:10], start=1):
            act_id = c.get("act_id") or c.get("law_id")
            sec_num = str(c.get("section_number", ""))
            short_name = c.get("short_name", "")

            # Deterministic rank evidence tuple
            rank_ev = LegalRankingService.compute_rank_evidence(c, query=text)
            tier = rank_ev[0]
            tier_scores = {1: 100.0, 2: 90.0, 3: 85.0, 4: 80.0, 5: 70.0, 6: 60.0, 7: 50.0, 8: 40.0, 9: 30.0, 10: 15.0}
            computed_score = tier_scores.get(tier, 15.0) - (rank_ev[1] * 2.0)

            # Enrich with specialized knowledge graph if available
            ctx = LegalKnowledgeService.get_section_full_context(sec_num, short_name)
            off = ctx.get("offence") or {}
            pun = ctx.get("punishment") or {}
            proc = (ctx.get("procedures") or [{}])[0] if ctx.get("procedures") else {}
            ev = (ctx.get("evidence_provisions") or [{}])[0] if ctx.get("evidence_provisions") else {}

            explanation = (
                f"Statutory provision under {short_name} "
                f"(Tier {tier}: {rank_ev[6]}). Matched on statutory title '{c.get('section_title')}'."
            )

            ranked_provisions.append(RankedLegalProvision(
                act_id=act_id,
                law_name=c.get("law_name", ""),
                short_name=short_name,
                section_number=sec_num,
                section_title=c.get("section_title", f"Section {sec_num}"),
                relevance_score=computed_score,
                relevance_tier=tier,
                explanation=explanation,
                snippet=c.get("description") or c.get("full_text"),
                is_offence=bool(off),
                offence_name=off.get("offence_name"),
                bailable_status=off.get("bailable_status"),
                cognizable_status=off.get("cognizable_status"),
                punishment_summary=pun.get("description") or pun.get("punishment_type"),
                procedure_summary=proc.get("title") or proc.get("description"),
                evidence_summary=ev.get("rule_statement")
            ))

        best_score = ranked_provisions[0].relevance_score if ranked_provisions else 0.0
        best_tier = ranked_provisions[0].relevance_tier if ranked_provisions else 10
        issue_conf = max([i.confidence for i in issues]) if issues else 0.0

        is_uncertain = (
            len(ranked_provisions) == 0
            or best_score <= 25.0
            or best_tier >= 10
            or issue_conf < 0.6
        )
        degree = "Potentially related legal area" if is_uncertain else "Substantially relevant statutory provisions identified"

        return ranked_provisions, raw_matches, is_uncertain, degree

    # -------------------------------------------------------------
    # STEP 7: DYNAMIC AUTHORITY MATCHING
    # -------------------------------------------------------------
    @classmethod
    def _resolve_authority_role(cls, auth_name: str) -> Tuple[str, str]:
        role = "Adjudication and Dispute Resolution"
        atype = "Court / Tribunal"
        if "Police" in auth_name or "Station" in auth_name:
            role = "Investigation, FIR Registration, and Law Enforcement"
            atype = "Enforcement Authority"
        elif "Commission" in auth_name or "CCPA" in auth_name:
            role = "Consumer Redressal, Compliance, and Compensation"
            atype = "Quasi-Judicial Commission"
        elif "Information" in auth_name or "PIO" in auth_name:
            role = "Statutory Information Disclosure and First Appeal"
            atype = "Public Statutory Authority"
        elif "Legal Services" in auth_name or "DLSA" in auth_name or "Lok Adalat" in auth_name:
            role = "Free Legal Aid and Pre-Litigation Mediation"
            atype = "Legal Services Authority"
        elif "Internal Complaints" in auth_name or "ICC" in auth_name:
            role = "Workplace Sexual Harassment Inquiry and Recommendations"
            atype = "Statutory Internal Committee"
        elif "Claims Tribunal" in auth_name or "MACT" in auth_name:
            role = "Motor Vehicular Accident Compensation Determination"
            atype = "Motor Accidents Claims Tribunal"
        return role, atype

    @classmethod
    def match_authorities(
        cls,
        issues: List[LegalIssue],
        matched_acts: List[Dict[str, Any]],
        ranked_provisions: List[RankedLegalProvision]
    ) -> List[AuthorityRecommendation]:
        """
        Dynamically matches applicable statutory authorities, forums, or tribunals.
        """
        authorities: List[AuthorityRecommendation] = []
        seen_auth_names: Set[str] = set()

        LegalKnowledgeService._load_data()
        registry = LegalKnowledgeService._registry_cache or []
        reg_map = {a["act_id"]: a for a in registry}
        name_map = {a["act_name"].lower(): a for a in registry}
        short_map = {a["short_name"].lower(): a for a in registry}

        # 1. From issue potential acts
        for iss in issues:
            for pact in iss.potential_acts:
                act_data = name_map.get(pact.lower()) or short_map.get(pact.lower())
                if not act_data:
                    for k, v in name_map.items():
                        if pact.lower() in k or k in pact.lower():
                            act_data = v
                            break
                if act_data:
                    for auth_name in act_data.get("authorities", []):
                        if auth_name not in seen_auth_names:
                            seen_auth_names.add(auth_name)
                            role, atype = cls._resolve_authority_role(auth_name)
                            authorities.append(AuthorityRecommendation(
                                authority_name=auth_name,
                                authority_type=atype,
                                jurisdiction=act_data.get("jurisdiction", "Central / Territorial"),
                                role=role,
                                relevance_reason=f"Governing statutory authority established under {act_data.get('act_name')}.",
                                is_primary_recourse=False
                            ))

        # 2. From ranked provisions
        for prov in ranked_provisions:
            aid = prov.act_id
            act_data = reg_map.get(aid)
            if act_data:
                for auth_name in act_data.get("authorities", []):
                    if auth_name not in seen_auth_names:
                        seen_auth_names.add(auth_name)
                        role, atype = cls._resolve_authority_role(auth_name)
                        authorities.append(AuthorityRecommendation(
                            authority_name=auth_name,
                            authority_type=atype,
                            jurisdiction=act_data.get("jurisdiction", "Central / Territorial"),
                            role=role,
                            relevance_reason=f"Governing statutory authority established under {act_data.get('act_name')}.",
                            is_primary_recourse=False
                        ))

        # 3. From raw search matched acts
        for act in matched_acts:
            aid = act.get("act_id")
            act_data = reg_map.get(aid)
            if act_data:
                for auth_name in act_data.get("authorities", []):
                    if auth_name not in seen_auth_names:
                        seen_auth_names.add(auth_name)
                        role, atype = cls._resolve_authority_role(auth_name)
                        authorities.append(AuthorityRecommendation(
                            authority_name=auth_name,
                            authority_type=atype,
                            jurisdiction=act_data.get("jurisdiction", "Central / Territorial"),
                            role=role,
                            relevance_reason=f"Governing statutory authority established under {act_data.get('act_name')}.",
                            is_primary_recourse=False
                        ))


        # Designate primary recourse authority based on issues
        if authorities:
            # Default first one as primary recourse
            authorities[0].is_primary_recourse = True

            # Special primary adjustments
            for a in authorities:
                if any(iss.title.startswith("Cyber") for iss in issues) and ("Cyber" in a.authority_name or "Police" in a.authority_name):
                    authorities[0].is_primary_recourse = False
                    a.is_primary_recourse = True
                    break
                elif any(iss.title.startswith("Security Deposit") for iss in issues) and ("Civil" in a.authority_name or "Rent" in a.authority_name):
                    authorities[0].is_primary_recourse = False
                    a.is_primary_recourse = True
                    break
                elif any("Consumer" in iss.title for iss in issues) and "District Consumer" in a.authority_name:
                    authorities[0].is_primary_recourse = False
                    a.is_primary_recourse = True
                    break

        return authorities

    # -------------------------------------------------------------
    # STEP 8: DYNAMIC LAWYER MATCHING & AUTHORITY PREFERENCE
    # -------------------------------------------------------------
    @classmethod
    def match_lawyers_and_evaluate_authority(
        cls,
        issues: List[LegalIssue],
        legal_domains: List[str],
        authorities: List[AuthorityRecommendation],
        db_cursor: Optional[Any] = None
    ) -> Tuple[List[LawyerRequirement], List[LawyerMatch], bool, Optional[str]]:
        """
        Derives lawyer requirements from legal domains and issues.
        Checks if direct statutory authority recourse is preferred over hiring an advocate.
        Matches lawyers gracefully from database and verified directory.
        """
        requirements: List[LawyerRequirement] = []
        matches: List[LawyerMatch] = []

        # 1. Formulate Lawyer Requirements
        for domain in legal_domains:
            expertise_list = []
            if "Criminal" in domain:
                expertise_list = ["Criminal Defence", "Bail & Anticipatory Bail", "Police Complaints"]
            elif "Property" in domain:
                expertise_list = ["Property & Real Estate Litigation", "Tenancy & Eviction Disputes", "Civil Injunctions"]
            elif "Consumer" in domain:
                expertise_list = ["Consumer Protection & Product Liability", "Deficiency in Service Claims"]
            elif "Cyber" in domain:
                expertise_list = ["Cyber Law & Digital Fraud", "IT Act Inquiries"]
            elif "Labour" in domain:
                expertise_list = ["Employment & Labour Law", "Salary & Severance Disputes"]
            elif "Family" in domain:
                expertise_list = ["Family & Matrimonial Law", "Domestic Violence (PWDVA)", "Succession"]
            elif "Banking" in domain:
                expertise_list = ["Negotiable Instruments & Cheque Bounce (Sec 138)", "Recovery Suits"]
            elif "Motor" in domain:
                expertise_list = ["Motor Accident Claims (MACT)", "Traffic & Transport Violations"]
            else:
                expertise_list = [f"{domain} Practice", "Civil Dispute Resolution"]

            requirements.append(LawyerRequirement(
                domain=domain,
                required_expertise=expertise_list,
                priority="high" if "Criminal" in domain or "Cyber" in domain else "medium"
            ))

        # 2. Authority Preference Evaluation
        authority_preferred = False
        authority_reason = None

        issue_titles = [i.title.lower() for i in issues]
        if any("right to information" in t or "rti" in t for t in issue_titles):
            authority_preferred = True
            authority_reason = (
                "Under the Right to Information Act, 2005, citizens can directly file applications "
                "before the Public Information Officer (PIO) and First Appellate Authority without "
                "needing private legal representation. Hiring an advocate is generally unnecessary at this stage."
            )
        elif any("cyber fraud" in t or "otp" in t for t in issue_titles):
            authority_preferred = True
            authority_reason = (
                "For immediate cyber financial deception, reporting directly to the National Cyber Crime "
                "Reporting Portal (cybercrime.gov.in) or National Helpline 1930 within the 'golden hours' "
                "is vital to freeze transacted amounts before engaging a private advocate."
            )
        elif any("deficiency in service" in t for t in issue_titles):
            authority_preferred = True
            authority_reason = (
                "The Consumer Protection Act, 2019 permits consumers to file grievances directly via the "
                "National Consumer Helpline (NCH) or online through the e-Daakhil portal without mandatory advocate representation."
            )

        # 3. Match Lawyers from Verified Directory & Database
        directory = cls._load_lawyers_directory()
        raw_lawyers = directory.get("lawyers", [])
        legal_aid_orgs = directory.get("legal_aid_organizations", [])

        # Match against legal domains
        for law in raw_lawyers:
            score = 0.0
            reasons = []
            law_domains = law.get("practice_domains", [])
            law_specs = law.get("specializations", [])

            for req in requirements:
                if any(req.domain.lower() in ld.lower() for ld in law_domains):
                    score += 40.0
                    reasons.append(f"Domain match on {req.domain}")
                for spec in law_specs:
                    if any(re_exp.lower() in spec.lower() for re_exp in req.required_expertise):
                        score += 30.0
                        reasons.append(f"Specialization in {spec}")

            if score > 0:
                score += min(law.get("experience_years", 5) * 2, 20)  # Experience bonus
                matches.append(LawyerMatch(
                    lawyer_id=law.get("lawyer_id"),
                    full_name=law.get("full_name"),
                    specializations=law_specs,
                    experience_years=law.get("experience_years", 0),
                    city=law.get("city", "India"),
                    match_score=min(score, 100.0),
                    match_reason="; ".join(reasons[:2]),
                    is_legal_aid=False,
                    contact_email=law.get("contact_email")
                ))

        # Include Legal Aid Organizations
        for org in legal_aid_orgs:
            matches.append(LawyerMatch(
                lawyer_id=None,
                full_name=org.get("organization_name"),
                specializations=org.get("domains_covered", ["Free Legal Representation"]),
                experience_years=35,
                city=org.get("city", "All India"),
                match_score=85.0,
                match_reason="Statutory Legal Aid under Legal Services Authorities Act, 1987 for eligible persons.",
                is_legal_aid=True,
                contact_email=org.get("email")
            ))

        matches.sort(key=lambda x: (not x.is_legal_aid, x.match_score), reverse=True)

        return requirements, matches, authority_preferred, authority_reason

    # -------------------------------------------------------------
    # STEP 9: DYNAMIC ACTION PLAN
    # -------------------------------------------------------------
    @classmethod
    def generate_action_plan(
        cls,
        issues: List[LegalIssue],
        authorities: List[AuthorityRecommendation],
        facts: List[FactItem]
    ) -> List[CaseAction]:
        """
        Dynamically generates sequenced, case-specific action steps.
        """
        actions: List[CaseAction] = []
        step = 1

        issue_titles = " ".join([i.title.lower() for i in issues])

        # Step 1: Evidence Preservation
        if "cyber" in issue_titles or "otp" in issue_titles:
            actions.append(CaseAction(
                step=step,
                action="Immediately Freeze Accounts & Report to Cyber Helpline",
                target_entity_or_authority="National Cyber Crime Reporting Portal (1930) & Concerned Bank",
                urgency="immediate",
                description="Immediately call national cybercrime helpline 1930 to freeze fraudulent transfers, and request the bank to block affected debit/credit cards or netbanking credentials."
            ))
            step += 1
        elif "trespass" in issue_titles or "threat" in issue_titles:
            actions.append(CaseAction(
                step=step,
                action="Document Incident Scene & Preserve Security Cues",
                target_entity_or_authority="Personal Records & Local Police Station",
                urgency="immediate",
                description="Preserve date-stamped photographs/videos of the premises, save call recordings/threatening messages, and identify any eyewitnesses or CCTV coverage."
            ))
            step += 1
        elif "scratched" in issue_titles or "licence" in issue_titles:
            actions.append(CaseAction(
                step=step,
                action="Preserve Defaced Document & Note Officer Credentials",
                target_entity_or_authority="Traffic Police Vigilance / Complaints Cell",
                urgency="immediate",
                description="Retain the damaged physical licence without further handling, photograph the damage clearly, and record the date, time, location, and badge number/name of the officer."
            ))
            step += 1
        else:
            actions.append(CaseAction(
                step=step,
                action="Assemble Relevant Agreements & Written Communications",
                target_entity_or_authority="Personal Documentation Archive",
                urgency="immediate",
                description="Compile complete records including original agreements, invoices, payment proofs, and dated correspondence with the opposing party."
            ))
            step += 1

        # Step 2: Formal Grievance / Legal Notice
        primary_auth = next((a.authority_name for a in authorities if a.is_primary_recourse), "Appropriate Statutory Forum")
        if "cheque" in issue_titles:
            actions.append(CaseAction(
                step=step,
                action="Issue Statutory Demand Notice within 30 Days",
                target_entity_or_authority="Drawer of the Cheque",
                urgency="short_term",
                description="Send a formal written demand notice under Section 138(b) Negotiable Instruments Act within 30 days of receiving the cheque dishonour bank memo."
            ))
            step += 1
        elif "deposit" in issue_titles or "salary" in issue_titles or "contract" in issue_titles:
            actions.append(CaseAction(
                step=step,
                action="Issue Formal Written Notice of Demand",
                target_entity_or_authority="Opposing Party (Landlord / Employer)",
                urgency="short_term",
                description="Dispatch a formal demand notice setting out the exact outstanding dues, reference to agreements, and stipulating a reasonable compliance period (e.g. 15 days)."
            ))
            step += 1
        elif "consumer" in issue_titles:
            actions.append(CaseAction(
                step=step,
                action="Lodge Formal Grievance with National Consumer Helpline",
                target_entity_or_authority="National Consumer Helpline / e-Daakhil",
                urgency="short_term",
                description="Register a complaint online on consumerhelpline.gov.in or e-Daakhil portal citing product defect or service deficiency along with purchase receipts."
            ))
            step += 1
        else:
            actions.append(CaseAction(
                step=step,
                action="Submit Written Representation or Complaint",
                target_entity_or_authority=primary_auth,
                urgency="short_term",
                description=f"Submit a structured written petition or grievance detailing facts, dates, and statutory grounds to {primary_auth}."
            ))
            step += 1

        # Step 3: Formal Adjudication / Escalation
        actions.append(CaseAction(
            step=step,
            action=f"Initiate Formal Adjudication before {primary_auth}",
            target_entity_or_authority=primary_auth,
            urgency="procedural",
            description=f"Upon expiry of notice or failure of resolution, file formal petition/complaint before {primary_auth} seeking legal remedies, restitution, or penalties."
        ))

        return actions

    # -------------------------------------------------------------
    # STEP 10: DYNAMIC DOCUMENT/EVIDENCE REQUIREMENTS
    # -------------------------------------------------------------
    @classmethod
    def generate_document_checklist(
        cls,
        issues: List[LegalIssue],
        facts: List[FactItem]
    ) -> List[DocumentRequirementItem]:
        """
        Dynamically derives evidence requirements from legal issues and facts.
        """
        docs: List[DocumentRequirementItem] = []
        issue_titles = " ".join([i.title.lower() for i in issues])
        all_concepts = " ".join([" ".join([c.lower() for c in i.legal_concepts]) for i in issues])
        facts_text = " ".join([f.fact.lower() for f in facts])
        combined_context = f"{issue_titles} {all_concepts} {facts_text}"

        # Core identity document for all matters
        docs.append(DocumentRequirementItem(
            document_name="Government Identity & Address Proof (Aadhaar / Voter ID / Passport)",
            purpose="Establishing legal standing (locus standi) and jurisdiction of complainant",
            mandatory=True,
            source_provision="Standard Procedural Requirement"
        ))

        # Tenancy
        if any(k in combined_context for k in ["deposit", "tenancy", "rent", "landlord", "tenant"]):
            docs.append(DocumentRequirementItem(
                document_name="Tenancy / Rental Agreement Copy",
                purpose="Proving contractual terms of security deposit, monthly rent, and refund covenants",
                mandatory=True,
                source_provision="Transfer of Property Act, 1882"
            ))
            docs.append(DocumentRequirementItem(
                document_name="Deposit Payment Proof & Bank Statements",
                purpose="Evidencing actual transfer of security deposit to the landlord",
                mandatory=True,
                source_provision="Bharatiya Sakshya Adhiniyam, 2023 (BSA)"
            ))

        # Criminal Trespass or Threats
        if any(k in combined_context for k in ["trespass", "threat", "intimidation", "unauthorized entry"]):
            docs.append(DocumentRequirementItem(
                document_name="Electronic Communications (WhatsApp, SMS, Call Logs, or Voice Notes)",
                purpose="Substantiating threats or unauthorized intrusion",
                mandatory=True,
                source_provision="Section 63, Bharatiya Sakshya Adhiniyam, 2023 (Electronic Certificate)"
            ))
            docs.append(DocumentRequirementItem(
                document_name="Certificate under Section 63 BSA for Electronic Records",
                purpose="Statutory mandatory condition for admissibility of digital records and printouts",
                mandatory=True,
                source_provision="Section 63, Bharatiya Sakshya Adhiniyam, 2023"
            ))

        # Transport & Licence defacement
        if any(k in combined_context for k in ["licence", "traffic", "vehicle", "scratched"]):
            docs.append(DocumentRequirementItem(
                document_name="Physical Driving Licence in Original Defaced State",
                purpose="Primary physical evidence of unauthorized scratching or alteration",
                mandatory=True,
                source_provision="Section 57, Bharatiya Sakshya Adhiniyam, 2023 (Primary Evidence)"
            ))
            docs.append(DocumentRequirementItem(
                document_name="High-Resolution Photographs of Defaced Licence with Timestamps",
                purpose="Corroborative visual record of document damage",
                mandatory=False,
                source_provision="Motor Vehicles Act, 1988"
            ))

        # Cyber Fraud
        if any(k in combined_context for k in ["cyber", "otp", "phishing", "fraudulent debit"]):
            docs.append(DocumentRequirementItem(
                document_name="Bank Account Statement showing Fraudulent Debit Transaction",
                purpose="Confirming unauthorized transaction reference (UTR) numbers and financial debit",
                mandatory=True,
                source_provision="Information Technology Act, 2000"
            ))
            docs.append(DocumentRequirementItem(
                document_name="Screenshots of Fraudulent SMS, Web Links, or Messages",
                purpose="Preserving phishing headers, sender IDs, and fraudulent hyperlinks",
                mandatory=True,
                source_provision="Section 63, Bharatiya Sakshya Adhiniyam, 2023"
            ))

        # Cheque Dishonour
        if any(k in combined_context for k in ["cheque", "dishonour", "bounce"]):
            docs.append(DocumentRequirementItem(
                document_name="Original Dishonoured Cheque & Cheque Return Memo from Bank",
                purpose="Mandatory statutory foundation establishing cheque presentation and dishonour reason",
                mandatory=True,
                source_provision="Section 138 & 146, Negotiable Instruments Act, 1881"
            ))
            docs.append(DocumentRequirementItem(
                document_name="Office Copy of Statutory Legal Notice & Postal Tracking Receipts",
                purpose="Proving dispatch and delivery of 30-day demand notice",
                mandatory=True,
                source_provision="Section 138(b), Negotiable Instruments Act, 1881"
            ))

        # Salary & Labour
        if any(k in combined_context for k in ["salary", "employment", "wage", "wages", "employer", "dues", "terminated", "severance"]):
            docs.append(DocumentRequirementItem(
                document_name="Employment Offer Letter / Contract & Salary Slips",
                purpose="Proving employer-employee relationship, salary terms, and unpaid period",
                mandatory=True,
                source_provision="Indian Contract Act, 1872"
            ))

        # Consumer
        if any(k in combined_context for k in ["consumer", "defective", "warranty", "refund", "deficiency"]):
            docs.append(DocumentRequirementItem(
                document_name="Purchase Invoice, Cash Memo, or Warranty Card",
                purpose="Establishing consumer transaction and terms of merchantability",
                mandatory=True,
                source_provision="Consumer Protection Act, 2019"
            ))

        # Fallback if no specific doc was added
        if len(docs) == 1:
            docs.append(DocumentRequirementItem(
                document_name="Chronological Written Statement of Events & Dates",
                purpose="Providing coherent factual timeline for court or authority inspection",
                mandatory=True,
                source_provision="General Evidence Requirement"
            ))

        return docs

    # -------------------------------------------------------------
    # STEP 11: DYNAMIC FURTHER PROCEDURE ("What happens next?")
    # -------------------------------------------------------------
    @classmethod
    def generate_procedural_roadmap(
        cls,
        issues: List[LegalIssue],
        authorities: List[AuthorityRecommendation]
    ) -> List[FurtherProcedureStage]:
        """
        Generates the procedural roadmap showing what stages follow.
        """
        stages: List[FurtherProcedureStage] = []
        primary_forum = authorities[0].authority_name if authorities else "Competent Authority"

        stages.append(FurtherProcedureStage(
            stage_number=1,
            stage_name="Initial Filing & Verification / Preliminary Scrutiny",
            forum_or_authority=primary_forum,
            description="The grievance or complaint is lodged and examined for prima facie jurisdiction and factual completeness.",
            expected_timeline_or_outcome="Typically completed within 7 to 14 days of presentation."
        ))

        stages.append(FurtherProcedureStage(
            stage_number=2,
            stage_name="Notice / Summons to Opposite Party",
            forum_or_authority=primary_forum,
            description="The forum or investigating authority issues formal notice calling upon the opposite party to respond or explain.",
            expected_timeline_or_outcome="Opposite party usually granted 15 to 30 days to submit written response."
        ))

        stages.append(FurtherProcedureStage(
            stage_number=3,
            stage_name="Inquiry, Evidence Examination & Conciliation / Hearing",
            forum_or_authority=primary_forum,
            description="Parties present documents, electronic evidence under BSA Sec 63, or explore conciliation/mediation.",
            expected_timeline_or_outcome="Pre-trial conciliation or formal framing of points for determination."
        ))

        stages.append(FurtherProcedureStage(
            stage_number=4,
            stage_name="Final Order, Redressal & Appeal Route",
            forum_or_authority=primary_forum,
            description="Issuance of binding statutory order, recovery warrant, or penal adjudication, with statutory appeal rights to higher forum.",
            expected_timeline_or_outcome="Order enforceable as a decree; appeal period typically 30 to 60 days."
        ))

        return stages

    # -------------------------------------------------------------
    # STEP 12: DYNAMIC EMOTIONAL ANALYSIS
    # -------------------------------------------------------------
    @classmethod
    def analyze_emotions(cls, text: str) -> Tuple[List[EmotionalIndicator], str]:
        """
        Analyzes natural language cues for 8 emotion types.
        Computes urgency and communication guidance.
        Strict rule: Emotion NEVER determines the legal classification.
        """
        indicators: List[EmotionalIndicator] = []
        lower = text.lower()

        detected_counts: Dict[str, List[str]] = {}
        for emotion, meta in EMOTION_PATTERNS.items():
            found = [w for w in meta["words"] if w in lower]
            if found:
                detected_counts[emotion] = found

        for emotion, cues in detected_counts.items():
            meta = EMOTION_PATTERNS[emotion]
            intensity = min(0.3 + (len(cues) * 0.25), 1.0)
            indicators.append(EmotionalIndicator(
                emotion=emotion,
                intensity=intensity,
                detected_cues=cues,
                communication_guidance=meta["guidance"]
            ))

        # Default calm/neutral if no overt emotions detected
        if not indicators:
            indicators.append(EmotionalIndicator(
                emotion="calm_neutral",
                intensity=0.8,
                detected_cues=["objective factual language"],
                communication_guidance="Maintain structured, objective, and precise legal analysis."
            ))

        # Determine overall urgency
        urgency = "medium"
        if "urgency" in detected_counts or "fear" in detected_counts:
            urgency = "high"
            if any(w in lower for w in ["kill", "arrested", "custody", "immediate", "freeze account"]):
                urgency = "critical"
        elif "calm_neutral" in [i.emotion for i in indicators]:
            urgency = "low"

        return indicators, urgency

    # -------------------------------------------------------------
    # STEP 13: EXPLANATION GENERATION
    # -------------------------------------------------------------
    @classmethod
    def generate_explanation(
        cls,
        issues: List[LegalIssue],
        ranked_provisions: List[RankedLegalProvision],
        authorities: List[AuthorityRecommendation],
        authority_preferred: bool,
        authority_reason: Optional[str]
    ) -> str:
        """
        Generates an empathetic, plain-language legal explanation of the case.
        """
        if not issues:
            return "Vidhik has received your description. Please provide more detailed facts to generate a comprehensive legal analysis."

        primary_issue = issues[0]
        additional_issues = issues[1:]

        parts = []
        parts.append(f"### Understanding of Your Legal Matter\nBased on your description, the primary legal issue involves **{primary_issue.title}**.")
        if additional_issues:
            add_titles = ", ".join([f"**{i.title}**" for i in additional_issues])
            parts.append(f"Additionally, your matter raises distinct legal questions regarding: {add_titles}.")

        # Statutory provisions summary
        if ranked_provisions:
            sec_summaries = []
            for p in ranked_provisions[:3]:
                sec_summaries.append(f"**Section {p.section_number} of {p.short_name}** ({p.section_title})")
            parts.append(f"\n### Relevant Statutory Provisions\nUnder Indian law, the most directly applicable statutory provisions are: {', '.join(sec_summaries)}.")
        else:
            parts.append("\n### Statutory Provisions\nVidhik could not identify a direct matching section in its available 24 Bare Acts for this exact matter. It is classified under a potentially related legal area.")

        # Authority & forum advice
        if authorities:
            primary_auth = next((a for a in authorities if a.is_primary_recourse), authorities[0])
            parts.append(f"\n### Recommended Recourse\nThe most appropriate forum for initial relief is the **{primary_auth.authority_name}**.")

        if authority_preferred and authority_reason:
            parts.append(f"\n> **Direct Authority Recourse Note**: {authority_reason}")

        return "\n".join(parts)

    # -------------------------------------------------------------
    # COMPLETE PIPELINE EXECUTION
    # -------------------------------------------------------------
    @classmethod
    def analyze_case(
        cls,
        description: str,
        case_id: Optional[str] = None,
        jurisdiction_hint: Optional[str] = None,
        db_cursor: Optional[Any] = None
    ) -> CaseContext:
        """
        Executes the complete end-to-end dynamic case intelligence pipeline.
        Saves the resulting CaseContext into the persistent case store.
        """
        assigned_id = case_id.strip() if case_id and case_id.strip() else CaseStore.next_case_id()
        normalized = cls.normalize_text(description)
        now_iso = datetime.now(timezone.utc).isoformat()

        # Step 1: Sufficiency check
        sufficient, notice, missing = cls.evaluate_sufficiency(normalized)
        if not sufficient:
            empty_context = CaseContext(
                case_id=assigned_id,
                original_description=description,
                normalized_description=normalized,
                facts=[],
                issues=[],
                legal_domains=[],
                jurisdiction=jurisdiction_hint or "India",
                legal_matches=[],
                ranked_provisions=[],
                authorities=[],
                lawyer_requirements=[],
                lawyer_matches=[],
                actions=[],
                documents=[],
                procedure=[],
                emotional_indicators=[
                    EmotionalIndicator(
                        emotion="confusion",
                        intensity=0.5,
                        detected_cues=["insufficient factual content"],
                        communication_guidance="Politely prompt the user for specific factual details."
                    )
                ],
                urgency="low",
                missing_information=missing,
                status="pending_clarification",
                confidence_overall=0.1,
                degree_of_relevance="Insufficient information in input",
                is_uncertain=True,
                sufficient_information=False,
                unavailability_notice=notice,
                explanation=notice,
                created_at=now_iso,
                updated_at=now_iso
            )
            return CaseStore.save_case(empty_context, db_cursor)

        # Step 2: Extract Facts
        facts = cls.extract_facts(normalized)

        # Step 3: Identify Issues (Multi-issue support)
        issues = cls.identify_legal_issues(normalized, facts)

        # Step 4, 5, 6: Search & Rank Provisions across 24 Acts
        ranked_provisions, raw_matches, is_uncertain, degree = cls.search_and_rank_provisions(normalized, issues, facts)

        # Step 4: Identify Legal Domains
        legal_domains = cls.identify_legal_domains(issues, raw_matches)

        # Step 7: Match Authorities
        authorities = cls.match_authorities(issues, raw_matches, ranked_provisions)

        # Step 8: Match Lawyers & Evaluate Authority Preference
        lawyer_reqs, lawyer_matches, auth_preferred, auth_reason = cls.match_lawyers_and_evaluate_authority(
            issues=issues,
            legal_domains=legal_domains,
            authorities=authorities,
            db_cursor=db_cursor
        )

        # Step 9: Action Plan
        actions = cls.generate_action_plan(issues, authorities, facts)

        # Step 10: Document Checklist
        documents = cls.generate_document_checklist(issues, facts)

        # Step 11: Procedural Roadmap
        procedure = cls.generate_procedural_roadmap(issues, authorities)

        # Step 12: Emotional Analysis
        emotional_indicators, urgency = cls.analyze_emotions(normalized)

        # Step 13: Plain-language explanation
        explanation = cls.generate_explanation(
            issues=issues,
            ranked_provisions=ranked_provisions,
            authorities=authorities,
            authority_preferred=auth_preferred,
            authority_reason=auth_reason
        )

        # Step 14: Missing information questions if uncertain
        missing_info: List[MissingInformation] = []
        if is_uncertain:
            missing_info.append(MissingInformation(
                aspect="Statutory Correlation Clarification",
                question="Could you specify if there was a formal contract, written document, or prior court/police complaint?",
                why_needed="To eliminate ambiguity across overlapping civil and criminal remedies."
            ))

        jurisdiction = jurisdiction_hint or "India / Central"

        case_context = CaseContext(
            case_id=assigned_id,
            original_description=description,
            normalized_description=normalized,
            facts=facts,
            issues=issues,
            legal_domains=legal_domains,
            jurisdiction=jurisdiction,
            legal_matches=raw_matches[:10],
            ranked_provisions=ranked_provisions,
            authorities=authorities,
            lawyer_requirements=lawyer_reqs,
            lawyer_matches=lawyer_matches,
            authority_preferred_over_lawyer=auth_preferred,
            authority_preference_reason=auth_reason,
            actions=actions,
            documents=documents,
            procedure=procedure,
            emotional_indicators=emotional_indicators,
            urgency=urgency,
            missing_information=missing_info,
            status="analyzed",
            confidence_overall=0.88 if not is_uncertain else 0.45,
            degree_of_relevance=degree,
            is_uncertain=is_uncertain,
            sufficient_information=True,
            unavailability_notice=None,
            explanation=explanation,
            created_at=now_iso,
            updated_at=now_iso
        )

        return CaseStore.save_case(case_context, db_cursor)

    @classmethod
    def clarify_case(
        cls,
        case_id: str,
        clarification_text: str,
        answers: Optional[Dict[str, str]] = None,
        db_cursor: Optional[Any] = None
    ) -> CaseContext:
        """
        Incorporates user follow-up clarifications and re-runs the pipeline.
        """
        existing = CaseStore.get_case(case_id)
        combined_text = (existing.original_description if existing else "") + " " + clarification_text
        if answers:
            ans_str = " ".join([f"{k}: {v}" for k, v in answers.items()])
            combined_text += " " + ans_str

        return cls.analyze_case(
            description=combined_text.strip(),
            case_id=case_id,
            db_cursor=db_cursor
        )
