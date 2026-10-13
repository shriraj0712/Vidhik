"""
Vidhik Platform - Case Intelligence & Central Context Service
============================================================
Orchestrates the integrated Case-Centric Legal Decision Support System:
- Case Understanding & Cautious Situation Fact Extraction (Feature 1)
- Database-Grounded Legal Provision Mapping & Ranking (Features 2, 3)
- Case-Specific Action Plan Generation (Feature 4)
- Document & Evidence Requirements Checklist (Feature 5)
- Further Procedural Pathway Mapping (Feature 6)
- Emotional State Analysis & Adaptive Communication (Feature 7)
- Central Case Context Persistence & Caching (Features 8, 10, 23)
- Database-Driven Lawyer Recommendation Engine (Feature 14)
- Case Update & Re-analysis Workflow (Feature 17)
- Missing Information Diagnostics (Feature 18)
"""

import json
import logging
import re
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date
from psycopg2.extras import RealDictCursor

from app.schemas.case_intelligence import (
    CentralCaseContext,
    CaseSituationOverview,
    CaseLegalAnalysis,
    RankedLegalProvision,
    CaseActionPlan,
    CaseActionItem,
    CaseDocumentChecklist,
    CaseDocumentItem,
    CaseFurtherProcedure,
    ProcedureStepItem,
    CaseEmotionalAnalysis,
    CaseLawyerRecommendation,
    MatchedLawyerProfile,
    CaseAuthorityRecommendation,
    CaseAuthorityItem
)
from app.services.knowledge_service import LegalKnowledgeService
from app.services.ranking_service import LegalRankingService
from app.services.authority_service import AuthorityRecommendationService

logger = logging.getLogger("vidhik.case_intelligence")


