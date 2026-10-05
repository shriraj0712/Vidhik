import re
import time
from typing import List, Dict, Any, Optional
from app.schemas.authority import (
    AuthorityRecommendationRequest,
    AuthorityRecommendationResponse,
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

        return AuthorityRecommendationResponse(
            primary_authority=config["primary"],
            alternative_authorities=config["alternatives"],
            reasoning=reason,
            confidence=0.92,
            escalation_hierarchy=config["escalation"],
            metadata={"latency_ms": round((time.time() - start_time) * 1000, 2), "state_applied": request.state_or_ut}
        )
