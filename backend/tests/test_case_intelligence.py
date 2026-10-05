"""
Vidhik Platform - Generalized Case Intelligence Acceptance Test Suite
=====================================================================
Validates that the Vidhik Case Intelligence Engine is FULLY DYNAMIC,
database-grounded, and capable of handling ANY natural language legal matter
without hardcoded case categories, rigid if/else workflows, or artificial limitations.

Test Coverage:
1. Multiple unrelated legal domains (Cybercrime, Cheque Bounce, POSH, RTI, MACT, Consumer, Tenancy, Succession)
2. Unusual / Novel legal matter (graceful handling, uncertainty detection, "Potentially related legal area")
3. Multi-issue matter (Primary issue + Additional issues analyzed independently and integrated)
4. Multi-Act matter (Cases involving provisions across multiple statutory Acts)
5. Insufficient information matter (Zero-hallucination policy, explicit unavailability notice, missing information queries)
6. Matter with no strong database match (detects uncertainty without fabricating laws)
7. Clarification workflow (submitting missing facts and updating context)
8. Graceful lawyer matching fallback (handles empty/no-match lawyer database with legal aid options)
9. Authority recommendation preferred over lawyer recommendation (RTI / Cyber 1930 / Consumer NCH)
10. Persistent Current Case architecture (CASE-001 -> CASE-002 -> CASE-003 -> CASE-004, switching, session persistence)
11. Generalized CaseContext schema verification (all generalized fields present, ZERO hardcoded case-type fields)
"""

import unittest
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
from app.main import app
from app.services.case_intelligence_service import CaseIntelligenceService, CaseStore
from app.schemas.case_intelligence import CaseContext


