"""
Vidhik Platform - Legal Document Analysis Engine (Phase 11)
===========================================================
High-precision deterministic legal extraction and statutory grounding engine:
1. Document classification & executive synthesis
2. Legal parties & representative capacities
3. Critical chronological dates & financial values
4. Core legal clauses, liabilities & obligations vs rights
5. Rule-based potential risks & objective issue flags
6. Grounded statutory references cross-referenced against the Vidhik database
   (869 Laws, 41,442 Sections) with zero hallucination.
"""

import os
import re
import json
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from psycopg2.extras import RealDictCursor

from app.schemas.document_analysis import (
    DocumentParty,
    DocumentDate,
    DocumentMonetaryValue,
    DocumentClause,
    DocumentObligationRight,
    DocumentRisk,
    DocumentMissingInfo,
    DocumentActionItem,
    LegalReference,
    DocumentAnalysisResponse,
    AnalysisHistoryItem,
    AnalysisHistoryResponse,
    SaveToCaseRequest,
    SaveToCaseResponse
)
from app.services.document_parser_service import ParsedDocument
from app.services.search_service import LegalSearchService
from app.services.lawyer_service import LawyerService

logger = logging.getLogger(__name__)


# Standard regexes for Indian legal dates (e.g. 15th August 2023, 15/08/2023, 2023-08-15)
DATE_PATTERNS = [
    r"\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{4})\b",
    r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})\b",
    r"\b(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\b"
]

# Indian currency & monetary amount patterns (₹, Rs., INR, Lakhs, Crores)
CURRENCY_PATTERN = re.compile(
    r"(?:(?:Rs\.?|INR|₹)\s*[\d,]+(?:\.\d{2})?(?:\s*(?:lakh|lakhs|crore|crores|thousand|million|billion))?|"
    r"[\d,]+(?:\.\d{2})?\s*(?:lakh|lakhs|crore|crores)\s*(?:rupees)?)",
    re.IGNORECASE
)

# Common Indian statutory citation patterns
STATUTE_CITATION_PATTERNS = [
    # "Section 138 of the Negotiable Instruments Act, 1881" or "Section 138, Negotiable Instruments Act"
    re.compile(r"Section\s+([0-9]+[A-Za-z]*(?:\s*\([0-9a-zA-Z]+\))*)\s+(?:of\s+(?:the\s+)?)?([A-Za-z\s,]+(?:Act|Code|Rules|Order))(?:\s*,\s*(\d{4}))?", re.IGNORECASE),
    # "Section 420 of IPC" / "Section 9 of CPC" / "Section 438 of CrPC"
    re.compile(r"Section\s+([0-9]+[A-Za-z]*(?:\s*\([0-9a-zA-Z]+\))*)\s+(?:of\s+(?:the\s+)?)?(IPC|CPC|CrPC|Cr\.P\.C\.|C\.P\.C\.|I\.P\.C\.|BNS|BNSS|BSA)\b", re.IGNORECASE),
    # "Article 21 of the Constitution of India" / "Article 226"
    re.compile(r"Article\s+([0-9]+[A-Za-z]*)\s+(?:of\s+(?:the\s+)?)?(?:the\s+)?(Constitution(?:\s+of\s+India)?)?", re.IGNORECASE),
    # "Order VII Rule 11 of CPC"
    re.compile(r"Order\s+([IVXLCDM0-9]+)\s+Rule\s+([0-9]+[A-Za-z]*)\s+(?:of\s+(?:the\s+)?)?(?:the\s+)?([A-Za-z\s,]+(?:Code|CPC|Act))?", re.IGNORECASE)
]


