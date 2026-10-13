"""
Vidhik Platform - Unit & Integration Tests for Authority Recommendation Module
==============================================================================
Validates:
1. Exact verified authority match
2. Section-to-authority match (Tier 1 exact mapping)
3. Law-to-authority match (Tier 2 statutory relationship)
4. Relevant legal concept match (Tier 3 & 4 propositions/concepts)
5. Irrelevant query handling (NO MATCH)
6. Unknown query handling (NO MATCH)
7. Authority unavailable / NOT IN SOURCE transparency (Acts 4-24)
8. Zero-fabrication guarantee (all recommendations strictly match verified records)
9. Deterministic ranking and consistent ordering
10. Preservation of existing legal search behavior
11. Read-only API endpoints verification:
    - GET /health
    - GET /api/laws
    - GET /api/sections
    - GET /api/search
    - GET /api/authorities/recommend
"""

import unittest
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.services.authority_service import AuthorityRecommendationService
from app.services.search_service import LegalSearchService
from app.services.ranking_service import LegalRankingService
from app.schemas.authority import AuthorityResult, AuthorityRecommendationResponse


class MockCursor:
    """Mock database cursor for API isolation testing."""
    def execute(self, *args, **kwargs):
        pass

    def fetchone(self):
        return {"total": 0, "count": 0}

    def fetchall(self):
        return []


def mock_get_db():
    yield MockCursor()


