"""
Vidhik Platform - Unit & Integration Tests for Phase 17 Advanced Legal Knowledge Base
=====================================================================================
Validates:
- LegalKnowledgeService functionality
- Knowledge schemas
- BNS, BNSS, BSA statutory representations
- Predecessor correlations and landmark judgments
- LegalSearchService and LegalRankingService integration
"""

import unittest
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.services.knowledge_service import LegalKnowledgeService
from app.services.search_service import LegalSearchService
from app.services.ranking_service import LegalRankingService
from app.schemas.knowledge_base import (
    KnowledgeOverviewResponse,
    OffenceResponse,
    PunishmentResponse,
    ProcedureResponse,
    EvidenceProvisionResponse,
    PredecessorMappingResponse,
    JudgmentResponse,
    SectionFullContextResponse
)


class TestPhase17KnowledgeBase(unittest.TestCase):

    def test_overview(self):
        overview = LegalKnowledgeService.get_overview()
        self.assertEqual(overview["status"], "active")
        self.assertEqual(overview["total_new_statutes"], 24)
        self.assertEqual(len(overview["supported_statutes"]), 24)
        self.assertGreater(overview["total_offences"], 0)
        self.assertGreater(overview["total_procedures"], 0)
        self.assertGreater(overview["total_evidence_provisions"], 0)
        self.assertGreater(overview["total_predecessor_mappings"], 0)
        self.assertGreater(overview["total_verified_judgments"], 0)


        # Validate with pydantic schema
        schema_obj = KnowledgeOverviewResponse(**overview)
        self.assertEqual(schema_obj.status, "active")

    def test_bns_offences_and_punishments(self):
        offences = LegalKnowledgeService.get_offences()
        self.assertGreaterEqual(len(offences), 5)

        # Test Sec 103 Murder
        sec103 = [o for o in offences if o["section_number"] == "103"]
        self.assertEqual(len(sec103), 1)
        self.assertEqual(sec103[0]["bailable_status"], "Non-Bailable")
        self.assertEqual(sec103[0]["cognizable_status"], "Cognizable")

        # Test Sec 303 Theft & Community Service
        punishments = LegalKnowledgeService.get_punishments()
        theft = [p for p in punishments if p["section_number"] == "303"]
        self.assertEqual(len(theft), 1)
        self.assertTrue(theft[0]["community_service"])

        # Validate Pydantic schema validation
        offence_obj = OffenceResponse(**sec103[0])
        self.assertEqual(offence_obj.section_number, "103")
        pun_obj = PunishmentResponse(**theft[0])
        self.assertTrue(pun_obj.community_service)

    def test_bnss_procedures(self):
        procedures = LegalKnowledgeService.get_procedures()
        self.assertGreaterEqual(len(procedures), 5)

        # Test Sec 173 FIR / Zero FIR
        fir = [p for p in procedures if p["section_number"] == "173" and (p.get("law_id") == 2 or "Nagarik" in p.get("law_name", ""))]
        self.assertEqual(len(fir), 1)
        self.assertEqual(fir[0]["timeline_days"], 14)


        # Test Sec 479 Bail
        bail = [p for p in procedures if p["section_number"] == "479"]
        self.assertEqual(len(bail), 1)
        self.assertIn("Bail", bail[0]["procedure_category"])

        # Validate Pydantic schema
        proc_obj = ProcedureResponse(**fir[0])
        self.assertEqual(proc_obj.timeline_days, 14)

    def test_bsa_evidence_rules(self):
        evidence_rules = LegalKnowledgeService.get_evidence_provisions()
        self.assertGreaterEqual(len(evidence_rules), 5)

        # Test Sec 63 Electronic record certificate
        sec63 = [e for e in evidence_rules if e["section_number"] == "63"]
        self.assertEqual(len(sec63), 1)
        self.assertIn("Electronic", sec63[0]["provision_type"])

        # Validate Pydantic schema
        ev_obj = EvidenceProvisionResponse(**sec63[0])
        self.assertEqual(ev_obj.section_number, "63")

    def test_predecessor_correlations(self):
        preds = LegalKnowledgeService.get_predecessor_mappings()
        self.assertGreaterEqual(len(preds), 15)

        # Test IPC 302 -> BNS 103
        mapping_302 = [p for p in preds if p["old_section_number"] == "302" and p["new_section_number"] == "103"]
        self.assertEqual(len(mapping_302), 1)
        self.assertEqual(mapping_302[0]["correspondence_type"], "Substantially Altered")

        # Test IEA 65B -> BSA 63
        mapping_65b = [p for p in preds if p["old_section_number"] == "65B" and p["new_section_number"] == "63"]
        self.assertEqual(len(mapping_65b), 1)

        # Validate Pydantic schema
        pred_obj = PredecessorMappingResponse(**mapping_302[0])
        self.assertEqual(pred_obj.old_section_number, "302")

    def test_verified_judgments(self):
        judgments = LegalKnowledgeService.get_judgments()
        self.assertGreaterEqual(len(judgments), 4)

        # Test Arjun Panditrao Khotkar
        arjun = [j for j in judgments if "(2020) 7 SCC 1" == j.get("citation")]
        self.assertEqual(len(arjun), 1)
        self.assertIn("Supreme Court", arjun[0]["court"])

        # Validate Pydantic schema
        j_obj = JudgmentResponse(**arjun[0])
        self.assertEqual(j_obj.citation, "(2020) 7 SCC 1")

    def test_section_full_context_graph(self):
        ctx = LegalKnowledgeService.get_section_full_context("103", "BNS")
        self.assertEqual(ctx["section_number"], "103")
        self.assertIsNotNone(ctx["offence"])
        self.assertIsNotNone(ctx["punishment"])
        self.assertGreater(len(ctx["procedures"]), 0)
        self.assertGreater(len(ctx["evidence_provisions"]), 0)
        self.assertGreater(len(ctx["predecessor_mappings"]), 0)
        self.assertGreater(len(ctx["judgments"]), 0)

        # Validate Pydantic schema
        ctx_obj = SectionFullContextResponse(**ctx)
        self.assertEqual(ctx_obj.section_number, "103")

    def test_deterministic_ranking_preservation(self):
        cands = [
            {"law_id": 1, "law_name": "Act A", "short_name": "A", "section_id": 1, "section_number": "15", "section_title": "General", "manual_review_required": False},
            {"law_id": 2, "law_name": "Act B", "short_name": "B", "section_id": 2, "section_number": "103", "section_title": "Specific", "manual_review_required": False}
        ]
        ranked = LegalRankingService.rank_candidates(cands, query="103")
        self.assertEqual(ranked[0]["section_number"], "103")

    def test_all_24_acts_coverage(self):
        acts = LegalKnowledgeService.get_acts()
        self.assertEqual(len(acts), 24)
        expected_short_names = [
            "BNS", "BNSS", "BSA", "IT Act", "POCSO Act", "JJ Act",
            "PWDVA", "DPA", "POSH Act", "HMA", "HSA", "SMA",
            "ICA", "SRA", "TPA", "Registration Act", "NI Act", "CPA",
            "MVA", "RTI Act", "LSAA", "Arbitration Act", "Companies Act", "IBC"
        ]
        actual_short_names = [a["short_name"] for a in acts]
        for name in expected_short_names:
            self.assertIn(name, actual_short_names, f"Expected {name} in 24 Acts")

    def test_specialized_acts_provisions(self):
        # 1. NI Act Sec 138 (Cheque Bounce)
        ni_ctx = LegalKnowledgeService.get_section_full_context("138", "NI Act")
        self.assertEqual(ni_ctx["section_number"], "138")
        self.assertIn("Negotiable Instruments", ni_ctx["law_name"])
        self.assertIn("cheque", ni_ctx["full_text"].lower())
        self.assertIsNotNone(ni_ctx["offence"])
        self.assertIsNotNone(ni_ctx["punishment"])

        # 2. POCSO Act Sec 3
        pocso_ctx = LegalKnowledgeService.get_section_full_context("3", "POCSO Act")
        self.assertEqual(pocso_ctx["section_number"], "3")
        self.assertIn("Sexual Offences", pocso_ctx["law_name"])
        self.assertIsNotNone(pocso_ctx["offence"])

        # 3. IT Act Sec 66
        it_ctx = LegalKnowledgeService.get_section_full_context("66", "IT Act")
        self.assertEqual(it_ctx["section_number"], "66")
        self.assertIn("Technology", it_ctx["law_name"])

        # 4. RTI Act Sec 6
        rti_ctx = LegalKnowledgeService.get_section_full_context("6", "RTI Act")
        self.assertEqual(rti_ctx["section_number"], "6")
        self.assertIn("Information", rti_ctx["law_name"])

    def test_judgments_unavailable_status(self):
        # Supreme Court judgments must only exist for Acts 1-3
        # For Acts 4-24, judgments must be empty with NOT IN SOURCE preserved
        for act_id in [4, 5, 7, 8, 17, 20, 23, 24]:
            judgments = LegalKnowledgeService.get_judgments(act_id=act_id)
            self.assertEqual(len(judgments), 0, f"Expected 0 judgments for Act ID {act_id} (NOT IN SOURCE)")

    def test_multi_statute_search(self):
        queries = ["cheque", "domestic violence", "arbitration", "RTI", "POCSO", "insolvency", "fraud"]
        for q in queries:
            results = LegalKnowledgeService.search_knowledge_base(query=q)
            self.assertGreater(len(results), 0, f"Search failed for query '{q}'")


if __name__ == "__main__":
    unittest.main()