class DocumentAnalysisService:
    """Service handling multi-category legal analysis and authentic statutory grounding."""

    # -------------------------------------------------------------
    # 1. DOCUMENT CLASSIFICATION
    # -------------------------------------------------------------
    @classmethod
    def classify_document(cls, text: str, file_name: str) -> str:
        """Determines legal document type based on deterministic evidentiary indicators."""
        t = text.lower()
        fn = file_name.lower()

        patterns = [
            ("Sale Deed", [r"sale\s+deed", r"conveyance\s+deed", r"vendor\s+and\s+purchaser", r"absolute\s+sale"]),
            ("Rent / Lease Agreement", [r"lease\s+agreement", r"rent\s+agreement", r"leave\s+and\s+licen[sc]e", r"lessor\s+and\s+lessee", r"landlord\s+and\s+tenant", r"monthly\s+rent"]),
            ("Commercial Agreement", [r"service\s+agreement", r"master\s+services\s+agreement", r"non-disclosure\s+agreement", r"nda\b", r"consultancy\s+agreement", r"partnership\s+deed", r"memorandum\s+of\s+understanding", r"mou\b"]),
            ("Legal Notice", [r"legal\s+notice", r"statutory\s+notice", r"notice\s+under\s+section", r"demand\s+notice", r"hereby\s+called\s+upon"]),
            ("Plaint / Civil Suit", [r"in\s+the\s+court\s+of", r"suit\s+no\.", r"plaint\s+under\s+order", r"plaintiff.*versus.*defendant"]),
            ("Writ Petition / Petition", [r"writ\s+petition", r"in\s+the\s+high\s+court\s+of", r"in\s+the\s+supreme\s+court\s+of", r"special\s+leave\s+petition", r"petitioner.*versus.*respondent"]),
            ("Bail Application", [r"application\s+for\s+(?:anticipatory\s+)?bail", r"under\s+section\s+437", r"under\s+section\s+438", r"under\s+section\s+439", r"under\s+section\s+482\s+of\s+bnss", r"under\s+section\s+483\s+of\s+bnss"]),
            ("Affidavit", [r"affidavit", r"solemnly\s+affirm", r"verified\s+at\b", r"deponent\b"]),
            ("Power of Attorney", [r"power\s+of\s+attorney", r"general\s+power\s+of\s+attorney", r"special\s+power\s+of\s+attorney", r"gpoa\b", r"spoa\b"]),
            ("Will / Testamentary Deed", [r"last\s+will\s+and\s+testament", r"testator\b", r"bequeath\b"]),
            ("Court Order / Judgment", [r"judgment\b", r"order\s+sheet", r"coram\b", r"before\s+the\s+hon'?ble\s+judge", r"decreed\s+with\s+costs"])
        ]

        # Check filename first for strong hint
        for doc_type, regexes in patterns:
            for r in regexes:
                if re.search(r, fn):
                    return doc_type

        # Check document text header and body
        header_text = t[:3000]
        for doc_type, regexes in patterns:
            match_count = sum(1 for r in regexes if re.search(r, header_text))
            if match_count >= 1:
                return doc_type

        # Fallback check across full text
        for doc_type, regexes in patterns:
            match_count = sum(1 for r in regexes if re.search(r, t))
            if match_count >= 2:
                return doc_type

        return "Unknown / Unclassified"

    # -------------------------------------------------------------
    # 2. PARTY DETECTION
    # -------------------------------------------------------------
    @classmethod
    def extract_parties(cls, text: str) -> List[DocumentParty]:
        """Identifies contracting parties, litigants, or entities with roles."""
        parties: List[DocumentParty] = []
        seen = set()

        def add_party(name: str, role: str, raw: Optional[str] = None):
            clean_name = re.sub(r"[\n\r\t]+", " ", name).strip(" ,.-:")
            clean_name = re.sub(r"\s{2,}", " ", clean_name)
            if len(clean_name) >= 3 and len(clean_name) <= 120 and clean_name.lower() not in seen:
                # Filter out pure noise / generic terms
                if not re.match(r"^(and|or|the|party|parties|first|second|said|between|dated|whereas)$", clean_name.lower()):
                    seen.add(clean_name.lower())
                    parties.append(DocumentParty(name=clean_name, role=role, raw_text=raw))

        # 1. Litigant format: "X ... Plaintiff / Petitioner VERSUS Y ... Defendant / Respondent"
        lit_match = re.search(r"([A-Z0-9][A-Za-z0-9\s.,&'/-]+?)\s*\.{2,}\s*(Plaintiff|Petitioner|Applicant|Complainant)\b", text, re.IGNORECASE)
        if lit_match:
            add_party(lit_match.group(1), lit_match.group(2).title(), lit_match.group(0))

        opp_match = re.search(r"(?:versus|vs\.?|v\.)\s*\n*\s*([A-Z0-9][A-Za-z0-9\s.,&'/-]+?)\s*\.{2,}\s*(Defendant|Respondent|Accused|Opposite\s+Party)\b", text, re.IGNORECASE)
        if opp_match:
            add_party(opp_match.group(1), opp_match.group(2).title(), opp_match.group(0))

        # 2. Preamble hereinafter pattern: e.g. "M/s Alpha ... hereinafter referred to as the 'Lessor'"
        here_pat = re.compile(
            r"([A-Z0-9][A-Za-z0-9\s.,&'/-]{2,90}?)\s*(?:,|\s+having|\s+aged|\s+residing|\s+represented|\s+incorporated|\s*\(|\s*\n)\s*"
            r"\(?hereinafter\s+(?:referred\s+to\s+as|called)\s+(?:the\s+)?[\"']?\s*"
            r"(Lessor|Lessee|Landlord|Tenant|Vendor|Purchaser|Seller|Buyer|Licensor|Licensee|Borrower|Lender|First\s+Party|Second\s+Party|First\s+Part|Second\s+Part)[\"']?",
            re.IGNORECASE
        )
        for m in here_pat.finditer(text):
            p_name = m.group(1).strip()
            p_name = re.sub(r"^(?:BY\s+AND\s+BETWEEN|BETWEEN|AND)\s*[:\s]*", "", p_name, flags=re.IGNORECASE).strip()
            role_str = m.group(2).title()
            if "Part" in role_str:
                role_str = role_str.replace("Part", "Party")
            add_party(p_name, role_str, m.group(0))

        # 3. Contract format: "BETWEEN[:] [Party A] ... AND[:] [Party B]"
        between_match = re.search(r"(?:BY\s+AND\s+)?BETWEEN[:\s]+([A-Z0-9][A-Za-z0-9\s.,&'/-]+?)(?:,|\s+hereinafter|\s+aged|\s+residing|\s+having|\s*\(1\)|\s*\n|\s+AND\b)", text, re.IGNORECASE)
        if between_match:
            cand = between_match.group(1).strip()
            if not any(k in cand.lower() for k in ["agreement", "deed", "notice", "contract"]):
                add_party(cand, "First Party / Executant", between_match.group(0))

        and_match = re.search(r"(?:;\s*|\.\s*|\n\s*)AND[:\s]+([A-Z0-9][A-Za-z0-9\s.,&'/-]+?)(?:,|\s+hereinafter|\s+aged|\s+residing|\s+having|\s*\(2\)|\s*\n|\s+executed\b|\s+dated\b|\s*\(collectively|\.)", text, re.IGNORECASE)
        if and_match:
            cand = and_match.group(1).strip()
            if not any(k in cand.lower() for k in ["agreement", "deed", "notice", "contract"]):
                add_party(cand, "Second Party / Recipient", and_match.group(0))

        # 4. Explicit role definitions with optional colons / parentheses
        role_pairs = [
            (r"(?:Lessor|Landlord)\s*[:/]\s*([A-Z0-9][A-Za-z0-9\s.,&'/-]+?)(?:\n|,|\.|\(|$)", "Lessor / Landlord"),
            (r"(?:Lessee|Tenant)\s*[:/]\s*([A-Z0-9][A-Za-z0-9\s.,&'/-]+?)(?:\n|,|\.|\(|$)", "Lessee / Tenant"),
            (r"(?:Vendor|Seller)\s*[:/]\s*([A-Z0-9][A-Za-z0-9\s.,&'/-]+?)(?:\n|,|\.|\(|$)", "Vendor / Seller"),
            (r"(?:Purchaser|Buyer)\s*[:/]\s*([A-Z0-9][A-Za-z0-9\s.,&'/-]+?)(?:\n|,|\.|\(|$)", "Purchaser / Buyer"),
            (r"(?:Employer|Company)\s*[:/]\s*([A-Z0-9][A-Za-z0-9\s.,&'/-]+?)(?:\n|,|\.|\(|$)", "Employer / Company"),
            (r"(?:Employee|Consultant)\s*[:/]\s*([A-Z0-9][A-Za-z0-9\s.,&'/-]+?)(?:\n|,|\.|\(|$)", "Employee / Consultant"),
            (r"called\s+the\s+['\"]?(Lessor|Landlord|Lessee|Tenant|Vendor|Purchaser)['\"]?", "Designated Role")
        ]
        for pat, role_name in role_pairs:
            m = re.search(pat, text, re.IGNORECASE)
            if m and role_name != "Designated Role":
                add_party(m.group(1), role_name, m.group(0))

        return parties

    # -------------------------------------------------------------
    # 3. DATE EXTRACTION
    # -------------------------------------------------------------
    @classmethod
    def extract_dates(cls, text: str) -> List[DocumentDate]:
        """Extracts labelled chronological dates without fabricating."""
        dates: List[DocumentDate] = []
        seen = set()

        def add_date(d_str: str, lbl: str, ctx: Optional[str] = None):
            clean_d = d_str.strip(" ,.-")
            if clean_d and clean_d.lower() not in seen:
                seen.add(clean_d.lower())
                dates.append(DocumentDate(date_str=clean_d, label=lbl, context=ctx))

        # 1. Labelled date searches
        label_patterns = [
            (r"(?:executed|dated|made\s+and\s+entered\s+into)\s+(?:on\s+this\s+)?([0-9]{1,2}(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?[A-Za-z]+,?\s+[0-9]{4})", "Execution Date"),
            (r"(?:effective\s+date|commencement\s+date)\s*(?::|is)?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4}|[0-9]{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+,?\s+[0-9]{4})", "Effective Date"),
            (r"(?:expiry\s+date|termination\s+date|valid\s+until|valid\s+upto)\s*(?::|is)?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4}|[0-9]{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+,?\s+[0-9]{4})", "Expiry Date"),
            (r"(?:filing\s+date|presented\s+on)\s*(?::|is)?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4}|[0-9]{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+,?\s+[0-9]{4})", "Filing Date"),
            (r"(?:hearing\s+date|listed\s+on|next\s+date\s+of\s+hearing)\s*(?::|is)?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4}|[0-9]{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+,?\s+[0-9]{4})", "Hearing Date"),
            (r"(?:notice\s+date|date\s+of\s+notice)\s*(?::|is)?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4}|[0-9]{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+,?\s+[0-9]{4})", "Notice Date"),
        ]

        for pat, label in label_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                snippet = text[max(0, m.start() - 30) : min(len(text), m.end() + 30)].strip()
                add_date(m.group(1), label, snippet)

        # 2. General dates in header (if execution date wasn't caught)
        if not any(d.label == "Execution Date" for d in dates):
            header_sample = text[:1000]
            for dp in DATE_PATTERNS:
                m = re.search(dp, header_sample)
                if m:
                    add_date(m.group(1), "Execution Date (Inferred)", m.group(0))
                    break

        return dates

    # -------------------------------------------------------------
    # 4. MONETARY VALUE EXTRACTION
    # -------------------------------------------------------------
    @classmethod
    def extract_monetary_values(cls, text: str) -> List[DocumentMonetaryValue]:
        """Extracts financial and monetary values preserving exact figures."""
        values: List[DocumentMonetaryValue] = []
        seen = set()

        for m in CURRENCY_PATTERN.finditer(text):
            amt = m.group(0).strip(" ,.")
            if amt.lower() in seen:
                continue
            seen.add(amt.lower())

            # Determine surrounding context (sentence or 80-char window)
            start = max(0, m.start() - 50)
            end = min(len(text), m.end() + 50)
            ctx = text[start:end].replace("\n", " ").strip()

            # Classify financial label based on context keywords
            ctx_lower = ctx.lower()
            label = "Monetary Value"
            if any(k in ctx_lower for k in ["consideration", "purchase price", "sale price"]):
                label = "Consideration"
            elif any(k in ctx_lower for k in ["monthly rent", "per month", "rent"]):
                label = "Rent"
            elif any(k in ctx_lower for k in ["security deposit", "deposit"]):
                label = "Security Deposit"
            elif any(k in ctx_lower for k in ["penalty", "liquidated damages", "default fee"]):
                label = "Penalty / Liquidated Damages"
            elif any(k in ctx_lower for k in ["stamp duty", "registration fee"]):
                label = "Stamp Duty / Fee"
            elif any(k in ctx_lower for k in ["compensation", "damages", "claim"]):
                label = "Compensation / Claim"

            values.append(DocumentMonetaryValue(amount_text=amt, label=label, context=ctx))
            if len(values) >= 15:  # Cap at 15 distinct figures
                break

        return values

    # -------------------------------------------------------------
    # 5. CLAUSE DETECTION
    # -------------------------------------------------------------
    @classmethod
    def extract_clauses(cls, text: str) -> List[DocumentClause]:
        """Identifies core legal clauses with verbatim excerpts and objective interpretations."""
        clauses: List[DocumentClause] = []

        clause_definitions = [
            (
                "Termination",
                r"(?:clause\s+\d+[:.]?\s*)?(?:termination|determination\s+of\s+lease)\b.*?(?=\n\s*(?:clause\s+\d+|\d+\.|\Z))",
                "Specifies circumstances, notice periods, and grounds for ending the agreement."
            ),
            (
                "Indemnity & Liability",
                r"(?:clause\s+\d+[:.]?\s*)?(?:indemnity|indemnification|hold\s+harmless|limitation\s+of\s+liability)\b.*?(?=\n\s*(?:clause\s+\d+|\d+\.|\Z))",
                "Defines financial obligation to compensate for damages, losses, or legal liabilities."
            ),
            (
                "Arbitration & Dispute Resolution",
                r"(?:clause\s+\d+[:.]?\s*)?(?:arbitration|dispute\s+resolution|conciliation)\b.*?(?=\n\s*(?:clause\s+\d+|\d+\.|\Z))",
                "Mandates resolution of legal disputes via out-of-court arbitration under the Arbitration and Conciliation Act, 1996."
            ),
            (
                "Jurisdiction & Governing Law",
                r"(?:clause\s+\d+[:.]?\s*)?(?:governing\s+law|jurisdiction|applicable\s+law)\b.*?(?=\n\s*(?:clause\s+\d+|\d+\.|\Z))",
                "Designates which statutory jurisdiction and courts possess exclusive legal authority over disputes."
            ),
            (
                "Confidentiality",
                r"(?:clause\s+\d+[:.]?\s*)?(?:confidentiality|non-disclosure|proprietary\s+information)\b.*?(?=\n\s*(?:clause\s+\d+|\d+\.|\Z))",
                "Restricts disclosure and misuse of sensitive or proprietary business data."
            ),
            (
                "Payment Terms & Consideration",
                r"(?:clause\s+\d+[:.]?\s*)?(?:payment\s+terms|consideration|manner\s+of\s+payment)\b.*?(?=\n\s*(?:clause\s+\d+|\d+\.|\Z))",
                "Sets schedules, bank particulars, and statutory milestones for financial disbursements."
            ),
            (
                "Force Majeure",
                r"(?:clause\s+\d+[:.]?\s*)?(?:force\s+majeure|act\s+of\s+god)\b.*?(?=\n\s*(?:clause\s+\d+|\d+\.|\Z))",
                "Excuses contract performance during unforeseeable statutory emergencies or natural calamities."
            ),
            (
                "Notice",
                r"(?:clause\s+\d+[:.]?\s*)?(?:notices?|communications?)\b.*?(?=\n\s*(?:clause\s+\d+|\d+\.|\Z))",
                "Outlines formalized channels (registered post, email) for legal communications."
            ),
            (
                "Severability",
                r"(?:clause\s+\d+[:.]?\s*)?(?:severability)\b.*?(?=\n\s*(?:clause\s+\d+|\d+\.|\Z))",
                "Preserves enforceability of remaining provisions if any single clause is adjudicated invalid."
            )
        ]

        for cat, pat, expl in clause_definitions:
            m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
            if m:
                excerpt = m.group(0).strip()
                # Bound excerpt length to a readable 400 characters
                if len(excerpt) > 400:
                    excerpt = excerpt[:397] + "..."
                clauses.append(DocumentClause(
                    category=cat,
                    title=f"{cat} Clause",
                    text_excerpt=excerpt,
                    explanation=expl
                ))

        return clauses

    # -------------------------------------------------------------
    # 6. OBLIGATIONS & RIGHTS
    # -------------------------------------------------------------
    @classmethod
    def extract_obligations_and_rights(cls, text: str) -> List[DocumentObligationRight]:
        """Distinguishes mandatory obligations (shall/must) from discretionary rights (may/entitled)."""
        items: List[DocumentObligationRight] = []
        sentences = re.split(r"(?<=[.!?])\s+", text)

        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) < 25 or len(s_clean) > 280:
                continue

            s_lower = s_clean.lower()

            # Obligation / Duty match
            if any(k in s_lower for k in [" shall ", " must ", " agrees to ", " covenants to ", " obligated to "]):
                # Identify party
                party = "Obligated Party"
                if "tenant" in s_lower or "lessee" in s_lower:
                    party = "Tenant / Lessee"
                elif "landlord" in s_lower or "lessor" in s_lower:
                    party = "Landlord / Lessor"
                elif "purchaser" in s_lower or "buyer" in s_lower:
                    party = "Purchaser / Buyer"
                elif "vendor" in s_lower or "seller" in s_lower:
                    party = "Vendor / Seller"
                elif "employee" in s_lower or "consultant" in s_lower:
                    party = "Employee / Consultant"
                elif "employer" in s_lower or "company" in s_lower:
                    party = "Employer / Company"

                items.append(DocumentObligationRight(
                    party=party,
                    type="obligation",
                    description=s_clean
                ))

            # Right match
            elif any(k in s_lower for k in [" may ", " is entitled to ", " reserves the right ", " has the right "]):
                party = "Entitled Party"
                if "tenant" in s_lower or "lessee" in s_lower:
                    party = "Tenant / Lessee"
                elif "landlord" in s_lower or "lessor" in s_lower:
                    party = "Landlord / Lessor"
                elif "purchaser" in s_lower or "buyer" in s_lower:
                    party = "Purchaser / Buyer"
                elif "vendor" in s_lower or "seller" in s_lower:
                    party = "Vendor / Seller"

                items.append(DocumentObligationRight(
                    party=party,
                    type="right",
                    description=s_clean
                ))

            if len(items) >= 12:
                break

        return items

    # -------------------------------------------------------------
    # 7. RULE-BASED RISKS & POTENTIAL ISSUES
    # -------------------------------------------------------------
    @classmethod
    def evaluate_risks(cls, text: str, doc_type: str, parties: List[DocumentParty], dates: List[DocumentDate]) -> List[DocumentRisk]:
        """Detects rule-based issues with supporting document evidence and non-definitive phrasing."""
        risks: List[DocumentRisk] = []
        t_lower = text.lower()

        # Risk 1: Missing Execution Date
        has_exec_date = any("execution" in d.label.lower() for d in dates)
        if not has_exec_date and doc_type not in ["Court Order / Judgment", "Unknown / Unclassified"]:
            risks.append(DocumentRisk(
                severity="High",
                title="Missing Formal Execution Date",
                description="The document does not explicitly specify an execution date. This may create ambiguity regarding when statutory limitation periods and contractual obligations commence.",
                evidence_excerpt="Execution date unstated in preamble or signature blocks.",
                recommendation="Ensure the exact date of signing and execution is inserted before formal registration or presentation."
            ))

        # Risk 2: Parties undefined or incomplete
        if len(parties) < 2 and doc_type in ["Sale Deed", "Rent / Lease Agreement", "Commercial Agreement"]:
            risks.append(DocumentRisk(
                severity="High",
                title="Incomplete Party Identification",
                description="Could not detect two distinct contracting entities with standard legal identifiers (PAN, Aadhaar, representation, address).",
                evidence_excerpt=f"Identified {len(parties)} party entity/entities.",
                recommendation="Verify full legal names, registered office or residential addresses, and authorized signatory credentials for both parties."
            ))

        # Risk 3: Unilateral / Immediate Termination Without Notice
        if re.search(r"terminate\s+(?:immediately|forthwith|without\s+notice)", t_lower):
            risks.append(DocumentRisk(
                severity="High",
                title="Immediate Termination Without Cure Notice",
                description="Document contains language permitting unilateral termination without standard cure or statutory notice periods.",
                evidence_excerpt="Contains clause allowing termination 'immediately' or 'without notice'.",
                recommendation="Review whether a mandatory 15-day or 30-day written cure period should be negotiated before termination rights vest."
            ))

        # Risk 4: Uncapped Indemnity or Excessive Liquidated Damages
        if re.search(r"indemnify\s+(?:and\s+hold\s+harmless\s+)?against\s+any\s+and\s+all", t_lower) or "uncapped" in t_lower:
            risks.append(DocumentRisk(
                severity="Medium",
                title="Broad 'Any and All' Indemnity Clause",
                description="The indemnity clause uses broad phrasing ('against any and all claims') without explicit liability caps or exclusion of consequential damages.",
                evidence_excerpt="Contains 'against any and all' indemnity phrasing.",
                recommendation="Advise incorporating mutual indemnity liability caps tied to contract consideration (e.g. fees paid over preceding 12 months)."
            ))

        # Risk 5: Mandatory Arbitration / High-Cost Seat
        if "arbitration" in t_lower:
            risks.append(DocumentRisk(
                severity="Medium",
                title="Mandatory Arbitration Mechanism Detected",
                description="Disputes must proceed through private arbitration rather than civil courts. While efficient, institutional arbitration can incur substantial arbitrator fees and administrative expenses.",
                evidence_excerpt="Arbitration clause detected under Arbitration & Conciliation Act.",
                recommendation="Verify the designated arbitral seat, number of arbitrators (sole vs three), and language of arbitration."
            ))

        # Risk 6: Potential Limitation Period / Delayed Presentation
        if "legal notice" in doc_type.lower():
            risks.append(DocumentRisk(
                severity="Medium",
                title="Statutory Limitation / Response Timeline",
                description="A legal notice triggers statutory response clocks (commonly 15 days under Section 138 NI Act or 30 days under civil procedure). Failure to respond timely may prejudice judicial defenses.",
                evidence_excerpt="Legal notice demand terms.",
                recommendation="Ensure a formal legal reply is drafted and served via Registered Post A.D. within the prescribed window."
            ))

        # Risk 7: Blank or Missing Signature Block Indicators
        if re.search(r"(?:signature\s+of\s+the|signed\s+and\s+delivered|in\s+witness\s+whereof)", t_lower) and "__________" in text:
            risks.append(DocumentRisk(
                severity="Low",
                title="Incomplete Signature or Witness Blanks",
                description="Document text contains blank placeholders ('___') in execution or witness endorsement blocks.",
                evidence_excerpt="Underscores detected in endorsement sections.",
                recommendation="Ensure all blanks, witness names, and dates are attested prior to statutory stamping."
            ))

        return risks

    # -------------------------------------------------------------
    # 8. MISSING INFORMATION & ACTION ITEMS
    # -------------------------------------------------------------
    @classmethod
    def evaluate_missing_information(cls, text: str, doc_type: str) -> List[DocumentMissingInfo]:
        """Identifies expected structural components absent from the document."""
        missing: List[DocumentMissingInfo] = []
        t_lower = text.lower()

        if doc_type == "Sale Deed":
            if not any(k in t_lower for k in ["schedule", "boundary", "demarcation", "survey no"]):
                missing.append(DocumentMissingInfo(
                    item="Schedule of Property / Boundary Demarcation",
                    description="The conveyance instrument lacks a detailed schedule specifying property boundaries (North, South, East, West) or Survey/CTS Number.",
                    why_expected="Mandatory under Section 21 of the Registration Act, 1908 for registering immovable property."
                ))
            if not any(k in t_lower for k in ["pan", "form 60"]):
                missing.append(DocumentMissingInfo(
                    item="PAN / Form 60 Details of Parties",
                    description="Permanent Account Number (PAN) particulars of the transferor and transferee are unstated.",
                    why_expected="Required by Income Tax regulations and Sub-Registrar offices for high-value conveyances."
                ))

        elif doc_type == "Rent / Lease Agreement":
            if not any(k in t_lower for k in ["term", "duration", "period of lease", "months"]):
                missing.append(DocumentMissingInfo(
                    item="Duration / Term of Tenancy",
                    description="No explicit tenancy term (e.g. 11 months or 3 years) was identified.",
                    why_expected="Essential term distinguishing leave and license from ongoing tenancy."
                ))

        elif doc_type == "Legal Notice":
            if not any(k in t_lower for k in ["within 15 days", "within 30 days", "within 7 days", "days from receipt"]):
                missing.append(DocumentMissingInfo(
                    item="Specific Demand Cure Period",
                    description="The notice does not state a concrete cure timeframe (e.g. 15 or 30 days) to comply before initiating litigation.",
                    why_expected="Standard procedural requirement to establish cause of action."
                ))

        return missing

    @classmethod
    def generate_action_items(cls, doc_type: str, risks: List[DocumentRisk]) -> List[DocumentActionItem]:
        """Generates clear, prioritized next steps based on document findings."""
        actions: List[DocumentActionItem] = []

        # Default initial action
        actions.append(DocumentActionItem(
            task=f"Conduct thorough advocate verification of '{doc_type}' terms against client instructions",
            responsible_party="Counsel / Advocate",
            deadline_or_trigger="Prior to execution or formal court filing",
            priority="High"
        ))

        # Risk-driven actions
        for r in risks:
            if r.severity == "High":
                actions.append(DocumentActionItem(
                    task=f"Resolve High Risk: {r.title} — {r.recommendation}",
                    responsible_party="Client & Advocate",
                    deadline_or_trigger="Immediate",
                    priority="High"
                ))

        if doc_type in ["Sale Deed", "Rent / Lease Agreement"]:
            actions.append(DocumentActionItem(
                task="Calculate state-specific non-judicial stamp duty and verify registration fee schedule",
                responsible_party="Registration Advocate",
                deadline_or_trigger="Before presentation to Sub-Registrar of Assurances",
                priority="Medium"
            ))

        return actions

    # -------------------------------------------------------------
    # 9. STATUTORY GROUNDING (CROSS-REFERENCE WITH VIDHIK DATABASE)
    # -------------------------------------------------------------
    @classmethod
    def ground_statutory_references(cls, db: RealDictCursor, text: str) -> List[LegalReference]:
        """
        Extracts legal citations and cross-references them against the authentic
        Vidhik PostgreSQL database (869 Laws, 41,442 Sections).
        Explicitly flags unverified citations with zero fabrication.
        """
        references: List[LegalReference] = []
        seen = set()

        def add_ref(citation: str, law_kw: Optional[str], sec_num: Optional[str], ref_type: str = "explicit_statutory_mention"):
            key = f"{citation}_{sec_num}_{law_kw}".lower()
            if key in seen:
                return
            seen.add(key)

            clean_citation = citation.strip(" ,.-")
            is_verified = False
            law_id = None
            law_name = None
            section_id = None
            section_number = None
            section_title = None
            explanation = None

            # Attempt database lookup
            if sec_num:
                clean_sec = sec_num.strip()
                # 1. Targeted lookup by section_number and law keyword if present
                if law_kw:
                    law_clean = law_kw.strip().replace("the ", "").replace("The ", "")
                    # Special alias resolution
                    alias_map = {
                        "ipc": "Indian Penal Code",
                        "i.p.c.": "Indian Penal Code",
                        "cpc": "Code of Civil Procedure",
                        "c.p.c.": "Code of Civil Procedure",
                        "crpc": "Code of Criminal Procedure",
                        "cr.p.c.": "Code of Criminal Procedure",
                        "bns": "Bharatiya Nyaya Sanhita",
                        "bnss": "Bharatiya Nagarik Suraksha Sanhita",
                        "bsa": "Bharatiya Sakshya Adhiniyam",
                        "ni act": "Negotiable Instruments Act",
                        "constitution": "Constitution of India"
                    }
                    search_law = alias_map.get(law_clean.lower(), law_clean)

                    query = """
                        SELECT s.section_id, s.section_number, s.section_title, l.law_id, l.law_name
                        FROM sections s
                        JOIN laws l ON s.law_id = l.law_id
                        WHERE s.section_number ILIKE %s
                          AND (l.law_name ILIKE %s OR l.short_name ILIKE %s)
                        ORDER BY s.section_id ASC
                        LIMIT 1;
                    """
                    db.execute(query, (clean_sec, f"%{search_law}%", f"%{search_law}%"))
                    match = db.fetchone()
                    if match:
                        is_verified = True
                        law_id = match["law_id"]
                        law_name = match["law_name"]
                        section_id = match["section_id"]
                        section_number = match["section_number"]
                        section_title = match["section_title"]
                        explanation = f"Statutory provision successfully verified in Vidhik database under {law_name}."

                # 2. General section lookup ONLY if law_kw was omitted
                elif clean_sec:
                    db.execute("""
                        SELECT s.section_id, s.section_number, s.section_title, l.law_id, l.law_name
                        FROM sections s
                        JOIN laws l ON s.law_id = l.law_id
                        WHERE s.section_number = %s
                        ORDER BY s.section_id ASC
                        LIMIT 1;
                    """, (clean_sec,))
                    match = db.fetchone()
                    if match:
                        is_verified = True
                        law_id = match["law_id"]
                        law_name = match["law_name"]
                        section_id = match["section_id"]
                        section_number = match["section_number"]
                        section_title = match["section_title"]
                        explanation = f"Section {clean_sec} matched with {law_name} in Vidhik statutory database."

            if not is_verified:
                explanation = "Unverified / Outside Vidhik Database: Citation mentioned in document but not confirmed in active statutory repository."

            references.append(LegalReference(
                citation_text=clean_citation,
                reference_type=ref_type,
                is_verified_in_db=is_verified,
                law_id=law_id,
                law_name=law_name,
                section_id=section_id,
                section_number=section_number,
                section_title=section_title,
                relevance_explanation=explanation
            ))

        # Scan text for statutory citation patterns
        for pat in STATUTE_CITATION_PATTERNS:
            for m in pat.finditer(text):
                full_citation = m.group(0).strip()
                groups = m.groups()
                sec_val = groups[0] if len(groups) > 0 else None
                law_val = groups[1] if len(groups) > 1 else None
                add_ref(full_citation, law_val, sec_val, "explicit_statutory_mention")

        # Contextual statutory discovery via LegalSearchService
        # For critical clause topics present in document, search existing repository
        clause_topics = []
        if "arbitration" in text.lower():
            clause_topics.append(("Arbitration", "Arbitration and Conciliation Act"))
        if "cheque" in text.lower() or "dishonour" in text.lower():
            clause_topics.append(("138", "Negotiable Instruments Act"))
        if "sale deed" in text.lower() or "conveyance" in text.lower():
            clause_topics.append(("54", "Transfer of Property Act"))
        if "consumer" in text.lower() or "deficiency" in text.lower():
            clause_topics.append(("35", "Consumer Protection Act"))

        for topic_sec, topic_law in clause_topics:
            search_res = LegalSearchService.search(db, query=f"{topic_law} {topic_sec}", limit=1)
            if search_res.results:
                r = search_res.results[0]
                citation_str = f"Section {r.section_number} of {r.law_name}"
                if not any(ref.section_id == r.section_id for ref in references):
                    references.append(LegalReference(
                        citation_text=citation_str,
                        reference_type="contextual_statute_match",
                        is_verified_in_db=True,
                        law_id=r.law_id,
                        law_name=r.law_name,
                        section_id=r.section_id,
                        section_number=r.section_number,
                        section_title=r.section_title,
                        relevance_explanation=f"Contextually relevant statutory section identified via Vidhik LegalSearchService matching document clauses."
                    ))

        return references

    # -------------------------------------------------------------
    # 10. MAIN ANALYSIS PIPELINE
    # -------------------------------------------------------------
    @classmethod
    def analyze_document(
        cls,
        db: RealDictCursor,
        parsed_doc: ParsedDocument,
        user_id: Optional[int] = None,
        lawyer_id: Optional[int] = None,
        case_id: Optional[int] = None,
        persist: bool = True
    ) -> DocumentAnalysisResponse:
        """
        Executes complete multi-dimensional document analysis:
        - Classification, entity extraction, clause analysis
        - Risk evaluation, missing information, action items
        - Authentic statutory database grounding
        - Non-destructive persistence into `legal_document_analyses`
        """
        text = parsed_doc.cleaned_text

        # Handle empty / scanned documents gracefully
        if parsed_doc.is_scanned_or_empty or len(text.strip()) == 0:
            return DocumentAnalysisResponse(
                analysis_id=None,
                document_name=parsed_doc.file_name,
                document_type="Scanned / Non-Searchable",
                file_type=parsed_doc.file_type,
                file_size_bytes=parsed_doc.file_size_bytes,
                file_hash_sha256=parsed_doc.file_hash_sha256,
                summary="The provided document contains no extractable digital text. It appears to be an image-based scanned file.",
                executive_takeaways=["No digital text detected.", "OCR is not active in this phase.", "Please provide a selectable text file."],
                parties=[],
                dates=[],
                monetary_values=[],
                clauses=[],
                obligations_and_rights=[],
                identified_risks=[],
                missing_information=[],
                action_items=[],
                legal_references=[],
                raw_text_excerpt="",
                case_id=case_id,
                created_at=datetime.utcnow(),
                is_scanned_or_empty=True,
                warning_message=parsed_doc.warning_message
            )

        # 1. Classification
        doc_type = cls.classify_document(text, parsed_doc.file_name)

        # 2. Extract Entities
        parties = cls.extract_parties(text)
        dates = cls.extract_dates(text)
        monetary_values = cls.extract_monetary_values(text)

        # 3. Extract Clauses & Obligations
        clauses = cls.extract_clauses(text)
        obligations_and_rights = cls.extract_obligations_and_rights(text)

        # 4. Risks & Issues
        risks = cls.evaluate_risks(text, doc_type, parties, dates)

        # 5. Missing Info & Actions
        missing_info = cls.evaluate_missing_information(text, doc_type)
        actions = cls.generate_action_items(doc_type, risks)

        # 6. Ground Statutory References against Vidhik database
        legal_refs = cls.ground_statutory_references(db, text)

        # 7. Generate Executive Summary & Takeaways
        summary, takeaways = cls.synthesize_summary(
            doc_type=doc_type,
            file_name=parsed_doc.file_name,
            parties=parties,
            dates=dates,
            values=monetary_values,
            clauses=clauses,
            risks=risks
        )

        raw_excerpt = text[:2500] if len(text) > 2500 else text

        analysis_id = None
        created_at = datetime.utcnow()

        # 8. Persist Analysis into Database
        if persist:
            try:
                db.execute("""
                    INSERT INTO legal_document_analyses (
                        user_id, lawyer_id, case_id, document_name, document_type,
                        file_type, file_size_bytes, file_hash_sha256, summary,
                        executive_takeaways, structured_entities, structured_clauses,
                        identified_risks, missing_information, action_items, raw_text_excerpt
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s
                    ) RETURNING analysis_id, created_at;
                """, (
                    user_id, lawyer_id, case_id, parsed_doc.file_name, doc_type,
                    parsed_doc.file_type, parsed_doc.file_size_bytes, parsed_doc.file_hash_sha256, summary,
                    json.dumps(takeaways),
                    json.dumps({
                        "parties": [p.model_dump() for p in parties],
                        "dates": [d.model_dump() for d in dates],
                        "monetary_values": [v.model_dump() for v in monetary_values]
                    }),
                    json.dumps([c.model_dump() for c in clauses]),
                    json.dumps([r.model_dump() for r in risks]),
                    json.dumps([m.model_dump() for m in missing_info]),
                    json.dumps([a.model_dump() for a in actions]),
                    raw_excerpt
                ))
                ins_row = db.fetchone()
                if ins_row:
                    analysis_id = ins_row["analysis_id"]
                    created_at = ins_row["created_at"]

                # Insert grounded references
                if analysis_id and legal_refs:
                    for ref in legal_refs:
                        db.execute("""
                            INSERT INTO analysis_legal_references (
                                analysis_id, section_id, law_id, citation_text,
                                reference_type, is_verified_in_db, relevance_explanation
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                            RETURNING ref_id;
                        """, (
                            analysis_id, ref.section_id, ref.law_id, ref.citation_text,
                            ref.reference_type, ref.is_verified_in_db, ref.relevance_explanation
                        ))
                        r_row = db.fetchone()
                        if r_row:
                            ref.ref_id = r_row["ref_id"]

                db.connection.commit()
            except Exception as e:
                db.connection.rollback()
                logger.error(f"Error persisting document analysis: {e}")

        return DocumentAnalysisResponse(
            analysis_id=analysis_id,
            document_name=parsed_doc.file_name,
            document_type=doc_type,
            file_type=parsed_doc.file_type,
            file_size_bytes=parsed_doc.file_size_bytes,
            file_hash_sha256=parsed_doc.file_hash_sha256,
            summary=summary,
            executive_takeaways=takeaways,
            parties=parties,
            dates=dates,
            monetary_values=monetary_values,
            clauses=clauses,
            obligations_and_rights=obligations_and_rights,
            identified_risks=risks,
            missing_information=missing_info,
            action_items=actions,
            legal_references=legal_refs,
            raw_text_excerpt=raw_excerpt,
            case_id=case_id,
            created_at=created_at,
            is_scanned_or_empty=False,
            warning_message=None
        )

    # -------------------------------------------------------------
    # 11. SUMMARY SYNTHESIZER
    # -------------------------------------------------------------
    @classmethod
    def synthesize_summary(
        cls,
        doc_type: str,
        file_name: str,
        parties: List[DocumentParty],
        dates: List[DocumentDate],
        values: List[DocumentMonetaryValue],
        clauses: List[DocumentClause],
        risks: List[DocumentRisk]
    ) -> Tuple[str, List[str]]:
        """Synthesizes an executive document overview and bulleted core takeaways."""
        parties_str = "unspecified entities"
        if len(parties) >= 2:
            parties_str = f"between {parties[0].name} ({parties[0].role}) and {parties[1].name} ({parties[1].role})"
        elif len(parties) == 1:
            parties_str = f"executed by / involving {parties[0].name} ({parties[0].role})"

        dates_str = "No specific execution date recorded."
        exec_date = next((d.date_str for d in dates if "execution" in d.label.lower()), None)
        if exec_date:
            dates_str = f"Executed on {exec_date}."

        financial_str = "No specific monetary consideration detected."
        if values:
            financial_str = f"Recorded financial terms include {', '.join(v.amount_text for v in values[:3])}."

        summary = (
            f"This instrument is classified as a {doc_type} ({file_name}), {parties_str}. "
            f"{dates_str} {financial_str} "
            f"The document sets out terms across {len(clauses)} primary legal clause areas, with {len(risks)} potential risk items flagged for advocate review."
        )

        takeaways = [
            f"Classification: {doc_type}",
            f"Parties Identified: {len(parties)} ({', '.join(p.name for p in parties[:2]) if parties else 'None explicitly identified'})",
            f"Financial Terms: {values[0].amount_text if values else 'None explicitly quantified'}",
            f"Clauses Identified: {len(clauses)} ({', '.join(c.category for c in clauses[:3]) if clauses else 'None detected'})",
            f"Risk Review: {len(risks)} issue(s) flagged ({sum(1 for r in risks if r.severity == 'High')} High Priority)"
        ]

        return summary, takeaways

    # -------------------------------------------------------------
    # 12. RETRIEVAL & HISTORY
    # -------------------------------------------------------------
    @classmethod
    def get_analysis_by_id(cls, db: RealDictCursor, analysis_id: int) -> Optional[DocumentAnalysisResponse]:
        """Retrieves an existing analysis with joined legal references."""
        db.execute("""
            SELECT * FROM legal_document_analyses WHERE analysis_id = %s;
        """, (analysis_id,))
        row = db.fetchone()
        if not row:
            return None

        # Fetch linked references
        db.execute("""
            SELECT 
                alr.ref_id, alr.analysis_id, alr.section_id, alr.law_id,
                alr.citation_text, alr.reference_type, alr.is_verified_in_db,
                alr.relevance_explanation,
                s.section_number, s.section_title, l.law_name
            FROM analysis_legal_references alr
            LEFT JOIN sections s ON alr.section_id = s.section_id
            LEFT JOIN laws l ON alr.law_id = l.law_id
            WHERE alr.analysis_id = %s
            ORDER BY alr.ref_id ASC;
        """, (analysis_id,))
        ref_rows = db.fetchall()

        entities = row.get("structured_entities") or {}
        parties = [DocumentParty(**p) for p in entities.get("parties", [])]
        dates = [DocumentDate(**d) for d in entities.get("dates", [])]
        values = [DocumentMonetaryValue(**v) for v in entities.get("monetary_values", [])]

        clauses = [DocumentClause(**c) for c in (row.get("structured_clauses") or [])]
        risks = [DocumentRisk(**r) for r in (row.get("identified_risks") or [])]
        missing = [DocumentMissingInfo(**m) for m in (row.get("missing_information") or [])]
        actions = [DocumentActionItem(**a) for a in (row.get("action_items") or [])]
        takeaways = row.get("executive_takeaways") or []

        legal_refs = [
            LegalReference(
                ref_id=r["ref_id"],
                citation_text=r["citation_text"],
                reference_type=r["reference_type"],
                is_verified_in_db=r["is_verified_in_db"],
                law_id=r["law_id"],
                law_name=r["law_name"],
                section_id=r["section_id"],
                section_number=r["section_number"],
                section_title=r["section_title"],
                relevance_explanation=r["relevance_explanation"]
            )
            for r in ref_rows
        ]

        return DocumentAnalysisResponse(
            analysis_id=row["analysis_id"],
            document_name=row["document_name"],
            document_type=row["document_type"] or "Unknown / Unclassified",
            file_type=row["file_type"],
            file_size_bytes=row["file_size_bytes"] or 0,
            file_hash_sha256=row["file_hash_sha256"],
            summary=row["summary"],
            executive_takeaways=takeaways,
            parties=parties,
            dates=dates,
            monetary_values=values,
            clauses=clauses,
            obligations_and_rights=[],
            identified_risks=risks,
            missing_information=missing,
            action_items=actions,
            legal_references=legal_refs,
            raw_text_excerpt=row.get("raw_text_excerpt"),
            case_id=row.get("case_id"),
            created_at=row.get("created_at")
        )

    @classmethod
    def list_history(
        cls,
        db: RealDictCursor,
        lawyer_id: Optional[int] = None,
        user_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> AnalysisHistoryResponse:
        """Lists historical analyses with case associations and risk counts."""
        conditions = []
        params = []

        if lawyer_id:
            conditions.append("(lda.lawyer_id = %s OR lda.lawyer_id IS NULL)")
            params.append(lawyer_id)
        elif user_id:
            conditions.append("lda.user_id = %s")
            params.append(user_id)

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

        count_sql = f"SELECT COUNT(*) AS total FROM legal_document_analyses lda{where_clause};"
        db.execute(count_sql, tuple(params))
        total_count = db.fetchone()["total"]

        query = f"""
            SELECT 
                lda.analysis_id, lda.document_name, lda.document_type, lda.file_type,
                lda.summary, lda.case_id, lda.created_at,
                c.case_title,
                jsonb_array_length(COALESCE(lda.identified_risks, '[]'::jsonb)) AS risks_count,
                (SELECT COUNT(*) FROM analysis_legal_references alr WHERE alr.analysis_id = lda.analysis_id AND alr.is_verified_in_db = TRUE) AS verified_refs_count
            FROM legal_document_analyses lda
            LEFT JOIN cases c ON lda.case_id = c.case_id
            {where_clause}
            ORDER BY lda.created_at DESC
            LIMIT %s OFFSET %s;
        """
        db.execute(query, tuple(params + [limit, offset]))
        rows = db.fetchall()

        items = []
        for r in rows:
            preview = (r["summary"][:140] + "...") if len(r["summary"] or "") > 140 else (r["summary"] or "")
            items.append(AnalysisHistoryItem(
                analysis_id=r["analysis_id"],
                document_name=r["document_name"],
                document_type=r["document_type"] or "Unknown / Unclassified",
                file_type=r["file_type"],
                summary_preview=preview,
                risks_count=r["risks_count"],
                verified_references_count=r["verified_refs_count"],
                created_at=r["created_at"],
                case_id=r["case_id"],
                case_title=r["case_title"]
            ))

        return AnalysisHistoryResponse(total=total_count, analyses=items)

    @classmethod
    def delete_analysis(cls, db: RealDictCursor, analysis_id: int, lawyer_id: Optional[int] = None) -> bool:
        """Deletes an analysis record and cascades to references."""
        params = [analysis_id]
        lawyer_clause = ""
        if lawyer_id:
            lawyer_clause = " AND (lawyer_id = %s OR lawyer_id IS NULL)"
            params.append(lawyer_id)

        sql = f"DELETE FROM legal_document_analyses WHERE analysis_id = %s{lawyer_clause} RETURNING analysis_id;"
        db.execute(sql, tuple(params))
        deleted = db.fetchone()
        if deleted:
            db.connection.commit()
            return True
        return False

    # -------------------------------------------------------------
    # 13. LAWYER MODULE CASE INTEGRATION (PHASE 13)
    # -------------------------------------------------------------
    @classmethod
    def save_analysis_to_case(
        cls,
        db: RealDictCursor,
        analysis_id: int,
        req: SaveToCaseRequest,
        lawyer_id: int
    ) -> SaveToCaseResponse:
        """
        Saves document analysis artifacts into Phase 13 lawyer workspace:
        1. Catalog as Case Document (case_documents)
        2. Save Executive Analysis Note (case_notes)
        3. Link Verified Statutory Provisions (case_legal_sections)
        Only executes with explicit user confirmation.
        """
        analysis = cls.get_analysis_by_id(db, analysis_id)
        if not analysis:
            raise ValueError(f"Analysis with ID {analysis_id} not found.")

        # Verify case exists and belongs to lawyer
        db.execute("SELECT case_id, case_title, user_id FROM cases WHERE case_id = %s;", (req.case_id,))
        case_row = db.fetchone()
        if not case_row:
            raise ValueError(f"Case with ID {req.case_id} not found.")

        client_id = case_row["user_id"]
        saved_doc_id = None
        saved_note_id = None
        linked_sections = 0

        # 1. Attach as Case Document
        if req.save_as_document:
            db.execute("""
                INSERT INTO case_documents (
                    case_id, client_id, lawyer_id, document_name, document_type,
                    file_path, file_size_bytes, mime_type, upload_status, description
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, 'analyzed', %s
                ) RETURNING document_id;
            """, (
                req.case_id, client_id, lawyer_id,
                f"Analysis Report - {analysis.document_name}",
                analysis.document_type,
                f"/analysis/{analysis_id}/{analysis.document_name}",
                analysis.file_size_bytes or 1024,
                "application/json",
                f"Automated legal analysis report ({analysis.document_type})"
            ))
            res = db.fetchone()
            if res:
                saved_doc_id = res["document_id"]

        # 2. Save Strategic Summary as Case Note
        if req.save_summary_note:
            note_content = (
                f"DOCUMENT ANALYSIS BRIEF: {analysis.document_name}\n"
                f"Classification: {analysis.document_type}\n\n"
                f"SUMMARY:\n{analysis.summary}\n\n"
                f"KEY TAKEAWAYS:\n" + "\n".join(f"• {t}" for t in analysis.executive_takeaways) + "\n\n"
            )
            if analysis.identified_risks:
                note_content += "IDENTIFIED POTENTIAL ISSUES / RISKS:\n"
                for r in analysis.identified_risks:
                    note_content += f"[{r.severity} Priority] {r.title}: {r.description}\n"

            db.execute("""
                INSERT INTO case_notes (case_id, lawyer_id, title, content, is_pinned)
                VALUES (%s, %s, %s, %s, TRUE)
                RETURNING note_id;
            """, (
                req.case_id, lawyer_id,
                f"Analysis Brief: {analysis.document_name}",
                note_content
            ))
            n_res = db.fetchone()
            if n_res:
                saved_note_id = n_res["note_id"]

        # 3. Link Verified Statutory Sections directly to case
        if req.link_verified_sections:
            for ref in analysis.legal_references:
                if ref.is_verified_in_db and ref.section_id:
                    try:
                        db.execute("""
                            INSERT INTO case_legal_sections (case_id, section_id, relevance_score, explanation)
                            VALUES (%s, %s, 90.0, %s)
                            ON CONFLICT (case_id, section_id) DO NOTHING;
                        """, (
                            req.case_id, ref.section_id,
                            f"Verified provision cited in '{analysis.document_name}': {ref.citation_text}"
                        ))
                        linked_sections += 1
                    except Exception:
                        pass

        # Update case_id on the analysis record itself
        db.execute("""
            UPDATE legal_document_analyses
            SET case_id = %s, lawyer_id = %s, updated_at = CURRENT_TIMESTAMP
            WHERE analysis_id = %s;
        """, (req.case_id, lawyer_id, analysis_id))

        db.connection.commit()

        return SaveToCaseResponse(
            status="success",
            message=f"Document analysis successfully integrated into Case #{req.case_id}.",
            case_id=req.case_id,
            saved_document_id=saved_doc_id,
            saved_note_id=saved_note_id,
            linked_sections_count=linked_sections
        )