class TestAuthorityRecommendation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.verified_citations = {
            "(2020) 7 SCC 1",
            "(2022) 10 SCC 51",
            "(2014) 2 SCC 1",
            "(1980) 2 SCC 684",
            "(2018) 2 SCC 801"
        }
        cls.verified_case_titles = {
            "Arjun Panditrao Khotkar v. Kailash Kushanrao Gorantyal and Others",
            "Satender Kumar Antil v. Central Bureau of Investigation and Another",
            "Lalita Kumari v. Government of Uttar Pradesh and Others",
            "Bachan Singh v. State of Punjab",
            "Shafhi Mohammad v. State of Himachal Pradesh"
        }

    # 1. Exact Verified Authority Match
    def test_exact_verified_authority_match(self):
        # Query by exact citation
        res = AuthorityRecommendationService.recommend_authorities(query="(2020) 7 SCC 1")
        self.assertEqual(res.source_status, "verified")
        self.assertGreaterEqual(res.total, 1)
        top = res.recommendations[0]
        self.assertEqual(top.citation, "(2020) 7 SCC 1")
        self.assertIn("Arjun Panditrao Khotkar", top.case_name)
        self.assertEqual(top.verification_status, "verified")

        # Query by case title keyword
        res2 = AuthorityRecommendationService.recommend_authorities(query="Bachan Singh")
        self.assertEqual(res2.source_status, "verified")
        self.assertGreaterEqual(res2.total, 1)
        self.assertEqual(res2.recommendations[0].citation, "(1980) 2 SCC 684")

    # 2. Section-to-Authority Match (Tier 1 Exact Mapping)
    def test_section_to_authority_match(self):
        # Section 63 BSA -> Arjun Panditrao Khotkar
        res_bsa = AuthorityRecommendationService.recommend_authorities(section_number="63", law_id=3)
        self.assertEqual(res_bsa.source_status, "verified")
        self.assertEqual(res_bsa.total, 1)
        rec_bsa = res_bsa.recommendations[0]
        self.assertEqual(rec_bsa.citation, "(2020) 7 SCC 1")
        self.assertEqual(rec_bsa.match_type, "exact_section_mapping")
        self.assertEqual(rec_bsa.relevance_score, 1.00)
        self.assertIn("Section 63", rec_bsa.reason)

        # Section 103 BNS -> Bachan Singh
        res_bns = AuthorityRecommendationService.recommend_authorities(section_number="103", law_id=1)
        self.assertEqual(res_bns.source_status, "verified")
        rec_bns = res_bns.recommendations[0]
        self.assertEqual(rec_bns.citation, "(1980) 2 SCC 684")
        self.assertEqual(rec_bns.match_type, "exact_section_mapping")

        # Section 173 BNSS -> Lalita Kumari
        res_fir = AuthorityRecommendationService.recommend_authorities(section_number="173", law_id=2)
        self.assertEqual(res_fir.source_status, "verified")
        self.assertEqual(res_fir.recommendations[0].citation, "(2014) 2 SCC 1")

        # Section 105 BNSS -> Shafhi Mohammad
        res_search = AuthorityRecommendationService.recommend_authorities(section_number="105", law_id=2)
        self.assertEqual(res_search.source_status, "verified")
        self.assertEqual(res_search.recommendations[0].citation, "(2018) 2 SCC 801")

        # Section 479 BNSS -> Satender Kumar Antil
        res_bail = AuthorityRecommendationService.recommend_authorities(section_number="479", law_id=2)
        self.assertEqual(res_bail.source_status, "verified")
        self.assertEqual(res_bail.recommendations[0].citation, "(2022) 10 SCC 51")

    # 3. Law-to-Authority Match (Tier 2 Statutory Relationship)
    def test_law_to_authority_match(self):
        # Law ID 2 (BNSS) with Section 35 (Arrest procedure) -> Satender Kumar Antil
        res = AuthorityRecommendationService.recommend_authorities(law_id=2, section_number="35")
        self.assertEqual(res.source_status, "verified")
        self.assertGreaterEqual(res.total, 1)
        self.assertEqual(res.recommendations[0].citation, "(2022) 10 SCC 51")
        self.assertIn("Section 35", res.recommendations[0].matched_sections[0])

    # 4. Relevant Legal Concept Match (Tier 3 & Tier 4)
    def test_relevant_legal_concept_match(self):
        # Tier 3 Proposition: "rarest of rare"
        res_prop = AuthorityRecommendationService.recommend_authorities(query="rarest of rare doctrine in murder")
        self.assertEqual(res_prop.source_status, "verified")
        self.assertEqual(res_prop.recommendations[0].citation, "(1980) 2 SCC 684")
        self.assertIn(res_prop.recommendations[0].match_type, ["legal_proposition_match", "exact_section_mapping"])

        # Tier 3 Proposition: "mandatory fir"
        res_fir = AuthorityRecommendationService.recommend_authorities(query="mandatory fir registration")
        self.assertEqual(res_fir.source_status, "verified")
        self.assertEqual(res_fir.recommendations[0].citation, "(2014) 2 SCC 1")

        # Tier 3 Proposition: "undertrial bail"
        res_bail = AuthorityRecommendationService.recommend_authorities(query="undertrial bail detention threshold")
        self.assertEqual(res_bail.source_status, "verified")
        self.assertEqual(res_bail.recommendations[0].citation, "(2022) 10 SCC 51")

        # Tier 3 Proposition: "videography in search and seizure"
        res_vid = AuthorityRecommendationService.recommend_authorities(query="search and seizure videography")
        self.assertEqual(res_vid.source_status, "verified")
        self.assertEqual(res_vid.recommendations[0].citation, "(2018) 2 SCC 801")

        # Tier 3 Proposition: "electronic record certificate"
        res_elec = AuthorityRecommendationService.recommend_authorities(query="electronic record 65b certificate")
        self.assertEqual(res_elec.source_status, "verified")
        self.assertEqual(res_elec.recommendations[0].citation, "(2020) 7 SCC 1")

    # 5. Irrelevant Query Handling
    def test_irrelevant_query(self):
        irrelevant_queries = [
            "chocolate cake baking recipe",
            "astronomy telescope physics",
            "quantum entanglement thermodynamics",
            "weather forecast tomorrow"
        ]
        for q in irrelevant_queries:
            res = AuthorityRecommendationService.recommend_authorities(query=q)
            self.assertEqual(res.total, 0, f"Expected 0 results for '{q}'")
            self.assertEqual(res.source_status, "NO MATCH")
            self.assertEqual(len(res.recommendations), 0)

    # 6. Unknown Query Handling
    def test_unknown_query(self):
        unknown_queries = ["asdfghjkl9876", "qwertyuiop12345", "zzzxxxyyy000"]
        for q in unknown_queries:
            res = AuthorityRecommendationService.recommend_authorities(query=q)
            self.assertEqual(res.total, 0)
            self.assertEqual(res.source_status, "NO MATCH")
            self.assertEqual(res.recommendations, [])

    # 7. Authority Unavailable / NOT IN SOURCE (Acts 4-24)
    def test_authority_unavailable_not_in_source(self):
        # 1. Query by law_id for Acts with no verified judgments (e.g. NI Act: 17, IT Act: 4, POCSO: 5)
        for act_id in [4, 5, 7, 8, 17, 20, 22, 23, 24]:
            res = AuthorityRecommendationService.recommend_authorities(law_id=act_id)
            self.assertEqual(res.source_status, "NOT IN SOURCE", f"Expected NOT IN SOURCE for law_id={act_id}")
            self.assertEqual(res.total, 0)
            self.assertEqual(res.recommendations, [])

        # 2. Query by domain keywords specific to Acts 4-24
        not_in_source_queries = [
            "cheque bounce under section 138",
            "domestic violence protection order under pwdva",
            "right to information pio response",
            "arbitral tribunal appointment under arbitration act",
            "corporate insolvency resolution process under ibc"
        ]
        for q in not_in_source_queries:
            res = AuthorityRecommendationService.recommend_authorities(query=q)
            self.assertEqual(res.source_status, "NOT IN SOURCE", f"Expected NOT IN SOURCE for '{q}'")
            self.assertEqual(res.total, 0)
            self.assertEqual(res.recommendations, [])

    # 8. No Fabricated Authority
    def test_no_fabricated_authority(self):
        # Collect all recommendations from multiple queries
        test_queries = [
            "(2020) 7 SCC 1",
            "mandatory fir",
            "rarest of rare",
            "bail guidelines",
            "search and seizure",
            "electronic record certificate"
        ]
        all_recommended_citations = set()
        all_recommended_titles = set()

        for q in test_queries:
            res = AuthorityRecommendationService.recommend_authorities(query=q)
            for rec in res.recommendations:
                all_recommended_citations.add(rec.citation)
                all_recommended_titles.add(rec.case_name)
                # Verify that each recommendation has verified status and valid court
                self.assertEqual(rec.verification_status, "verified")
                self.assertIn("Supreme Court of India", rec.court)
                self.assertIsNotNone(rec.legal_proposition)
                self.assertGreater(len(rec.legal_proposition), 10)
                self.assertIsNotNone(rec.reason)
                self.assertIn("Tier", rec.reason)

        # Assert strict subset: NO case title or citation may exist outside project verified set
        for cit in all_recommended_citations:
            self.assertIn(cit, self.verified_citations, f"Fabricated citation detected: {cit}")

        for title in all_recommended_titles:
            self.assertIn(title, self.verified_case_titles, f"Fabricated case title detected: {title}")

    # 9. Deterministic Ordering
    def test_deterministic_ordering(self):
        # Query with multiple potential matches
        res1 = AuthorityRecommendationService.recommend_authorities(query="investigation fir videography")
        res2 = AuthorityRecommendationService.recommend_authorities(query="investigation fir videography")

        self.assertEqual(res1.total, res2.total)
        self.assertEqual(len(res1.recommendations), len(res2.recommendations))

        for r1, r2 in zip(res1.recommendations, res2.recommendations):
            self.assertEqual(r1.authority_id, r2.authority_id)
            self.assertEqual(r1.case_name, r2.case_name)
            self.assertEqual(r1.relevance_score, r2.relevance_score)
            self.assertEqual(r1.reason, r2.reason)

        # Verify sorted by relevance_score descending
        scores = [r.relevance_score for r in res1.recommendations]
        self.assertEqual(scores, sorted(scores, reverse=True))

    # 10. Existing Search Behavior Remains Unchanged
    def test_existing_search_remains_unchanged(self):
        # Test snippet extraction
        sample_text = "Whoever commits murder shall be punished with death, or imprisonment for life, and shall also be liable to fine."
        snippet = LegalSearchService.extract_snippet(
            full_text=sample_text,
            description="Punishment for murder",
            section_title="Punishment for murder",
            law_name="Bharatiya Nyaya Sanhita, 2023",
            query="murder"
        )
        self.assertIsNotNone(snippet)
        self.assertIn("murder", snippet.lower())

        # Test deterministic ranking consistency
        candidates = [
            {"law_id": 1, "law_name": "Act A", "short_name": "A", "section_id": 1, "section_number": "15", "section_title": "General", "manual_review_required": False},
            {"law_id": 2, "law_name": "Act B", "short_name": "B", "section_id": 2, "section_number": "103", "section_title": "Specific", "manual_review_required": False}
        ]
        ranked = LegalRankingService.rank_candidates(candidates, query="103")
        self.assertEqual(ranked[0]["section_number"], "103")

    # 11. API Endpoints Verification via TestClient
    def test_api_endpoints_health_and_recommend(self):
        # GET /health
        res_h = self.client.get("/health")
        self.assertEqual(res_h.status_code, 200)
        self.assertIn("status", res_h.json())

        # GET /api/authorities/recommend (exact section)
        res_auth1 = self.client.get("/api/authorities/recommend?section_number=63&law_id=3")
        self.assertEqual(res_auth1.status_code, 200)
        data1 = res_auth1.json()
        self.assertEqual(data1["source_status"], "verified")
        self.assertEqual(data1["total"], 1)
        self.assertEqual(data1["recommendations"][0]["citation"], "(2020) 7 SCC 1")
        # Validate Pydantic schema
        AuthorityRecommendationResponse(**data1)

        # GET /api/authorities/recommend (NOT IN SOURCE)
        res_auth2 = self.client.get("/api/authorities/recommend?law_id=17")
        self.assertEqual(res_auth2.status_code, 200)
        data2 = res_auth2.json()
        self.assertEqual(data2["source_status"], "NOT IN SOURCE")
        self.assertEqual(data2["total"], 0)
        AuthorityRecommendationResponse(**data2)

        # GET /api/authorities/recommend (query)
        res_auth3 = self.client.get("/api/authorities/recommend?q=mandatory+fir")
        self.assertEqual(res_auth3.status_code, 200)
        data3 = res_auth3.json()
        self.assertEqual(data3["source_status"], "verified")
        self.assertEqual(data3["recommendations"][0]["citation"], "(2014) 2 SCC 1")

    def test_existing_endpoints_with_mock_db(self):
        """Ensures /api/laws, /api/sections, /api/search return 200 and maintain backward compatibility."""
        app.dependency_overrides[get_db] = mock_get_db
        try:
            # GET /api/laws
            res_laws = self.client.get("/api/laws")
            self.assertEqual(res_laws.status_code, 200)

            # GET /api/sections
            res_secs = self.client.get("/api/sections")
            self.assertEqual(res_secs.status_code, 200)

            # GET /api/search
            res_search = self.client.get("/api/search?q=murder")
            self.assertEqual(res_search.status_code, 200)
            s_data = res_search.json()
            self.assertIn("results", s_data)
        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