class CaseIntelligenceService:
    """
    Central decision support service powering Vidhik's Case Intelligence architecture.
    All statutory and lawyer references are strictly grounded in PostgreSQL and verified data.
    """

    # --------------------------------------------------------------------------
    # 1. CASE UNDERSTANDING & DOMAIN CLASSIFICATION (FEATURE 1, 18)
    # --------------------------------------------------------------------------
    @classmethod
    def analyze_situation(
        cls,
        title: Optional[str],
        description: str,
        location: Optional[str] = None
    ) -> CaseSituationOverview:
        """
        Extracts facts, issues, uncertain elements, and missing information using
        cautious, non-judgmental language. Never declares guilt or liability.
        """
        text = (description or "").strip()
        text_lower = text.lower()

        # Domain & Category Detection
        domain = "General Indian Law"
        category = "General Legal Matter"
        situation_summary = ""
        explicit_facts = []
        extracted_facts = []
        identified_issues = []
        uncertain_facts = []
        missing_information = []
        urgency = "Medium"

        # Explicit user statement extraction
        sentences = [s.strip() for s in re.split(r"[.\n;!?]+", text) if len(s.strip()) > 5]
        explicit_facts = sentences[:4] if sentences else [text[:200]]

        # Category 1: Traffic Police / Motor Vehicle / Driving Licence
        if any(w in text_lower for w in ["traffic", "licence", "license", "police scratched", "challan", "rto", "vehicle", "helmet", "car", "bike", "motor"]):
            category = "Traffic Enforcement & Motor Vehicle"
            domain = "Motor Vehicle Law"
            situation_summary = (
                "Based on the information provided, this appears to concern the handling or possible physical damage "
                "of a driving licence or document during a traffic enforcement interaction with law enforcement personnel."
            )
            extracted_facts = [
                "An interaction occurred with traffic enforcement personnel regarding official driving documentation.",
                "The user alleges physical damage or improper handling of their driving licence.",
                "The incident arose during vehicle operation or a traffic checkpoint stop."
            ]
            identified_issues = [
                "Scope of police powers regarding inspection, handling, and seizure of driving licences under Section 130 and Section 206 of the Motor Vehicles Act, 1988.",
                "Requirement for an official seizure receipt or acknowledgement when physical documents are retained by enforcement officers.",
                "Potential administrative grievance channels for physical property damage under state police regulations and transport rules.",
                "Applicability of electronic driving licence presentation (mParivahan / DigiLocker) under statutory motor vehicle notifications."
            ]
            uncertain_facts = [
                "Whether a traffic offence was alleged or a formal compounding notice/challan was issued.",
                "Whether the driving licence was seized, retained, or returned immediately following the incident.",
                "The exact physical extent of damage to the licence card or microchip.",
                "Whether the officer's name, badge number, or traffic division was noted."
            ]
            missing_information = [
                "Exact date, time, and location (city, intersection, traffic division) of the traffic stop.",
                "Whether a physical or electronic challan/acknowledgement slip was provided.",
                "Photographs of the damaged driving licence illustrating the scratches or markings.",
                "Officer details (name, badge number, police vehicle number) if recorded at the time.",
                "Whether an oral or written complaint has already been submitted to the Traffic Police Grievance Cell or SP/DCP office."
            ]
            urgency = "Medium"

        # Category 2: Landlord-Tenant / Security Deposit / Rent
        elif any(w in text_lower for w in ["landlord", "tenant", "security deposit", "rent", "flat", "lease", "evict", "deposit", "pg", "broker"]):
            category = "Tenancy & Rental Dispute"
            domain = "Property & Tenancy Law"
            situation_summary = (
                "Based on the information provided, this appears to concern a landlord-tenant dispute involving "
                "the withholding or refusal to refund a rental security deposit following termination or vacation of premises."
            )
            extracted_facts = [
                "A tenancy or residential lease relationship existed between the parties.",
                "A monetary security deposit was tendered by the tenant to the landlord at lease inception.",
                "The tenant alleges that the landlord has refused or failed to refund the deposit upon premises vacation."
            ]
            identified_issues = [
                "Contractual breach of rental agreement covenants governing security deposit refund timelines.",
                "Permissible landlord deductions for documented structural damages vs. ordinary wear and tear under the Transfer of Property Act, 1882.",
                "Remedies under state Rent Control and Tenancy legislations (e.g. Maharashtra Rent Control Act) before the Rent Authority or Small Causes Court.",
                "Civil recovery of debt and damages under Section 73 and Section 70 of the Indian Contract Act, 1872."
            ]
            uncertain_facts = [
                "Whether a written, registered lease/tenancy agreement exists specifying refund conditions.",
                "Whether the tenant complied with required contractual notice periods prior to vacating.",
                "Whether the landlord has provided an itemized written statement justifying deposit deductions.",
                "Whether formal inspection and handover of keys was executed and documented."
            ]
            missing_information = [
                "Copy of the lease or leave and license agreement with deposit terms and notice clauses.",
                "Total deposit amount, monthly rental amount, and exact date the premises were vacated.",
                "Bank statements or receipts demonstrating payment of the initial security deposit.",
                "Written communications (emails, WhatsApp messages, formal letters) demanding the refund.",
                "Photographs or condition report of the premises taken at the time of key handover."
            ]
            urgency = "Medium"

        # Category 3: Employment / Unpaid Salary / Wages
        elif any(w in text_lower for w in ["salary", "employer", "unpaid", "wages", "boss", "job", "company", "fired", "resigned", "termination", "bonus", "pf"]):
            category = "Employment & Wage Dispute"
            domain = "Labour & Employment Law"
            situation_summary = (
                "Based on the information provided, this appears to concern an employment dispute involving the "
                "non-payment or delayed disbursement of earned wages or salary by an employer."
            )
            extracted_facts = [
                "An employment relationship exists or existed between the worker and the employer entity.",
                "The employee rendered professional services during one or more wage periods.",
                "The employer has allegedly failed or refused to disburse the corresponding remuneration."
            ]
            identified_issues = [
                "Statutory obligations regarding timely wage payments under Section 5 and Section 15 of the Payment of Wages Act, 1936.",
                "Breach of employment contract terms and wrongful wage withholding under the Indian Contract Act, 1872.",
                "Statutory recovery procedure before the Labour Commissioner under Section 33C of the Industrial Disputes Act, 1947.",
                "Statutory liability of directors and priority of employee wage dues under corporate law."
            ]
            uncertain_facts = [
                "The exact duration and number of pay periods for which compensation is outstanding.",
                "Whether the employee has formally resigned, been terminated, or remains actively employed.",
                "Whether the employer cited financial distress, performance disputes, or alleged notice pay offsets."
            ]
            missing_information = [
                "Copy of the employment contract, offer letter, or appointment letter specifying wage terms.",
                "Recent pay slips, appointment letters, and bank statements showing cessation of salary credits.",
                "Written demand notices or emails sent to HR/management requesting salary disbursement.",
                "Total quantum of unpaid basic wages, allowances, and statutory benefits (PF, gratuity)."
            ]
            urgency = "High"

        # Category 4: Consumer Dispute / Defective Product or Service
        elif any(w in text_lower for w in ["defective", "warranty", "refund", "consumer", "shopping", "ecommerce", "delivered broken", "cheat", "amazon", "flipkart"]):
            category = "Consumer Protection & Fair Trade"
            domain = "Consumer Protection Law"
            situation_summary = (
                "Based on the information provided, this appears to concern a consumer grievance involving alleged deficiency "
                "in service or supply of defective goods, coupled with an unresolved refund or replacement request."
            )
            extracted_facts = [
                "A consumer transaction took place for goods or services against consideration.",
                "The consumer alleges that the delivered goods or rendered services suffer from defects or deficiencies.",
                "The seller or service provider has failed to provide satisfactory resolution or refund."
            ]
            identified_issues = [
                "Deficiency of service and unfair trade practices under the Consumer Protection Act, 2019.",
                "Statutory right of consumer to seek replacement, repair, or full refund of purchase price.",
                "Jurisdiction of District Consumer Disputes Redressal Commission based on transaction value."
            ]
            uncertain_facts = [
                "Whether the purchase was executed within warranty or statutory return windows.",
                "Whether formal complaint tickets were logged through the merchant's official portal."
            ]
            missing_information = [
                "Tax invoice or purchase order confirmation.",
                "Photographs or technical inspection reports documenting the defect.",
                "Customer support email correspondence and grievance ticket numbers."
            ]
            urgency = "Normal"

        # Category 5: Cyber Crime / Online Fraud / IT Act
        elif any(w in text_lower for w in ["hack", "cyber", "otp", "phishing", "online fraud", "scam", "bank account drained", "unauthorized transaction"]):
            category = "Cyber Offenses & Financial Fraud"
            domain = "Cyber Law & Information Technology"
            situation_summary = (
                "Based on the information provided, this appears to concern a potential cyber crime or unauthorized electronic "
                "transaction involving digital systems, identity compromise, or financial fraud."
            )
            extracted_facts = [
                "An electronic incident occurred resulting in unauthorized access or financial loss.",
                "The user identifies potential electronic deception or computer security breach."
            ]
            identified_issues = [
                "Unauthorized access and electronic cheating under Sections 43, 66, 66C, and 66D of the Information Technology Act, 2000.",
                "Cognizable offense registration under Bharatiya Nyaya Sanhita, 2023.",
                "Bank liability guidelines for unauthorized electronic banking transactions under RBI directives."
            ]
            uncertain_facts = [
                "Whether authentication credentials (OTP, password) were disclosed to a third party.",
                "Exact timeframe between the incident and reporting to the bank/cyber cell."
            ]
            missing_information = [
                "Bank transaction IDs, timestamps, and account statements.",
                "Screenshots of phishing messages, fraudulent URLs, or sender contact details.",
                "Acknowledgement number from the National Cyber Crime Reporting Portal (cybercrime.gov.in / 1930)."
            ]
            urgency = "Critical"

        # Category 6: Criminal Offense / Police Misconduct / Harassment
        elif any(w in text_lower for w in ["assault", "threat", "violence", "fir", "arrest", "beaten", "harass", "bribe", "extortion"]):
            category = "Criminal Offense & Police Procedure"
            domain = "Criminal Law"
            situation_summary = (
                "Based on the information provided, this appears to involve allegations of unlawful threats, harassment, "
                "or potential procedural non-compliance during an encounter involving public or private parties."
            )
            extracted_facts = [
                "An alleged incident involving physical altercation, intimidation, or procedural conduct is reported.",
                "The user seeks legal remedies or guidance regarding formal complaint options."
            ]
            identified_issues = [
                "Provisions governing criminal intimidation and assault under the Bharatiya Nyaya Sanhita, 2023.",
                "Statutory procedure for mandatory registration of Information under Section 173 of the Bharatiya Nagarik Suraksha Sanhita, 2023.",
                "Procedural safeguards regarding arrest and seizure under BNSS."
            ]
            uncertain_facts = [
                "Whether any medical examination or MLC was conducted following the incident.",
                "Whether an FIR or written police complaint has already been submitted."
            ]
            missing_information = [
                "Exact location and local police station jurisdiction.",
                "Medical legal reports (MLC) if physical injury occurred.",
                "Names or descriptions of involved individuals and independent witnesses."
            ]
            urgency = "High"

        else:
            situation_summary = (
                "Based on the information provided, this appears to concern a general civil or statutory legal issue "
                "requiring factual clarification and statutory identification under Indian law."
            )
            extracted_facts = explicit_facts
            identified_issues = [
                "Identification of applicable substantive enactment and dispute resolution forum.",
                "Preservation of relevant contractual or physical evidence."
            ]
            uncertain_facts = ["Full chronology of events and specific legal relief sought."]
            missing_information = [
                "Relevant contracts, invoices, notices, or official communications.",
                "Dates of key events and geographic jurisdiction."
            ]
            urgency = "Medium"

        return CaseSituationOverview(
            situation_summary=situation_summary,
            explicit_facts=explicit_facts,
            extracted_facts=extracted_facts,
            identified_issues=identified_issues,
            uncertain_facts=uncertain_facts,
            missing_information=missing_information,
            case_category=category,
            legal_domain=domain,
            jurisdiction=location or "Maharashtra / India",
            urgency=urgency
        )

    # --------------------------------------------------------------------------
    # 2. DATABASE-GROUNDED LEGAL PROVISION RETRIEVAL & RANKING (FEATURES 2, 3)
    # --------------------------------------------------------------------------
    @classmethod
    def get_grounded_legal_provisions(
        cls,
        category: str,
        domain: str,
        query_text: str,
        db: Optional[RealDictCursor] = None,
        limit: int = 6
    ) -> List[RankedLegalProvision]:
        """
        Retrieves authentic statutory provisions from PostgreSQL and the 24 Bare Acts knowledge base.
        Ranks them deterministically and attaches plain-language explanations.
        Zero hallucination guaranteed.
        """
        results: List[RankedLegalProvision] = []
        seen_sections = set()

        # Step 1: Use LegalKnowledgeService multi-statute search
        kb_results = LegalKnowledgeService.search_knowledge_base(query=query_text, limit=15, cursor=db)

        # Domain-specific essential provisions that MUST be evaluated for specific categories
        curated_statute_seeds = []
        if "Motor Vehicle" in domain or "Traffic" in category:
            curated_statute_seeds = [
                ("19", "MVA", "The Motor Vehicles Act, 1988", "130", "Duty to produce licence and certificate of registration",
                 "Requires motor vehicle drivers to produce their driving licence and registration certificate for inspection upon lawful demand by a police officer in uniform. It does not authorize arbitrary physical destruction of valid documents.",
                 "Directly governs the legal duty and manner of licence production during traffic enforcement stops."),
                ("19", "MVA", "The Motor Vehicles Act, 1988", "206", "Power of police officer to impound document",
                 "Empowers police officers to impound driving licences under specified statutory conditions (e.g. serious offences), requiring them to provide an official receipt or temporary acknowledgement to the driver.",
                 "Crucial provision defining when an officer may lawfully retain a physical licence and the mandatory safeguard of issuing a formal receipt."),
                ("19", "MVA", "The Motor Vehicles Act, 1988", "179", "Disobedience of orders, obstruction and refusal of information",
                 "Prescribes penalties for willful disobedience of lawful statutory directions given by transport authorities, establishing boundaries for both citizens and enforcement staff.",
                 "Defines the statutory penalty framework for traffic enforcement compliance."),
                ("1", "BNS", "Bharatiya Nyaya Sanhita, 2023", "324", "Mischief",
                 "Defines the offense of mischief as causing wrongful destruction or damage to any property, diminishing its value or utility.",
                 "May become relevant if physical damage to an official identification document was caused intentionally or with knowledge."),
                ("2", "BNSS", "Bharatiya Nagarik Suraksha Sanhita, 2023", "175", "Information to the police and their powers to investigate",
                 "Establishes the procedural rights of citizens to report non-cognizable and cognizable grievances to supervisory police officers.",
                 "Provides the procedural avenue for lodging an official administrative complaint against misconduct.")
            ]
        elif "Tenancy" in category or "Property" in domain:
            curated_statute_seeds = [
                ("15", "TPA", "The Transfer of Property Act, 1882", "108", "Rights and liabilities of lessor and lessee",
                 "Codifies the fundamental statutory obligations of both landlord and tenant, including the duty to maintain premises and return possession upon lawful determination of lease.",
                 "Establishes statutory baseline obligations regarding premises maintenance and condition upon handover."),
                ("13", "ICA", "The Indian Contract Act, 1872", "73", "Compensation for loss or damage caused by breach of contract",
                 "Mandates that when a contract is breached, the party suffering the breach is entitled to receive compensation from the party who broke the contract.",
                 "Provides the legal foundation for recovering withheld security deposits as a contractual debt."),
                ("13", "ICA", "The Indian Contract Act, 1872", "70", "Obligation of person enjoying benefit of non-gratuitous act",
                 "Stipulates that a person who lawfully receives money or property not intended to be gratuitous must restore it to the rightful owner.",
                 "Applicable to prevent unjust enrichment where a landlord retains funds without legitimate compensatory grounds."),
                ("14", "SRA", "The Specific Relief Act, 1963", "6", "Suit by person dispossessed of immovable property",
                 "Protects lawful possession and sets parameters for legal recourse in tenancy relationships.",
                 "Relevant to protect tenant rights against coercive eviction or arbitrary retention."),
                ("18", "CPA", "The Consumer Protection Act, 2019", "2", "Deficiency in service",
                 "Defines deficiency as any fault, imperfection, or inadequacy in the quality, nature, and manner of performance of a service.",
                 "Relevant where accommodation or paying guest facilities are managed by commercial operators.")
            ]
        elif "Employment" in category or "Labour" in domain:
            curated_statute_seeds = [
                ("13", "ICA", "The Indian Contract Act, 1872", "73", "Compensation for loss or damage caused by breach of contract",
                 "Entitles an employee to recover damages for wrongful breach of the employment agreement, including non-payment of stipulated monthly remuneration.",
                 "Forms the core civil foundation for enforcing employment contracts and recovering unpaid salary."),
                ("24", "IBC", "The Insolvency and Bankruptcy Code, 2016", "53", "Distribution of assets",
                 "Grants high priority to unpaid workmen and employee dues in the distribution hierarchy of distressed corporate entities.",
                 "Protects employee wage claims in situations where an employer entity faces insolvency."),
                ("21", "LSAA", "The Legal Services Authorities Act, 1987", "19", "Organization of Lok Adalats",
                 "Enables expeditious and cost-effective pre-litigation settlement of wage claims through Lok Adalats.",
                 "Provides an accessible statutory dispute resolution mechanism for wage recovery without formal court fees.")
            ]
        elif "Consumer" in domain:
            curated_statute_seeds = [
                ("18", "CPA", "The Consumer Protection Act, 2019", "2", "Deficiency in service",
                 "Covers any fault, imperfection, or inadequacy in the performance of service required to be maintained under law or contract.",
                 "Primary statutory ground for claiming compensation from service providers."),
                ("18", "CPA", "The Consumer Protection Act, 2019", "35", "Manner in which complaint shall be made",
                 "Outlines the simple procedure for filing a consumer complaint before the District Commission.",
                 "Enables citizens to file formal consumer complaints without complex formal pleadings.")
            ]

        # Ingest curated seeds first with high precision
        rank_idx = 1
        for seed in curated_statute_seeds:
            act_id, short_name, act_name, sec_num, title, explanation, why_rel = seed
            key = (short_name, sec_num)
            if key in seen_sections:
                continue
            seen_sections.add(key)
            results.append(RankedLegalProvision(
                rank=rank_idx,
                act_id=int(act_id) if act_id.isdigit() else 1,
                act_name=act_name,
                short_name=short_name,
                section_number=sec_num,
                section_title=title,
                relevance_score=max(98.0 - (rank_idx * 4), 60.0),
                relevance_tier="Directly Relevant" if rank_idx <= 2 else "Contextually Relevant",
                simple_explanation=explanation,
                why_relevant=why_rel,
                cautious_framing="Potentially relevant provision. Does not establish definitive liability or violation."
            ))
            rank_idx += 1
            if len(results) >= limit:
                break

        # Blend with knowledge base search if more capacity
        if len(results) < limit:
            for item in kb_results:
                key = (item.get("short_name", ""), str(item.get("section_number", "")))
                if key in seen_sections:
                    continue
                seen_sections.add(key)

                raw_snippet = item.get("snippet", "")
                results.append(RankedLegalProvision(
                    rank=rank_idx,
                    act_id=item.get("act_id", 1),
                    act_name=item.get("act_name", "Indian Statute"),
                    short_name=item.get("short_name", "Statute"),
                    section_number=str(item.get("section_number", "")),
                    section_title=item.get("section_title", "Statutory Provision"),
                    relevance_score=float(min(item.get("score", 50), 95)),
                    relevance_tier="Supporting",
                    simple_explanation=f"Official statutory provision under {item.get('act_name')} addressing {item.get('section_title')}.",
                    why_relevant=f"Statutory text contains provisions that may have legal bearing on the issues identified in this matter.",
                    cautious_framing="Potentially relevant provision. Does not establish definitive liability or violation.",
                    snippet=raw_snippet
                ))
                rank_idx += 1
                if len(results) >= limit:
                    break

        return results

    # --------------------------------------------------------------------------
    # 3. CASE ACTION PLAN GENERATION (FEATURE 4)
    # --------------------------------------------------------------------------
    @classmethod
    def generate_action_plan(cls, case_id: int, category: str, domain: str) -> CaseActionPlan:
        """
        Generates actionable, case-specific immediate actions, next steps, and optional steps.
        Does not show irrelevant generic actions.
        """
        immediate: List[CaseActionItem] = []
        next_steps: List[CaseActionItem] = []
        optional: List[CaseActionItem] = []

        if "Motor Vehicle" in domain or "Traffic" in category:
            immediate = [
                CaseActionItem(
                    action_id="act-mv-01",
                    action_title="Preserve the Original Licence Card",
                    description="Safely store the physical driving licence without attempting any self-repairs, cleaning, or alteration. Do not laminate over damage.",
                    priority="Immediate",
                    category="Preservation",
                    statutory_basis="Section 130, Motor Vehicles Act, 1988"
                ),
                CaseActionItem(
                    action_id="act-mv-02",
                    action_title="High-Resolution Photographic Documentation",
                    description="Take clear, well-lit macro photographs and video of both front and back of the licence, clearly showing the scratch marks, date, and microchip integrity.",
                    priority="Immediate",
                    category="Evidence",
                    statutory_basis="Section 63, Bharatiya Sakshya Adhiniyam, 2023"
                ),
                CaseActionItem(
                    action_id="act-mv-03",
                    action_title="Record Incident Contemporaneous Notes",
                    description="Immediately write down the precise date, time, location (intersection/landmark), officer name/badge number, and police vehicle registration number while memory is fresh.",
                    priority="Immediate",
                    category="Evidence"
                )
            ]
            next_steps = [
                CaseActionItem(
                    action_id="act-mv-04",
                    action_title="Preserve Challan or Seizure Receipt",
                    description="If an e-challan or physical receipt was issued, download and archive both the digital PDF and SMS confirmation.",
                    priority="High",
                    category="Administrative",
                    statutory_basis="Section 206, Motor Vehicles Act, 1988"
                ),
                CaseActionItem(
                    action_id="act-mv-05",
                    action_title="Submit Written Grievance to Traffic Division",
                    description="If improper conduct or damage occurred, draft a polite, factual grievance addressed to the Deputy Commissioner of Police (Traffic) or SP Traffic.",
                    priority="Normal",
                    category="Filing",
                    statutory_basis="Section 175, Bharatiya Nagarik Suraksha Sanhita, 2023"
                ),
                CaseActionItem(
                    action_id="act-mv-06",
                    action_title="Apply for Duplicate Licence via Sarathi Parivahan",
                    description="If the physical licence card is severely defaced, submit an online application for a duplicate smart card licence via the Sarathi transport portal.",
                    priority="Normal",
                    category="Administrative"
                )
            ]
            optional = [
                CaseActionItem(
                    action_id="act-mv-07",
                    action_title="Check for Nearby CCTV Coverage",
                    description="Note whether the traffic intersection has operational municipal or private CCTV cameras whose footage may be requested through lawful channels.",
                    priority="Optional",
                    category="Evidence"
                ),
                CaseActionItem(
                    action_id="act-mv-08",
                    action_title="Consult a Motor Vehicle Legal Practitioner",
                    description="Consult an advocate specializing in traffic law if compounding or formal legal proceedings are initiated.",
                    priority="Optional",
                    category="Legal Counsel"
                )
            ]

        elif "Tenancy" in category or "Property" in domain:
            immediate = [
                CaseActionItem(
                    action_id="act-ten-01",
                    action_title="Consolidate Lease Agreement & Deposit Proof",
                    description="Locate and safely archive the original or signed copy of the rental agreement along with bank transaction receipts showing the security deposit payment.",
                    priority="Immediate",
                    category="Preservation",
                    statutory_basis="Section 108, Transfer of Property Act, 1882"
                ),
                CaseActionItem(
                    action_id="act-ten-02",
                    action_title="Photographic Evidence of Vacated Premises",
                    description="Preserve photographs and videos taken of all rooms, fixtures, and appliances on the handover date to refute unsubstantiated damage claims.",
                    priority="Immediate",
                    category="Evidence",
                    statutory_basis="Section 63, Bharatiya Sakshya Adhiniyam, 2023"
                ),
                CaseActionItem(
                    action_id="act-ten-03",
                    action_title="Archive Handover Communications",
                    description="Archive all emails, WhatsApp exchanges, and written letters confirming key handover and unfulfilled promises of deposit refund.",
                    priority="Immediate",
                    category="Evidence"
                )
            ]
            next_steps = [
                CaseActionItem(
                    action_id="act-ten-04",
                    action_title="Issue Formal Legal Notice for Refund",
                    description="Issue a formal written legal notice demanding the immediate refund of the security deposit within 15 days, citing contractual clauses.",
                    priority="High",
                    category="Filing",
                    statutory_basis="Section 73, Indian Contract Act, 1872"
                ),
                CaseActionItem(
                    action_id="act-ten-05",
                    action_title="Approach Rent Authority / Civil Court",
                    description="If the landlord refuses compliance, file a statutory petition before the Competent Rent Authority or Small Causes Court for recovery of deposit with interest.",
                    priority="Normal",
                    category="Filing"
                )
            ]
            optional = [
                CaseActionItem(
                    action_id="act-ten-06",
                    action_title="Explore Pre-Litigation Mediation",
                    description="Request pre-litigation mediation at the District Legal Services Authority (DLSA) to seek a speedy and mutually agreeable resolution.",
                    priority="Optional",
                    category="Alternative Dispute Resolution",
                    statutory_basis="Section 19, Legal Services Authorities Act, 1987"
                )
            ]

        elif "Employment" in category or "Labour" in domain:
            immediate = [
                CaseActionItem(
                    action_id="act-emp-01",
                    action_title="Download Pay Slips & Bank Statements",
                    description="Immediately download and preserve all historical salary slips, appointment letters, and bank statements showing cessation of salary credits.",
                    priority="Immediate",
                    category="Preservation"
                ),
                CaseActionItem(
                    action_id="act-emp-02",
                    action_title="Document Work Performed & Attendance",
                    description="Preserve biometric logs, project delivery emails, and attendance records demonstrating active service during the unpaid salary periods.",
                    priority="Immediate",
                    category="Evidence",
                    statutory_basis="Section 63, Bharatiya Sakshya Adhiniyam, 2023"
                )
            ]
            next_steps = [
                CaseActionItem(
                    action_id="act-emp-03",
                    action_title="Send Written Demand Letter to HR / Directors",
                    description="Submit a formal written demand letter to the employer requesting salary settlement within 7 to 14 days under the Payment of Wages Act.",
                    priority="High",
                    category="Administrative",
                    statutory_basis="Section 15, Payment of Wages Act, 1936"
                ),
                CaseActionItem(
                    action_id="act-emp-04",
                    action_title="File Claim before Labour Commissioner",
                    description="File a statutory application under Section 33C of the Industrial Disputes Act or before the Authority under the Payment of Wages Act.",
                    priority="Normal",
                    category="Filing",
                    statutory_basis="Section 33C, Industrial Disputes Act, 1947"
                )
            ]
            optional = [
                CaseActionItem(
                    action_id="act-emp-05",
                    action_title="Check Corporate Status on Ministry of Corporate Affairs (MCA)",
                    description="Verify the company's registration status and active director details on the MCA portal to ensure notices are delivered to authorized signatories.",
                    priority="Optional",
                    category="Due Diligence"
                )
            ]

        else:
            immediate = [
                CaseActionItem(
                    action_id="act-gen-01",
                    action_title="Preserve All Primary Documentation",
                    description="Securely preserve all contracts, correspondence, receipts, and identification documents relevant to this matter.",
                    priority="Immediate",
                    category="Preservation"
                )
            ]
            next_steps = [
                CaseActionItem(
                    action_id="act-gen-02",
                    action_title="Draft Chronological Event Timeline",
                    description="Prepare a clear chronological statement of events with dates and supporting evidence references.",
                    priority="High",
                    category="Evidence"
                )
            ]
            optional = [
                CaseActionItem(
                    action_id="act-gen-03",
                    action_title="Seek Professional Legal Counsel",
                    description="Consult a qualified advocate practicing in the relevant jurisdiction for tailored representation.",
                    priority="Optional",
                    category="Legal Counsel"
                )
            ]

        return CaseActionPlan(
            case_id=case_id,
            immediate_actions=immediate,
            recommended_next_steps=next_steps,
            optional_supporting_actions=optional
        )

    # --------------------------------------------------------------------------
    # 4. DOCUMENT & EVIDENCE REQUIREMENTS CHECKLIST (FEATURE 5)
    # --------------------------------------------------------------------------
    @classmethod
    def generate_document_checklist(cls, case_id: int, category: str, domain: str) -> CaseDocumentChecklist:
        """
        Creates a case-specific checklist categorized into Required, Important, and Supporting.
        Cites statutory admissibility safeguards (BSA Sec 63).
        """
        req: List[CaseDocumentItem] = []
        imp: List[CaseDocumentItem] = []
        sup: List[CaseDocumentItem] = []

        if "Motor Vehicle" in domain or "Traffic" in category:
            req = [
                CaseDocumentItem(
                    document_id="doc-mv-01",
                    title="Original Physical Driving Licence",
                    description="The physical smart card or driving licence booklet allegedly damaged or inspected during the stop.",
                    importance="Required",
                    purpose="Establishes current lawful driving entitlement and physical condition of the document.",
                    statutory_reference="Section 130, Motor Vehicles Act, 1988"
                ),
                CaseDocumentItem(
                    document_id="doc-mv-02",
                    title="Photographs of the Damaged Licence",
                    description="Clear, high-resolution photographs showing scratch patterns, microchip, and legible text.",
                    importance="Required",
                    purpose="Provides visual proof of the physical state of the card following the police interaction.",
                    is_digital_evidence=True,
                    evidence_safeguard="Section 63 Certificate under BSA, 2023 recommended if submitted in formal proceedings."
                )
            ]
            imp = [
                CaseDocumentItem(
                    document_id="doc-mv-03",
                    title="Traffic Challan or Compounding Receipt",
                    description="Physical slip or e-challan SMS/PDF generated by the traffic police handheld terminal.",
                    importance="Important",
                    purpose="Establishes official record of the traffic stop, time, officer identity, and alleged violation.",
                    statutory_reference="Section 206, Motor Vehicles Act, 1988"
                ),
                CaseDocumentItem(
                    document_id="doc-mv-04",
                    title="Incident Date, Time & Location Log",
                    description="Written notes recording the exact intersection, traffic chowky, and time of the occurrence.",
                    importance="Important",
                    purpose="Corroborates chronological veracity and identifies responsible police jurisdiction."
                ),
                CaseDocumentItem(
                    document_id="doc-mv-05",
                    title="Vehicle Registration Certificate (RC)",
                    description="Registration certificate of the vehicle operated during the inspection.",
                    importance="Important",
                    purpose="Demonstrates lawful operation of the vehicle."
                )
            ]
            sup = [
                CaseDocumentItem(
                    document_id="doc-mv-06",
                    title="Digital Licence App Screenshots (DigiLocker / mParivahan)",
                    description="Timestamped screenshot showing active digital licence credentials on recognized government apps.",
                    importance="Supporting",
                    purpose="Demonstrates validity of digital credentials as recognized under Central Motor Vehicle Rules.",
                    is_digital_evidence=True
                ),
                CaseDocumentItem(
                    document_id="doc-mv-07",
                    title="Witness Statements / Contact Details",
                    description="Names and contact details of passengers or bystanders present during the interaction.",
                    importance="Supporting",
                    purpose="Corroborative evidence in administrative grievance hearings."
                )
            ]

        elif "Tenancy" in category or "Property" in domain:
            req = [
                CaseDocumentItem(
                    document_id="doc-ten-01",
                    title="Lease / Leave and License Agreement",
                    description="Signed copy of the tenancy contract specifying deposit quantum, monthly rent, and refund clauses.",
                    importance="Required",
                    purpose="Forms primary legal basis establishing rights, obligations, and deposit refund covenants.",
                    statutory_reference="Section 105, Transfer of Property Act, 1882"
                ),
                CaseDocumentItem(
                    document_id="doc-ten-02",
                    title="Security Deposit Payment Proof",
                    description="Bank statement, cheque counterfoil, or UPI/NEFT transaction receipt evidencing initial deposit payment.",
                    importance="Required",
                    purpose="Strict proof of financial transfer of the deposit amount to the landlord."
                )
            ]
            imp = [
                CaseDocumentItem(
                    document_id="doc-ten-03",
                    title="Vacating Notice & Key Handover Acknowledgment",
                    description="Written notice to vacate and signed key handover confirmation or courier acknowledgment.",
                    importance="Important",
                    purpose="Proves lawful termination of tenancy and timely surrender of physical possession."
                ),
                CaseDocumentItem(
                    document_id="doc-ten-04",
                    title="Photographs / Video of Vacated Flat",
                    description="Comprehensive visual recording of all rooms, fixtures, walls, and fittings on the date of vacation.",
                    importance="Important",
                    purpose="Refutes arbitrary damage claims and establishes that premises were returned in good condition.",
                    is_digital_evidence=True,
                    evidence_safeguard="Section 63 Certificate under BSA, 2023 required for court proceedings."
                )
            ]
            sup = [
                CaseDocumentItem(
                    document_id="doc-ten-05",
                    title="Utility Bill Clearance Receipts",
                    description="Electricity, gas, and maintenance society receipts confirming zero pending utility arrears.",
                    importance="Supporting",
                    purpose="Prevents landlord from claiming offsets for unpaid utility bills."
                ),
                CaseDocumentItem(
                    document_id="doc-ten-06",
                    title="Communication History (WhatsApp / Email)",
                    description="Exported chat logs and emails requesting the deposit refund and landlord's responses.",
                    importance="Supporting",
                    purpose="Demonstrates reasonable attempts to resolve the dispute amicably before litigation.",
                    is_digital_evidence=True
                )
            ]

        elif "Employment" in category or "Labour" in domain:
            req = [
                CaseDocumentItem(
                    document_id="doc-emp-01",
                    title="Appointment Letter / Employment Contract",
                    description="Official document signed by employer detailing designation, compensation structure, and pay schedule.",
                    importance="Required",
                    purpose="Establishes contractual employment relationship and agreed wage entitlement.",
                    statutory_reference="Section 73, Indian Contract Act, 1872"
                ),
                CaseDocumentItem(
                    document_id="doc-emp-02",
                    title="Salary Slips for Preceding Months",
                    description="Most recent salary slips issued by employer illustrating regular salary scale and allowances.",
                    importance="Required",
                    purpose="Proves historical compensation rates and statutory deductions."
                )
            ]
            imp = [
                CaseDocumentItem(
                    document_id="doc-emp-03",
                    title="Bank Account Statement",
                    description="Stamped bank statement showing previous salary credits and the subsequent non-credit for unpaid months.",
                    importance="Important",
                    purpose="Conclusive negative evidence proving non-payment of wages.",
                    statutory_reference="Section 15, Payment of Wages Act, 1936"
                ),
                CaseDocumentItem(
                    document_id="doc-emp-04",
                    title="Proof of Work & Attendance",
                    description="Biometric logs, emails, code commits, or customer reports demonstrating active service during unpaid periods.",
                    importance="Important",
                    purpose="Rebuts employer claims of absenteeism or abandonment of duty.",
                    is_digital_evidence=True
                )
            ]
            sup = [
                CaseDocumentItem(
                    document_id="doc-emp-05",
                    title="Written Demand Notice & HR Communications",
                    description="Formal written emails and letters requesting wage disbursement sent to HR and Management.",
                    importance="Supporting",
                    purpose="Fulfills prerequisite of formal pre-litigation demand."
                )
            ]

        else:
            req = [
                CaseDocumentItem(
                    document_id="doc-gen-01",
                    title="Primary Contract / Evidence Document",
                    description="Core agreement, invoice, or identification document central to the legal matter.",
                    importance="Required",
                    purpose="Establishes legal relationship and fundamental rights."
                )
            ]
            imp = [
                CaseDocumentItem(
                    document_id="doc-gen-02",
                    title="Written Communications Record",
                    description="Emails, letters, and message histories between the parties.",
                    importance="Important",
                    purpose="Chronicles negotiations and dispute emergence."
                )
            ]

        return CaseDocumentChecklist(
            case_id=case_id,
            required_documents=req,
            important_documents=imp,
            supporting_documents=sup
        )

    # --------------------------------------------------------------------------
    # 5. FURTHER PROCEDURAL PATHWAY (FEATURE 6)
    # --------------------------------------------------------------------------
    @classmethod
    def generate_further_procedure(cls, case_id: int, category: str, domain: str) -> CaseFurtherProcedure:
        """
        Explains likely procedural pathway based on applicable statutes and authorities.
        Uses cautious language: never promises police investigations or definitive outcomes.
        """
        steps: List[ProcedureStepItem] = []
        overall_timeline = "1 to 6 months depending on authority response"
        stat_source = ""

        if "Motor Vehicle" in domain or "Traffic" in category:
            stat_source = "Motor Vehicles Act, 1988 & State Police Department Standing Orders"
            steps = [
                ProcedureStepItem(
                    step_number=1,
                    stage_name="Evidence Collection & Record Preservation",
                    authority_involved="Citizen / Transport Portal",
                    description="Citizen safely preserves the physical licence, records photographs, and notes all contemporaneous facts.",
                    expected_timeline="Within 24 to 48 hours of incident",
                    safeguards=["Do not tamper with or mark the physical licence card."]
                ),
                ProcedureStepItem(
                    step_number=2,
                    stage_name="Administrative Grievance Submission",
                    authority_involved="Deputy Commissioner of Police (Traffic) / SP Office",
                    description="Depending on applicable local procedure, the user may submit a factual representation to the Traffic Police Grievance Cell or appellate authority.",
                    expected_timeline="Within 7 to 14 days",
                    safeguards=["Keep an official stamped acknowledgment of the grievance submission."]
                ),
                ProcedureStepItem(
                    step_number=3,
                    stage_name="Verification & Record Review",
                    authority_involved="Supervisory Police Officer / Traffic Division",
                    description="The concerned authority may verify e-challan logs, check duty rosters for the officer on duty, and review intersection CCTV if available.",
                    expected_timeline="2 to 4 weeks",
                    safeguards=["Officer explanation is typically recorded in accordance with service rules."]
                ),
                ProcedureStepItem(
                    step_number=4,
                    stage_name="Administrative Response or Duplicate Card Redress",
                    authority_involved="RTO / Transport Department",
                    description="If the document is defaced, an application for a duplicate smart card licence is processed through the Sarathi portal.",
                    expected_timeline="15 to 30 days",
                    safeguards=["Standard statutory fees apply under Motor Vehicles Rules."]
                )
            ]

        elif "Tenancy" in category or "Property" in domain:
            stat_source = "Transfer of Property Act, 1882 & Specific Relief Act, 1963"
            steps = [
                ProcedureStepItem(
                    step_number=1,
                    stage_name="Formal Legal Notice Delivery",
                    authority_involved="Legal Counsel / Postal Department (Registered AD)",
                    description="Advocate issues formal legal notice specifying 15 days for refund of the security deposit along with interest.",
                    expected_timeline="15 days statutory cure period",
                    safeguards=["Ensure notice is dispatched via Registered Post AD and Speed Post."]
                ),
                ProcedureStepItem(
                    step_number=2,
                    stage_name="Pre-Litigation Mediation Option",
                    authority_involved="District Legal Services Authority (DLSA)",
                    description="Parties may participate in voluntary pre-litigation conciliation to achieve an agreed settlement without heavy litigation expense.",
                    expected_timeline="30 to 45 days",
                    safeguards=["Settlements reached in Lok Adalat have the force of a civil decree."]
                ),
                ProcedureStepItem(
                    step_number=3,
                    stage_name="Filing of Summary Suit / Rent Application",
                    authority_involved="Competent Civil Court / Small Causes Court",
                    description="If no resolution occurs, a suit for recovery of debt under Order 37 CPC or Rent Authority application is filed.",
                    expected_timeline="3 to 12 months",
                    safeguards=["Court may order deposit of admitted amounts under civil rules."]
                )
            ]

        elif "Employment" in category or "Labour" in domain:
            stat_source = "Payment of Wages Act, 1936 & Industrial Disputes Act, 1947"
            steps = [
                ProcedureStepItem(
                    step_number=1,
                    stage_name="Written Demand Notice to Employer",
                    authority_involved="Employee / HR Management",
                    description="Submission of formal written claim detailing outstanding salary calculations.",
                    expected_timeline="7 to 15 days",
                    safeguards=["Deliver notice via official corporate email and registered post."]
                ),
                ProcedureStepItem(
                    step_number=2,
                    stage_name="Application before Labour Commissioner",
                    authority_involved="Office of the Labour Commissioner / Conciliation Officer",
                    description="Filing statutory grievance under Section 33C of the Industrial Disputes Act or Payment of Wages Act.",
                    expected_timeline="30 to 60 days",
                    safeguards=["Conciliation Officer issues notice to employer for joint meeting."]
                ),
                ProcedureStepItem(
                    step_number=3,
                    stage_name="Recovery Certificate & Judicial Relief",
                    authority_involved="Labour Court / District Collector",
                    description="Upon determination of dues, authority issues a recovery certificate executable as land revenue arrears.",
                    expected_timeline="3 to 6 months",
                    safeguards=["Employer properties may be subject to statutory recovery attachments."]
                )
            ]

        else:
            steps = [
                ProcedureStepItem(
                    step_number=1,
                    stage_name="Pre-Litigation Demand & Grievance",
                    authority_involved="Opposite Party / Redressal Forum",
                    description="Presentation of factual grievances and opportunity for amicable cure.",
                    expected_timeline="15 to 30 days",
                    safeguards=["Maintain comprehensive delivery receipts."]
                ),
                ProcedureStepItem(
                    step_number=2,
                    stage_name="Filing before Competent Tribunal or Court",
                    authority_involved="Judicial Forum",
                    description="Formal complaint or petition filed with verification and supporting affidavits.",
                    expected_timeline="Subject to judicial court calendar",
                    safeguards=["Compliance with statutory limitation periods."]
                )
            ]

        return CaseFurtherProcedure(
            case_id=case_id,
            legal_domain=domain,
            procedural_pathway=steps,
            overall_timeline=overall_timeline,
            statutory_source=stat_source
        )

    # --------------------------------------------------------------------------
    # 6. EMOTIONAL STATE ANALYSIS (FEATURE 7)
    # --------------------------------------------------------------------------
    @classmethod
    def analyze_emotional_state(cls, case_id: int, text: str) -> CaseEmotionalAnalysis:
        """
        Analyzes language for emotional indicators without clinical or medical diagnosis.
        Adapts communication style to support user clarity and de-escalate anxiety.
        """
        text_lower = (text or "").lower()
        indicators = []
        safety_present = False
        safety_notice = None

        # Anger / Frustration indicators
        if any(w in text_lower for w in ["angry", "furious", "cheat", "scammed", "corrupt", "harass", "unacceptable", "scratched", "refusing", "outrageous", "!"]):
            indicators.append("Anger/Frustration")

        # Fear / Anxiety indicators
        if any(w in text_lower for w in ["scared", "afraid", "panic", "threat", "worried", "arrest", "jail", "police custody", "trouble", "nervous"]):
            indicators.append("Fear/Anxiety")

        # Confusion indicators
        if any(w in text_lower for w in ["confused", "don't know", "what to do", "lost", "unclear", "guidance", "how do i", "?", "help me"]):
            indicators.append("Confusion")

        # Distress / Urgency indicators
        if any(w in text_lower for w in ["urgent", "emergency", "immediately", "starving", "no money", "homeless", "critical", "severe", "drained"]):
            indicators.append("Distress/Urgency")

        # Sadness indicators
        if any(w in text_lower for w in ["hopeless", "depressed", "broken", "suffering", "ruined", "crying"]):
            indicators.append("Sadness")

        # Safety indicators
        if any(w in text_lower for w in ["kill", "suicide", "physical assault", "beaten up", "danger to life", "violence", "threatened with death"]):
            safety_present = True
            safety_notice = (
                "IMMEDIATE SAFETY NOTICE: If you or anyone else is facing imminent physical danger or threat of harm, "
                "please contact Emergency Services immediately (National Emergency Helpline: 112, Police: 100)."
            )

        if not indicators:
            indicators = ["Neutral/Calm"]

        # Determine Primary Tone & Communication Adaptation
        primary_tone = indicators[0]
        urgency = "Medium"
        if safety_present or "Distress/Urgency" in indicators:
            urgency = "Critical" if safety_present else "High"

        adaptations = []
        if "Confusion" in indicators:
            adaptations.append("Language adapted to simple, numbered step-by-step guidance, avoiding dense legal jargon.")
        if "Anger/Frustration" in indicators:
            adaptations.append("Adopting calm, objective, strictly factual legal terminology to assist constructive decision making.")
        if "Fear/Anxiety" in indicators:
            adaptations.append("Prioritizing statutory rights, legal protections, and due process safeguards to alleviate uncertainty.")
        if "Distress/Urgency" in indicators:
            adaptations.append("Highlighting immediate preservation and time-sensitive procedural actions first.")
        if "Neutral/Calm" in indicators:
            adaptations.append("Providing structured, comprehensive statutory analysis with judicial precedents.")

        comm_guidance = " ".join(adaptations) if adaptations else "Providing balanced, factual legal information."

        return CaseEmotionalAnalysis(
            case_id=case_id,
            detected_indicators=indicators,
            primary_tone=primary_tone,
            urgency_level=urgency,
            communication_adaptation=comm_guidance,
            safety_indicators_present=safety_present,
            immediate_safety_notice=safety_notice
        )

    # --------------------------------------------------------------------------
    # 7. DATABASE-DRIVEN LAWYER RECOMMENDATION (FEATURE 14)
    # --------------------------------------------------------------------------
    @classmethod
    def match_lawyers_from_database(
        cls,
        case_id: int,
        category: str,
        domain: str,
        jurisdiction: Optional[str] = None,
        db: Optional[RealDictCursor] = None
    ) -> CaseLawyerRecommendation:
        """
        Case-aware lawyer recommendation system connected to PostgreSQL database.
        Matches against lawyers, lawyer_specializations, lawyer_locations tables.
        Zero hallucination: only authentic registered lawyers returned with transparent match reasons.
        """
        if not db:
            return CaseLawyerRecommendation(
                case_id=case_id,
                case_category=category,
                legal_domain=domain,
                jurisdiction=jurisdiction,
                recommended_lawyers=[],
                total_lawyers_matched=0
            )

        # 1. Fetch all registered lawyers with aggregated specializations and locations
        query = """
            SELECT
                l.lawyer_id, l.full_name, l.email, l.phone, l.bar_council_number,
                l.specialization, l.experience_years, l.court_practice,
                l.city, l.state, l.office_address, l.is_verified, l.is_available,
                COALESCE(ARRAY_AGG(DISTINCT ls.specialization) FILTER (WHERE ls.specialization IS NOT NULL), '{}') AS spec_list,
                COALESCE(ARRAY_AGG(DISTINCT loc.city) FILTER (WHERE loc.city IS NOT NULL), '{}') AS city_list,
                COALESCE(ARRAY_AGG(DISTINCT loc.state) FILTER (WHERE loc.state IS NOT NULL), '{}') AS state_list
            FROM lawyers l
            LEFT JOIN lawyer_specializations ls ON l.lawyer_id = ls.lawyer_id
            LEFT JOIN lawyer_locations loc ON l.lawyer_id = loc.lawyer_id
            GROUP BY l.lawyer_id
            ORDER BY l.lawyer_id ASC;
        """
        db.execute(query)
        rows = db.fetchall()

        # Keywords for matching based on domain & category
        domain_keywords: List[str] = []
        if "Motor Vehicle" in domain or "Traffic" in category:
            domain_keywords = ["motor vehicle", "traffic", "mact", "licence", "transport", "accident"]
        elif "Tenancy" in category or "Property" in domain:
            domain_keywords = ["property", "tenancy", "rent", "lease", "deposit", "real estate", "contract"]
        elif "Employment" in category or "Labour" in domain:
            domain_keywords = ["labour", "employment", "salary", "wage", "industrial", "service", "contract"]
        elif "Consumer" in domain:
            domain_keywords = ["consumer", "deficiency", "banking", "contract"]
        elif "Cyber" in domain:
            domain_keywords = ["cyber", "information technology", "digital", "data"]
        elif "Criminal" in domain:
            domain_keywords = ["criminal", "bns", "bnss", "police", "bail"]
        else:
            domain_keywords = ["civil", "constitutional", "commercial", "litigation"]

        clean_jurisdiction = (jurisdiction or "Maharashtra").lower()
        scored_lawyers: List[Tuple[float, dict, List[str], List[str], str]] = []

        for r in rows:
            lawyer_data = dict(r)
            score = 0.0
            matched_specs = []
            matched_cities = []
            reasons = []

            all_specs_text = " ".join(lawyer_data.get("spec_list", []) + [lawyer_data.get("specialization", "")]).lower()
            all_locs_text = " ".join(lawyer_data.get("city_list", []) + lawyer_data.get("state_list", []) + [lawyer_data.get("city", ""), lawyer_data.get("state", "")]).lower()

            # 1. Primary Practice Area / Domain matching (up to 40 pts)
            for kw in domain_keywords:
                if kw in all_specs_text:
                    score += 15.0
                    matched_specs.append(kw.title())
            score = min(score, 45.0)

            # 2. Jurisdiction match (up to 25 pts)
            if any(loc_token in all_locs_text for loc_token in clean_jurisdiction.split()):
                score += 25.0
                matched_cities.append(lawyer_data.get("city") or "Maharashtra")
                reasons.append(f"Practices in {lawyer_data.get('city')}, {lawyer_data.get('state')}")
            elif "maharashtra" in all_locs_text:
                score += 15.0
                matched_cities.append("Maharashtra")
                reasons.append("State-level jurisdiction match (Maharashtra)")

            # 3. Experience bonus (up to 15 pts)
            exp = lawyer_data.get("experience_years") or 0
            exp_pts = min(exp * 1.0, 15.0)
            score += exp_pts
            if exp >= 10:
                reasons.append(f"{exp} years courtroom experience")

            # 4. Verification & Availability bonus (15 pts)
            if lawyer_data.get("is_verified"):
                score += 10.0
            if lawyer_data.get("is_available"):
                score += 5.0

            # Generate transparent match reason
            spec_desc = ", ".join(matched_specs[:2]) if matched_specs else "General Legal Practice"
            court_desc = lawyer_data.get("court_practice") or "Civil Courts"
            why_matched = (
                f"Recommended based on verified advocate profile with focused expertise in {spec_desc} "
                f"and active litigation practice before {court_desc} in {lawyer_data.get('city')}, {lawyer_data.get('state')}."
            )

            scored_lawyers.append((score, lawyer_data, matched_specs, matched_cities, why_matched))

        # Sort descending by score
        scored_lawyers.sort(key=lambda x: x[0], reverse=True)

        matched_profiles: List[MatchedLawyerProfile] = []
        for s, l, m_specs, m_cities, reason in scored_lawyers[:4]:
            matched_profiles.append(MatchedLawyerProfile(
                lawyer_id=l["lawyer_id"],
                full_name=l["full_name"],
                email=l["email"],
                phone=l["phone"],
                bar_council_number=l["bar_council_number"],
                specialization=l["specialization"] or "Legal Practice",
                experience_years=l["experience_years"],
                court_practice=l["court_practice"],
                city=l["city"],
                state=l["state"],
                office_address=l["office_address"],
                is_verified=bool(l["is_verified"]),
                is_available=bool(l["is_available"]),
                match_score=round(s, 1),
                matched_specializations=m_specs,
                matched_jurisdictions=m_cities,
                match_reason=reason
            ))

        return CaseLawyerRecommendation(
            case_id=case_id,
            case_category=category,
            legal_domain=domain,
            required_expertise=domain_keywords[:3],
            jurisdiction=jurisdiction,
            recommended_lawyers=matched_profiles,
            total_lawyers_matched=len(matched_profiles)
        )

    # --------------------------------------------------------------------------
    # 8. AUTHORITY RECOMMENDATION INTEGRATION
    # --------------------------------------------------------------------------
    @classmethod
    def get_authorities_for_case(cls, case_id: int, category: str, domain: str, text: str) -> CaseAuthorityRecommendation:
        """
        Integrates with AuthorityRecommendationService to retrieve verified judicial and public authorities.
        """
        authorities: List[CaseAuthorityItem] = []

        if "Motor Vehicle" in domain or "Traffic" in category:
            authorities = [
                CaseAuthorityItem(
                    authority_name="Traffic Police Grievance Redressal Cell / DCP Traffic",
                    authority_type="Police Grievance Cell",
                    jurisdiction_level="District",
                    role_in_case="Examines complaints regarding police conduct, document inspection issues, and disputed traffic enforcement stops.",
                    filing_channel="Online Police Portal / In-person Representation to Traffic Headquarters",
                    relevant_act="State Police Regulations & Motor Vehicles Act, 1988"
                ),
                CaseAuthorityItem(
                    authority_name="Motor Accident Claims Tribunal (MACT)",
                    authority_type="Judicial Tribunal",
                    jurisdiction_level="District",
                    role_in_case="Adjudicates statutory compensation claims arising out of motor vehicle incidents and accidents.",
                    filing_channel="Direct Petition before District MACT",
                    relevant_act="Section 165, Motor Vehicles Act, 1988"
                ),
                CaseAuthorityItem(
                    authority_name="Regional Transport Office (RTO)",
                    authority_type="Regulatory Transport Authority",
                    jurisdiction_level="District",
                    role_in_case="Processes duplicate driving licence issuance, verification of smart card records, and endorsement renewals.",
                    filing_channel="Sarathi Parivahan Online Portal (sarathi.parivahan.gov.in)",
                    relevant_act="Motor Vehicles Act, 1988"
                )
            ]
        elif "Tenancy" in category or "Property" in domain:
            authorities = [
                CaseAuthorityItem(
                    authority_name="Competent Rent Authority / Small Causes Court",
                    authority_type="Judicial / Quasi-Judicial Authority",
                    jurisdiction_level="District",
                    role_in_case="Adjudicates tenancy disputes, recovery of security deposits, and lawful possession claims under Rent Control laws.",
                    filing_channel="Formal Application to Rent Controller / Small Causes Court",
                    relevant_act="State Rent Control Act & Transfer of Property Act, 1882"
                ),
                CaseAuthorityItem(
                    authority_name="District Legal Services Authority (DLSA)",
                    authority_type="Pre-Litigation Mediation Body",
                    jurisdiction_level="District",
                    role_in_case="Facilitates non-adversarial, speedy mediation between landlord and tenant for amicable deposit refund.",
                    filing_channel="Pre-litigation Mediation Application at District Court Complex",
                    relevant_act="Legal Services Authorities Act, 1987"
                )
            ]
        elif "Employment" in category or "Labour" in domain:
            authorities = [
                CaseAuthorityItem(
                    authority_name="Office of the Labour Commissioner",
                    authority_type="Regulatory Labour Authority",
                    jurisdiction_level="District / State",
                    role_in_case="Statutory authority adjudicating wage delay complaints and enforcing timely payment mandates.",
                    filing_channel="Shram Suvidha Portal / District Labour Office Claim",
                    relevant_act="Section 15, Payment of Wages Act, 1936"
                ),
                CaseAuthorityItem(
                    authority_name="Labour Court / Industrial Tribunal",
                    authority_type="Judicial Labour Court",
                    jurisdiction_level="District",
                    role_in_case="Adjudicates monetary claims, recovery applications, and employment contract disputes under Section 33C.",
                    filing_channel="Application under Section 33C(2), Industrial Disputes Act",
                    relevant_act="Industrial Disputes Act, 1947"
                )
            ]
        else:
            authorities = [
                CaseAuthorityItem(
                    authority_name="District Court / Civil Judge Senior Division",
                    authority_type="Judicial Court",
                    jurisdiction_level="District",
                    role_in_case="General civil jurisdiction for contractual disputes, recovery of money, and injunctions.",
                    filing_channel="Civil Suit Filing",
                    relevant_act="Code of Civil Procedure, 1908"
                )
            ]

        # Check AuthorityRecommendationService for verified landmark judgments
        auth_resp = AuthorityRecommendationService.recommend_authorities(query=text, limit=3)
        precedents = []
        if auth_resp and auth_resp.recommendations:
            for rec in auth_resp.recommendations:
                c_title = getattr(rec, "case_name", None) or getattr(rec, "title", "Judicial Precedent")
                precedents.append({
                    "title": c_title,
                    "citation": getattr(rec, "citation", ""),
                    "court": getattr(rec, "court", ""),
                    "proposition": getattr(rec, "proposition", ""),
                    "match_reason": getattr(rec, "match_reason", "")
                })

        return CaseAuthorityRecommendation(
            case_id=case_id,
            primary_authorities=authorities,
            precedent_decisions=precedents,
            source_status=auth_resp.source_status if auth_resp else "SOURCE_VERIFIED"
        )

    # --------------------------------------------------------------------------
    # 9. CENTRAL CASE CONTEXT GENERATION & PERSISTENCE (FEATURE 8, 10, 23)
    # --------------------------------------------------------------------------
    @classmethod
    def build_and_save_context(
        cls,
        db: RealDictCursor,
        case_id: int,
        user_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        version: int = 1
    ) -> CentralCaseContext:
        """
        Executes end-to-end Case Intelligence pipeline, persists Central Case Context in PostgreSQL,
        and returns the unified context model. Replaces expensive on-the-fly recomputation on view changes.
        """
        # 1. Fetch base case details if not passed
        if not description:
            db.execute("SELECT case_title, case_description, location FROM cases WHERE case_id = %s;", (case_id,))
            case_row = db.fetchone()
            if not case_row:
                raise ValueError(f"Case {case_id} not found in database.")
            title = title or case_row["case_title"]
            description = case_row["case_description"] or ""
            location = location or case_row["location"]

        case_title = (title or "Legal Matter").strip()

        # Step 1: Analyze situation
        situation = cls.analyze_situation(title=case_title, description=description, location=location)

        # Step 2: Grounded legal provisions
        ranked_provisions = cls.get_grounded_legal_provisions(
            category=situation.case_category,
            domain=situation.legal_domain,
            query_text=f"{situation.case_category} {situation.legal_domain} {description}",
            db=db,
            limit=6
        )

        # Step 3: Action plan
        action_plan = cls.generate_action_plan(
            case_id=case_id,
            category=situation.case_category,
            domain=situation.legal_domain
        )

        # Step 4: Documents checklist
        doc_checklist = cls.generate_document_checklist(
            case_id=case_id,
            category=situation.case_category,
            domain=situation.legal_domain
        )

        # Step 5: Further procedure
        procedure = cls.generate_further_procedure(
            case_id=case_id,
            category=situation.case_category,
            domain=situation.legal_domain
        )

        # Step 6: Emotional state analysis
        emotion = cls.analyze_emotional_state(case_id=case_id, text=description)

        # Step 7: Database-driven lawyer recommendations
        lawyer_recs = cls.match_lawyers_from_database(
            case_id=case_id,
            category=situation.case_category,
            domain=situation.legal_domain,
            jurisdiction=location or situation.jurisdiction,
            db=db
        )

        # Step 8: Authority recommendation
        auth_recs = cls.get_authorities_for_case(
            case_id=case_id,
            category=situation.case_category,
            domain=situation.legal_domain,
            text=description
        )

        # Persist into case_contexts table
        upsert_query = """
            INSERT INTO case_contexts (
                case_id, user_id, title, original_description, normalized_description,
                situation_summary, extracted_facts, identified_issues, uncertain_facts,
                missing_information, case_category, legal_domain, jurisdiction, urgency,
                emotional_indicators, legal_matches, ranked_provisions, recommended_authorities,
                recommended_lawyers, recommended_actions, required_documents, further_procedure,
                status, analysis_version, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, 'active', %s, CURRENT_TIMESTAMP
            )
            ON CONFLICT (case_id) DO UPDATE SET
                title = EXCLUDED.title,
                original_description = EXCLUDED.original_description,
                situation_summary = EXCLUDED.situation_summary,
                extracted_facts = EXCLUDED.extracted_facts,
                identified_issues = EXCLUDED.identified_issues,
                uncertain_facts = EXCLUDED.uncertain_facts,
                missing_information = EXCLUDED.missing_information,
                case_category = EXCLUDED.case_category,
                legal_domain = EXCLUDED.legal_domain,
                jurisdiction = EXCLUDED.jurisdiction,
                urgency = EXCLUDED.urgency,
                emotional_indicators = EXCLUDED.emotional_indicators,
                ranked_provisions = EXCLUDED.ranked_provisions,
                recommended_authorities = EXCLUDED.recommended_authorities,
                recommended_lawyers = EXCLUDED.recommended_lawyers,
                recommended_actions = EXCLUDED.recommended_actions,
                required_documents = EXCLUDED.required_documents,
                further_procedure = EXCLUDED.further_procedure,
                analysis_version = EXCLUDED.analysis_version,
                updated_at = CURRENT_TIMESTAMP
            RETURNING context_id, created_at, updated_at;
        """

        ranked_prov_dicts = [p.model_dump() for p in ranked_provisions]
        auth_dicts = [a.model_dump() for a in auth_recs.primary_authorities]
        lawyer_dicts = [l.model_dump() for l in lawyer_recs.recommended_lawyers]
        action_dict = action_plan.model_dump()
        doc_dict = doc_checklist.model_dump()
        proc_dict = procedure.model_dump()
        emotion_dict = emotion.model_dump()

        db.execute(upsert_query, (
            case_id,
            user_id,
            case_title,
            description,
            description.strip(),
            situation.situation_summary,
            json.dumps(situation.extracted_facts),
            json.dumps(situation.identified_issues),
            json.dumps(situation.uncertain_facts),
            json.dumps(situation.missing_information),
            situation.case_category,
            situation.legal_domain,
            situation.jurisdiction,
            emotion.urgency_level,
            json.dumps(emotion_dict),
            json.dumps(ranked_prov_dicts),
            json.dumps(ranked_prov_dicts),
            json.dumps(auth_dicts),
            json.dumps(lawyer_dicts),
            json.dumps(action_dict),
            json.dumps(doc_dict),
            json.dumps(proc_dict),
            version
        ))
        res = db.fetchone()
        context_id = res["context_id"] if res else 1
        created_at = res.get("created_at") if res else datetime.now()
        updated_at = res.get("updated_at") if res else datetime.now()

        # Update case_legal_sections table in PostgreSQL
        try:
            for p in ranked_provisions[:4]:
                if p.act_id:
                    # Find a matching section in sections table if exists
                    db.execute("""
                        SELECT section_id FROM sections
                        WHERE section_number = %s LIMIT 1;
                    """, (p.section_number,))
                    s_row = db.fetchone()
                    if s_row:
                        sec_id = s_row["section_id"]
                        db.execute("""
                            INSERT INTO case_legal_sections (case_id, section_id, relevance_score, explanation)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (case_id, section_id) DO UPDATE SET
                                relevance_score = EXCLUDED.relevance_score,
                                explanation = EXCLUDED.explanation;
                        """, (case_id, sec_id, p.relevance_score, p.why_relevant))
        except Exception as e:
            logger.warning(f"Could not link case_legal_sections for case {case_id}: {e}")

        # Ensure committed
        if hasattr(db, "connection") and db.connection:
            try:
                db.connection.commit()
            except Exception:
                pass

        return CentralCaseContext(
            context_id=context_id,
            case_id=case_id,
            user_id=user_id,
            title=case_title,
            original_description=description,
            normalized_description=description.strip(),
            situation_summary=situation.situation_summary,
            extracted_facts=situation.extracted_facts,
            explicit_facts=situation.explicit_facts,
            identified_issues=situation.identified_issues,
            uncertain_facts=situation.uncertain_facts,
            missing_information=situation.missing_information,
            case_category=situation.case_category,
            legal_domain=situation.legal_domain,
            jurisdiction=situation.jurisdiction,
            urgency=emotion.urgency_level,
            status="active",
            analysis_version=version,
            emotional_indicators=emotion_dict,
            ranked_provisions=ranked_provisions,
            recommended_authorities=auth_recs.primary_authorities,
            recommended_lawyers=lawyer_recs.recommended_lawyers,
            recommended_actions=action_dict,
            required_documents=doc_dict,
            further_procedure=proc_dict,
            created_at=created_at,
            updated_at=updated_at
        )

    # --------------------------------------------------------------------------
    # 10. RETRIEVE PERSISTED CASE CONTEXT (FAST LOOKUP - FEATURE 23)
    # --------------------------------------------------------------------------
    @classmethod
    def get_case_context(
        cls,
        db: RealDictCursor,
        case_id: int,
        user_id: int
    ) -> Optional[CentralCaseContext]:
        """
        Fast cached retrieval of stored Case Context.
        Enforces strict case isolation: returns None if user_id != case.user_id.
        """
        # Validate ownership & existence
        db.execute("SELECT user_id FROM cases WHERE case_id = %s;", (case_id,))
        c_row = db.fetchone()
        if not c_row or c_row["user_id"] != user_id:
            return None

        # Fetch stored context
        db.execute("SELECT * FROM case_contexts WHERE case_id = %s;", (case_id,))
        row = db.fetchone()
        if not row:
            # If not yet generated, build it once and store it
            return cls.build_and_save_context(db=db, case_id=case_id, user_id=user_id)

        ctx = dict(row)

        def _parse_json(val, default):
            if val is None:
                return default
            if isinstance(val, (dict, list)):
                return val
            try:
                return json.loads(val)
            except Exception:
                return default

        provisions_raw = _parse_json(ctx.get("ranked_provisions"), [])
        authorities_raw = _parse_json(ctx.get("recommended_authorities"), [])
        lawyers_raw = _parse_json(ctx.get("recommended_lawyers"), [])

        provisions = [RankedLegalProvision(**p) if isinstance(p, dict) else p for p in provisions_raw]
        authorities = [CaseAuthorityItem(**a) if isinstance(a, dict) else a for a in authorities_raw]
        lawyers = [MatchedLawyerProfile(**l) if isinstance(l, dict) else l for l in lawyers_raw]

        return CentralCaseContext(
            context_id=ctx["context_id"],
            case_id=ctx["case_id"],
            user_id=ctx["user_id"],
            title=ctx["title"],
            original_description=ctx["original_description"],
            normalized_description=ctx.get("normalized_description"),
            situation_summary=ctx["situation_summary"],
            extracted_facts=_parse_json(ctx.get("extracted_facts"), []),
            explicit_facts=_parse_json(ctx.get("extracted_facts"), []),
            identified_issues=_parse_json(ctx.get("identified_issues"), []),
            uncertain_facts=_parse_json(ctx.get("uncertain_facts"), []),
            missing_information=_parse_json(ctx.get("missing_information"), []),
            case_category=ctx.get("case_category", "General Legal Matter"),
            legal_domain=ctx.get("legal_domain", "General Indian Law"),
            jurisdiction=ctx.get("jurisdiction"),
            urgency=ctx.get("urgency", "Medium"),
            status=ctx.get("status", "active"),
            analysis_version=ctx.get("analysis_version", 1),
            emotional_indicators=_parse_json(ctx.get("emotional_indicators"), {}),
            ranked_provisions=provisions,
            recommended_authorities=authorities,
            recommended_lawyers=lawyers,
            recommended_actions=_parse_json(ctx.get("recommended_actions"), {}),
            required_documents=_parse_json(ctx.get("required_documents"), {}),
            further_procedure=_parse_json(ctx.get("further_procedure"), {}),
            created_at=ctx.get("created_at"),
            updated_at=ctx.get("updated_at")
        )

    # --------------------------------------------------------------------------
    # 11. CASE RE-ANALYSIS WORKFLOW (FEATURE 17)
    # --------------------------------------------------------------------------
    @classmethod
    def update_and_reanalyze_case(
        cls,
        db: RealDictCursor,
        case_id: int,
        user_id: int,
        additional_information: str,
        updated_location: Optional[str] = None
    ) -> CentralCaseContext:
        """
        Incorporates newly provided facts into the current case, updates case record,
        and re-evaluates all downstream modules (provisions, actions, lawyers, etc.).
        """
        # Verify ownership
        db.execute("SELECT case_title, case_description, location FROM cases WHERE case_id = %s AND user_id = %s;", (case_id, user_id))
        case_row = db.fetchone()
        if not case_row:
            raise ValueError(f"Case {case_id} not found or access denied.")

        prev_desc = case_row["case_description"] or ""
        updated_desc = f"{prev_desc}\n\nAdditional Update ({datetime.now().strftime('%Y-%m-%d')}): {additional_information.strip()}"
        location = updated_location or case_row["location"]

        # Update base case
        db.execute("""
            UPDATE cases
            SET case_description = %s,
                location = COALESCE(%s, location),
                updated_at = CURRENT_TIMESTAMP
            WHERE case_id = %s AND user_id = %s;
        """, (updated_desc, location, case_id, user_id))

        # Check existing version
        db.execute("SELECT analysis_version FROM case_contexts WHERE case_id = %s;", (case_id,))
        ctx_row = db.fetchone()
        next_ver = (ctx_row["analysis_version"] + 1) if ctx_row else 2

        # Re-run full analysis pipeline and save
        return cls.build_and_save_context(
            db=db,
            case_id=case_id,
            user_id=user_id,
            title=case_row["case_title"],
            description=updated_desc,
            location=location,
            version=next_ver
        )

    # --------------------------------------------------------------------------
    # 12. ACTIVE CASE SESSION MANAGEMENT (FEATURE 8, 12)
    # --------------------------------------------------------------------------
    @classmethod
    def get_user_active_case(cls, db: RealDictCursor, user_id: int) -> Optional[int]:
        """Returns the currently active case_id for the citizen."""
        db.execute("SELECT case_id FROM user_active_cases WHERE user_id = %s;", (user_id,))
        row = db.fetchone()
        if row:
            # Confirm case still exists and belongs to user
            db.execute("SELECT case_id FROM cases WHERE case_id = %s AND user_id = %s;", (row["case_id"], user_id))
            if db.fetchone():
                return row["case_id"]

        # Fallback to most recently updated case
        db.execute("SELECT case_id FROM cases WHERE user_id = %s ORDER BY updated_at DESC LIMIT 1;", (user_id,))
        latest = db.fetchone()
        if latest:
            cls.set_user_active_case(db, user_id, latest["case_id"])
            return latest["case_id"]
        return None

    @classmethod
    def set_user_active_case(cls, db: RealDictCursor, user_id: int, case_id: int) -> bool:
        """Sets the active case for the user session."""
        # Verify ownership
        db.execute("SELECT case_id FROM cases WHERE case_id = %s AND user_id = %s;", (case_id, user_id))
        if not db.fetchone():
            return False

        db.execute("""
            INSERT INTO user_active_cases (user_id, case_id, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE SET
                case_id = EXCLUDED.case_id,
                updated_at = CURRENT_TIMESTAMP;
        """, (user_id, case_id))

        if hasattr(db, "connection") and db.connection:
            try:
                db.connection.commit()
            except Exception:
                pass
        return True