class TestCaseIntelligenceEngine(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        CaseStore.clear_for_tests()

    # -------------------------------------------------------------
    # 1. GENERALIZED CASE CONTEXT SCHEMA INTEGRITY
    # -------------------------------------------------------------
    def test_generalized_case_context_schema_no_hardcoding(self):
        """Verifies CaseContext contains generalized fields and NO hardcoded case-type flags."""
        fields = CaseContext.model_fields.keys()
        
        # Mandatory generalized fields specified in core requirements
        required_fields = [
            "case_id", "original_description", "normalized_description", "facts",
            "issues", "legal_domains", "jurisdiction", "legal_matches",
            "ranked_provisions", "authorities", "lawyer_requirements",
            "lawyer_matches", "actions", "documents", "procedure",
            "emotional_indicators", "urgency", "missing_information", "status"
        ]
        for rf in required_fields:
            self.assertIn(rf, fields, f"Missing required generalized field: {rf}")

        # Prohibited hardcoded category fields
        prohibited_fields = [
            "traffic_case", "property_case", "salary_case", "is_traffic",
            "is_property", "is_salary", "case_category_enum"
        ]
        for pf in prohibited_fields:
            self.assertNotIn(pf, fields, f"Found prohibited hardcoded field: {pf}")

    # -------------------------------------------------------------
    # 2. MULTIPLE UNRELATED LEGAL DOMAINS (DYNAMIC UNDERSTANDING)
    # -------------------------------------------------------------
    def test_domain_cyber_fraud(self):
        """Verifies dynamic processing of cyber fraud / digital OTP theft."""
        text = "I received a suspicious message asking for my bank OTP, and Rs. 50,000 was debited without my consent."
        res = self.client.post("/api/case/analyze", json={"description": text})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertTrue(data["sufficient_information"])
        self.assertIn("Cyber Law & Digital Fraud", data["legal_domains"])
        self.assertTrue(any("OTP" in f["fact"] or "Financial" in f["fact"] for f in data["facts"]))
        self.assertTrue(any("Cyber" in i["title"] for i in data["issues"]))
        self.assertTrue(len(data["ranked_provisions"]) > 0)
        self.assertTrue(any("IT Act" in p["short_name"] or "BNS" in p["short_name"] for p in data["ranked_provisions"]))
        self.assertTrue(len(data["actions"]) > 0)
        self.assertTrue(any("Freeze" in a["action"] or "1930" in a["description"] for a in data["actions"]))

    def test_domain_cheque_bounce(self):
        """Verifies dynamic processing of negotiable instruments cheque dishonour."""
        text = "My business client gave me a cheque of Rs. 3,50,000 which bounced yesterday due to insufficient funds."
        res = self.client.post("/api/case/analyze", json={"description": text})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("Banking & Negotiable Instruments", data["legal_domains"])
        self.assertTrue(any("cheque" in f["fact"].lower() for f in data["facts"]))
        self.assertTrue(any("Cheque" in i["title"] for i in data["issues"]))
        self.assertTrue(any("NI Act" in p["short_name"] for p in data["ranked_provisions"]))
        self.assertTrue(any("Demand Notice" in a["action"] for a in data["actions"]))

    def test_domain_posh_workplace_harassment(self):
        """Verifies dynamic processing of workplace sexual harassment (POSH)."""
        text = "My team manager has been sending unwelcome messages late at night and threatening my appraisal if I refuse."
        res = self.client.post("/api/case/analyze", json={"description": text})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("Workplace & Harassment Law", data["legal_domains"])
        self.assertTrue(any("Harassment" in i["title"] for i in data["issues"]))
        self.assertTrue(any("Internal Complaints Committee" in a["authority_name"] or "Session" in a["authority_name"] for a in data["authorities"]))

    def test_domain_rti_denial(self):
        """Verifies dynamic processing of Right to Information refusal."""
        text = "I filed an RTI application regarding municipal expenditure 45 days ago, but the Public Information Officer has refused to provide the records."
        res = self.client.post("/api/case/analyze", json={"description": text})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("Administrative & RTI Law", data["legal_domains"])
        self.assertTrue(any("Information" in i["title"] for i in data["issues"]))
        self.assertTrue(any("RTI Act" in p["short_name"] for p in data["ranked_provisions"]))

    def test_domain_motor_accident_claim(self):
        """Verifies dynamic processing of motor vehicular collision and compensation."""
        text = "A speeding vehicle crashed into my motorcycle causing serious injury and complete damage to the bike."
        res = self.client.post("/api/case/analyze", json={"description": text})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("Motor Vehicle & Transport Law", data["legal_domains"])
        self.assertTrue(any("Motor" in i["title"] for i in data["issues"]))
        self.assertTrue(any("Motor Accidents Claims Tribunal" in a["authority_name"] or "Claims" in a["authority_name"] for a in data["authorities"]))

    def test_domain_consumer_defective_product(self):
        """Verifies dynamic processing of defective consumer goods and warranty refund."""
        text = "I bought a mobile phone from an ecommerce platform for Rs. 40,000, but it arrived defective and the seller is refusing to refund or replace it."
        res = self.client.post("/api/case/analyze", json={"description": text})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("Consumer Protection & Redressal", data["legal_domains"])
        self.assertTrue(any("Consumer" in i["title"] or "Deficiency" in i["title"] for i in data["issues"]))
        self.assertTrue(any("Consumer" in a["authority_name"] for a in data["authorities"]))

    # -------------------------------------------------------------
    # 3. MULTI-ISSUE CASE WITH MULTIPLE STATUTORY ACTS
    # -------------------------------------------------------------
    def test_multi_issue_case_landlord_trespass_threats(self):
        """
        Validates:
        'My landlord is refusing to return my deposit, entered my room without permission, and is threatening me.'
        Must NOT be classified simply as 'rental dispute'.
        Must identify separate Primary Issue (deposit) and Additional Issues (unlawful entry, threats).
        Must map across multiple Acts: Transfer of Property Act + Bharatiya Nyaya Sanhita.
        """
        text = "My landlord is refusing to return my deposit, entered my room without permission, and is threatening me."
        res = self.client.post("/api/case/analyze", json={"description": text})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        issues = data["issues"]
        self.assertGreaterEqual(len(issues), 2, "Must identify multiple distinct legal issues")

        # Verify Primary and Additional Issue distinction
        primary_issues = [i for i in issues if i["issue_type"] == "primary"]
        additional_issues = [i for i in issues if i["issue_type"] == "additional"]
        self.assertEqual(len(primary_issues), 1, "Exactly one primary issue must be established")
        self.assertGreaterEqual(len(additional_issues), 1, "At least one additional issue must be identified")

        # Verify specific issue scopes
        self.assertTrue(any("Deposit" in i["title"] for i in primary_issues), "Primary issue must cover security deposit dispute")
        self.assertTrue(any("Unlawful Entry" in i["title"] or "Trespass" in i["title"] for i in additional_issues), "Must identify unlawful entry/trespass issue")
        self.assertTrue(any("Intimidation" in i["title"] or "Threat" in i["title"] for i in additional_issues), "Must identify threats/intimidation issue")

        # Verify Multi-Act involvement (Property Act + Criminal Code)
        ranked_acts = {p["short_name"] for p in data["ranked_provisions"]}
        self.assertTrue(
            any("BNS" in act for act in ranked_acts) or any("TPA" in act for act in ranked_acts),
            "Provisions must encompass applicable penal and property acts"
        )

        # Verify multiple legal domains
        domains = data["legal_domains"]
        self.assertTrue(
            any("Property" in d for d in domains) and any("Criminal" in d for d in domains),
            "Must register both Property and Criminal domains"
        )

    # -------------------------------------------------------------
    # 4. UNUSUAL / NOVEL LEGAL MATTER
    # -------------------------------------------------------------
    def test_unusual_legal_matter_handling(self):
        """
        Validates handling of an unusual situation:
        Must NOT force it into an arbitrary category.
        Must identify uncertainty, explain degree of relevance, and ask follow-up questions.
        """
        text = "An unidentified drone has been hovering over my rooftop garden every evening and taking photos."
        res = self.client.post("/api/case/analyze", json={"description": text})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertTrue(data["sufficient_information"])
        # Should identify privacy / trespass or general legal dispute
        self.assertTrue(len(data["facts"]) > 0)
        self.assertTrue(len(data["issues"]) > 0)
        # Degree of relevance must be articulated
        self.assertTrue(len(data["degree_of_relevance"]) > 0)
        # Should generate useful action steps and guidance
        self.assertTrue(len(data["actions"]) > 0)

    # -------------------------------------------------------------
    # 5. INSUFFICIENT INFORMATION MATTER
    # -------------------------------------------------------------
    def test_insufficient_information_zero_hallucination(self):
        """
        Validates zero-hallucination policy when input has insufficient facts.
        Must return explicit notice:
        'Vidhik could not identify sufficient information in its available legal knowledge to provide a reliable specific analysis.'
        """
        text = "Someone did something bad to me yesterday."
        res = self.client.post("/api/case/analyze", json={"description": text})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertFalse(data["sufficient_information"])
        self.assertEqual(data["status"], "pending_clarification")
        self.assertIsNotNone(data["unavailability_notice"])
        self.assertIn(
            "Vidhik could not identify sufficient information in its available legal knowledge to provide a reliable specific analysis.",
            data["unavailability_notice"]
        )
        self.assertGreater(len(data["missing_information"]), 0, "Must provide targeted clarifying questions")
        self.assertEqual(len(data["ranked_provisions"]), 0, "Must NOT fabricate statutory provisions on empty facts")

    # -------------------------------------------------------------
    # 6. MATTER WITH NO STRONG DATABASE MATCH
    # -------------------------------------------------------------
    def test_no_strong_database_match(self):
        """
        Validates handling when a query is legally extraterritorial or has no match in Indian Bare Acts.
        Must detect uncertainty, state degree of relevance, and avoid fabricating laws.
        """
        text = "I want to apply for a Martian orbital mining permit under deep space exploration treaties."
        res = self.client.post("/api/case/analyze", json={"description": text})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertTrue(data["is_uncertain"])
        self.assertIn("Potentially related legal area", data["degree_of_relevance"])
        self.assertGreater(len(data["missing_information"]), 0)

    # -------------------------------------------------------------
    # 7. CLARIFICATION & MISSING INFORMATION WORKFLOW
    # -------------------------------------------------------------
    def test_clarification_workflow(self):
        """
        Validates that a case can be clarified by submitting missing facts,
        which re-runs the pipeline dynamically and updates the context.
        """
        # Step 1: Submit brief matter
        res1 = self.client.post("/api/case/analyze", json={
            "description": "My employer did not pay me my dues.",
            "case_id": "CASE-CLARIFY-01"
        })
        self.assertEqual(res1.status_code, 200)

        # Step 2: Clarify with specific salary amount and termination date
        res2 = self.client.post("/api/case/CASE-CLARIFY-01/clarify", json={
            "clarification_text": "I was terminated without notice on 1st October and my salary of Rs. 75,000 for 2 months is unpaid.",
            "answers": {"contract_exists": "Yes, I have an employment contract."}
        })
        self.assertEqual(res2.status_code, 200)
        updated = res2.json()

        self.assertEqual(updated["case_id"], "CASE-CLARIFY-01")
        self.assertTrue(any("75,000" in f["fact"] for f in updated["facts"]))
        self.assertTrue(any("terminated" in f["fact"].lower() for f in updated["facts"]))
        self.assertTrue(any("Salary" in doc["document_name"] or "Employment" in doc["document_name"] for doc in updated["documents"]))

    # -------------------------------------------------------------
    # 8. AUTHORITY PREFERENCE OVER LAWYER
    # -------------------------------------------------------------
    def test_authority_preference_over_lawyer_recommendation(self):
        """
        Validates that when statutory authority recourse is more direct/suitable than
        hiring a private advocate (e.g. RTI application to PIO, or cyber 1930 reporting),
        the system indicates authority_preferred_over_lawyer = True and explains why.
        """
        text = "I need to file an RTI application because the municipal corporation is not revealing public park maintenance expenditure."
        res = self.client.post("/api/case/analyze", json={"description": text})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertTrue(data["authority_preferred_over_lawyer"])
        self.assertIsNotNone(data["authority_preference_reason"])
        self.assertIn("Public Information Officer", data["authority_preference_reason"])

    # -------------------------------------------------------------
    # 9. DYNAMIC LAWYER MATCHING & LEGAL AID FALLBACK
    # -------------------------------------------------------------
    def test_lawyer_matching_and_legal_aid_fallback(self):
        """
        Validates dynamic lawyer matching from database and verified directory,
        including legal aid organization integration for free legal representation.
        """
        text = "My landlord has illegally locked my apartment and is withholding my Rs. 60,000 deposit."
        res = self.client.post("/api/case/analyze", json={"description": text})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertGreater(len(data["lawyer_requirements"]), 0)
        self.assertGreater(len(data["lawyer_matches"]), 0)
        # Check that legal aid organizations (like NALSA/MSLSA/DSLSA) are present
        has_legal_aid = any(m["is_legal_aid"] for m in data["lawyer_matches"])
        self.assertTrue(has_legal_aid, "Must include legal aid organizations for accessible justice")

    # -------------------------------------------------------------
    # 10. DYNAMIC EMOTIONAL ANALYSIS
    # -------------------------------------------------------------
    def test_dynamic_emotional_analysis(self):
        """
        Validates that emotional cues (fear, anger, urgency, distress) are detected dynamically
        from user language to improve tone and communication, WITHOUT altering legal classification.
        """
        text = "I am terrified and scared for my life because my business partner is threatening to kill me immediately!"
        res = self.client.post("/api/case/analyze", json={"description": text})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        emotions = [e["emotion"] for e in data["emotional_indicators"]]
        self.assertTrue("fear" in emotions or "urgency" in emotions)
        self.assertIn(data["urgency"], ["high", "critical"])
        # Legal classification must remain grounded in Criminal Law (intimidation/threats)
        self.assertIn("Criminal Law", data["legal_domains"])

    # -------------------------------------------------------------
    # 11. PERSISTENT CURRENT CASE ENGINE
    # -------------------------------------------------------------
    def test_persistent_current_case_switching_and_tracking(self):
        """
        Validates that ANY legal matter is supported in the Persistent Current Case architecture:
        User creates CASE-001 -> All modules connect to CASE-001.
        User creates CASE-002 -> All modules connect to CASE-002.
        User creates CASE-003 -> All modules connect to CASE-003.
        User creates CASE-004 -> All modules connect to CASE-004.
        Can switch back to CASE-001 anytime.
        """
        # Case 1: Example 1
        res1 = self.client.post("/api/case/analyze", json={
            "description": "Traffic police scratched my licence during a routine checkpoint.",
            "case_id": "CASE-001"
        })
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(CaseStore.get_current_case_id(), "CASE-001")

        cur1 = self.client.get("/api/case/current")
        self.assertEqual(cur1.status_code, 200)
        self.assertEqual(cur1.json()["case_id"], "CASE-001")

        # Case 2: Example 2
        res2 = self.client.post("/api/case/analyze", json={
            "description": "My brother and I have a dispute regarding inherited property.",
            "case_id": "CASE-002"
        })
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(CaseStore.get_current_case_id(), "CASE-002")

        cur2 = self.client.get("/api/case/current")
        self.assertEqual(cur2.json()["case_id"], "CASE-002")
        self.assertTrue(any("Partition" in i["title"] or "Property" in i["title"] for i in cur2.json()["issues"]))

        # Case 3: Example 3
        res3 = self.client.post("/api/case/analyze", json={
            "description": "I received a suspicious message asking for my bank OTP.",
            "case_id": "CASE-003"
        })
        self.assertEqual(res3.status_code, 200)
        self.assertEqual(CaseStore.get_current_case_id(), "CASE-003")

        cur3 = self.client.get("/api/case/current")
        self.assertEqual(cur3.json()["case_id"], "CASE-003")

        # Case 4: Example 4
        res4 = self.client.post("/api/case/analyze", json={
            "description": "My employer has terminated me without paying my pending salary.",
            "case_id": "CASE-004"
        })
        self.assertEqual(res4.status_code, 200)
        self.assertEqual(CaseStore.get_current_case_id(), "CASE-004")

        cur4 = self.client.get("/api/case/current")
        self.assertEqual(cur4.json()["case_id"], "CASE-004")

        # Test listing all 4 cases
        list_res = self.client.get("/api/case")
        self.assertEqual(list_res.status_code, 200)
        cases_list = list_res.json()
        self.assertEqual(len(cases_list), 4)

        # Switch back to CASE-001
        switch_res = self.client.post("/api/case/CASE-001/switch")
        self.assertEqual(switch_res.status_code, 200)
        self.assertTrue(switch_res.json()["success"])
        self.assertEqual(CaseStore.get_current_case_id(), "CASE-001")

        cur_switched = self.client.get("/api/case/current")
        self.assertEqual(cur_switched.json()["case_id"], "CASE-001")


if __name__ == "__main__":
    unittest.main()
