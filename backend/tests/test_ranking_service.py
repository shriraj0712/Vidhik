"""
Vidhik Platform - Phase 8 Deterministic Legal Ranking Test Suite
================================================================
Comprehensive test cases validating all Phase 8 ranking behaviors:
1. Exact match ranks above weaker match
2. Normalized match
3. Phrase match
4. Multilingual match
5. Context/concept match
6. Title match versus section-body match
7. Law/section number matching
8. Deterministic tie-breaking
9. Empty result set
10. Multiple candidate results
11. Existing /api/search schema & response behavior
12. Existing LegalQueryService utility & confidence behavior
"""

import unittest
from typing import List, Dict, Any

from app.schemas.query import (
    LegalQueryAnalysis,
    MatchedTerm,
    MatchedConcept,
    MatchedSynonym
)
from app.schemas.search import SearchResultItem, SearchResponse
from app.services.ranking_service import LegalRankingService, RANKING_WEIGHTS
from app.services.query_service import LegalQueryService, CONFIDENCE_PRIORITY


class TestDeterministicLegalRanking(unittest.TestCase):
    """
    Test suite for deterministic legal search ranking.
    """

    def setUp(self):
        """Set up standard sample candidates and base configurations."""
        self.ranking = LegalRankingService

    def test_01_exact_match_ranks_above_weaker_match(self):
        """1. Exact match ranks above weaker match (normalized, phrase, partial, body)."""
        query = "indemnity"
        analysis = LegalQueryAnalysis(
            original_query=query,
            normalized_query=query,
            matched_terms=[
                MatchedTerm(
                    term_id="indemnity",
                    term_en="Indemnity",
                    confidence="exact",
                    match_types=["exact_term('Indemnity')"]
                )
            ]
        )

        candidates = [
            {
                "section_id": 1,
                "law_id": 10,
                "law_name": "General Law",
                "section_number": "10",
                "section_title": "Miscellaneous provisions mentioning indemnity in case of loss",
                "full_text": "provisions regarding indemnity",
            },
            {
                "section_id": 2,
                "law_id": 10,
                "law_name": "General Law",
                "section_number": "11",
                "section_title": "Indemnity",  # Exact title match
                "full_text": "Definition of indemnity",
            },
            {
                "section_id": 3,
                "law_id": 10,
                "law_name": "General Law",
                "section_number": "12",
                "section_title": "Special Liabilities",
                "full_text": "The party shall provide indemnity against damage.",  # Body match only
            }
        ]

        ranked = self.ranking.rank_candidates(candidates, query, analysis)

        # Candidate 2 (exact term on section title) must rank 1st
        self.assertEqual(ranked[0]["section_id"], 2)
        self.assertIn("exact_legal_term_section_title", ranked[0]["rank_reason"])

        # Candidate 1 (phrase / tokens in title) must rank 2nd
        self.assertEqual(ranked[1]["section_id"], 1)

        # Candidate 3 (body only) must rank last
        self.assertEqual(ranked[2]["section_id"], 3)
        self.assertGreater(ranked[0]["rank_score"], ranked[1]["rank_score"])
        self.assertGreater(ranked[1]["rank_score"], ranked[2]["rank_score"])

    def test_02_normalized_match(self):
        """2. Normalized match handles hyphens, plural suffix, whitespace, and ranks above weaker matches."""
        query = "cooperative societies"
        analysis = LegalQueryAnalysis(
            original_query=query,
            normalized_query=query,
            matched_terms=[
                MatchedTerm(
                    term_id="cooperative_society",
                    term_en="Co-operative Society",
                    confidence="normalized",
                    match_types=["normalized_stem_term('Co-operative Society')"]
                )
            ]
        )

        candidates = [
            {
                "section_id": 101,
                "law_id": 5,
                "law_name": "Maharashtra Societies Act",
                "section_number": "3",
                "section_title": "Registration of Co-operative Societies.",  # Normalized term match on title
                "full_text": "Any society may register under this Act.",
            },
            {
                "section_id": 102,
                "law_id": 5,
                "law_name": "Maharashtra Societies Act",
                "section_number": "4",
                "section_title": "Powers of Registrar",
                "full_text": "The registrar oversees all cooperative societies in the state.",  # Body match only
            }
        ]

        ranked = self.ranking.rank_candidates(candidates, query, analysis)
        self.assertEqual(ranked[0]["section_id"], 101)
        self.assertIn("normalized", ranked[0]["rank_reason"])
        self.assertGreater(ranked[0]["rank_score"], ranked[1]["rank_score"])

    def test_03_phrase_match(self):
        """3. Whole phrase match on title ranks above token matches and body phrase matches."""
        query = "breach of contract"
        analysis = LegalQueryAnalysis(
            original_query=query,
            normalized_query=query,
            matched_terms=[
                MatchedTerm(
                    term_id="breach_of_contract",
                    term_en="Breach of contract",
                    confidence="phrase",
                    match_types=["whole_phrase_containment('Breach of contract')"]
                )
            ]
        )

        candidates = [
            {
                "section_id": 201,
                "law_id": 15,
                "law_name": "The Indian Contract Act, 1872",
                "section_number": "73",
                "section_title": "Compensation for loss or damage caused by breach of contract.",  # Phrase in title
                "full_text": "When a contract has been broken...",
            },
            {
                "section_id": 202,
                "law_id": 15,
                "law_name": "The Indian Contract Act, 1872",
                "section_number": "74",
                "section_title": "Compensation for failure to discharge obligations.",  # Body only
                "full_text": "In event of breach of contract, penalty may be claimed.",
            }
        ]

        ranked = self.ranking.rank_candidates(candidates, query, analysis)
        self.assertEqual(ranked[0]["section_id"], 201)
        self.assertIn("phrase", ranked[0]["rank_reason"])
        self.assertGreater(ranked[0]["rank_score"], ranked[1]["rank_score"])

    def test_04_multilingual_match(self):
        """4. Multilingual Devanagari match ranks appropriately above context/concept and body matches."""
        query = "करार"  # Marathi for contract
        analysis = LegalQueryAnalysis(
            original_query=query,
            normalized_query=query,
            matched_terms=[
                MatchedTerm(
                    term_id="contract",
                    term_en="Contract",
                    term_mr="करार",
                    confidence="multilingual",
                    match_types=["multilingual_exact(mr:'करार')"]
                )
            ]
        )

        candidates = [
            {
                "section_id": 301,
                "law_id": 25,
                "law_name": "भारतीय करार कायदा",
                "section_number": "1",
                "section_title": "संक्षिप्त नाव आणि व्याप्ती",
                "full_text": "हा करार कायदा म्हणून ओळखला जाईल.",  # Multilingual term in text
            },
            {
                "section_id": 302,
                "law_id": 25,
                "law_name": "भारतीय करार कायदा",  # Multilingual term in law title
                "section_number": "2",
                "section_title": "व्याख्या",
                "full_text": "प्रस्तावाची व्याख्या.",
            },
            {
                "section_id": 303,
                "law_id": 26,
                "law_name": "दुसरा कायदा",
                "section_number": "5",
                "section_title": "इतर बाबी",
                "full_text": "सामान्य नियम.",  # Generic fallback
            }
        ]

        ranked = self.ranking.rank_candidates(candidates, query, analysis)
        # Law title multilingual match > body multilingual match > generic fallback
        self.assertEqual(ranked[0]["section_id"], 302)
        self.assertEqual(ranked[1]["section_id"], 301)
        self.assertEqual(ranked[2]["section_id"], 303)
        self.assertGreater(ranked[0]["rank_score"], ranked[1]["rank_score"])
        self.assertGreater(ranked[1]["rank_score"], ranked[2]["rank_score"])

    def test_05_context_and_concept_match(self):
        """5. Context match ranks above category concept match, following the strict hierarchy."""
        query = "dispute arbitration"
        analysis = LegalQueryAnalysis(
            original_query=query,
            normalized_query=query,
            matched_terms=[
                MatchedTerm(
                    term_id="arbitration_agreement",
                    term_en="Arbitration Agreement",
                    confidence="context",
                    match_types=["context_phrase_match(dispute,arbitration)"]
                )
            ],
            matched_concepts=[
                MatchedConcept(
                    category="dispute_resolution",
                    matched_terms=["arbitration_agreement"]
                )
            ]
        )

        candidates = [
            {
                "section_id": 401,
                "law_id": 30,
                "law_name": "Commercial Courts Act",
                "section_number": "12",
                "section_title": "Settlement of disputes through arbitration agreement",
                "full_text": "Referral of dispute.",
            },
            {
                "section_id": 402,
                "law_id": 30,
                "law_name": "Commercial Courts Act",
                "section_number": "15",
                "section_title": "Dispute Resolution mechanism",
                "full_text": "Categorized under dispute resolution.",
            }
        ]

        ranked = self.ranking.rank_candidates(candidates, query, analysis)
        # Section 401 has context term in title, section 402 has concept domain
        self.assertEqual(ranked[0]["section_id"], 401)
        self.assertIn("context", ranked[0]["rank_reason"])
        self.assertGreater(ranked[0]["rank_score"], ranked[1]["rank_score"])

    def test_06_title_match_versus_section_body_match(self):
        """6. Title match ranks strictly higher than section-body match."""
        query = "injunction"
        candidates = [
            {
                "section_id": 501,
                "law_id": 40,
                "law_name": "Specific Relief Act",
                "section_number": "38",
                "section_title": "Perpetual Injunction when granted.",  # Section Title match
                "full_text": "Subject to other provisions...",
            },
            {
                "section_id": 502,
                "law_id": 40,
                "law_name": "Specific Relief Act",
                "section_number": "5",
                "section_title": "Recovery of specific immovable property",
                "full_text": "A plaintiff may apply for an injunction to restrain trespass.",  # Body match only
            }
        ]

        ranked = self.ranking.rank_candidates(candidates, query, None)
        self.assertEqual(ranked[0]["section_id"], 501)
        self.assertGreater(ranked[0]["rank_score"], ranked[1]["rank_score"])

    def test_07_law_and_section_number_matching(self):
        """7. Law/Section number matching takes top deterministic tier when query targets section number."""
        query = "155"
        candidates = [
            {
                "section_id": 601,
                "law_id": 50,
                "law_name": "Code of Criminal Procedure, 1973",
                "section_number": "155",  # Exact section number match
                "section_title": "Information as to non-cognizable cases and investigation of such cases.",
                "full_text": "When information is given to an officer...",
            },
            {
                "section_id": 602,
                "law_id": 50,
                "law_name": "Code of Criminal Procedure, 1973",
                "section_number": "156",
                "section_title": "Police officer's power to investigate cognizable case.",
                "full_text": "Subject to section 155, any officer in charge...",  # Body mentions 155
            }
        ]

        ranked = self.ranking.rank_candidates(candidates, query, None)
        self.assertEqual(ranked[0]["section_id"], 601)
        self.assertEqual(ranked[0]["_rank_tier"], 1)
        self.assertIn("exact_section_number_match", ranked[0]["rank_reason"])
        self.assertGreater(ranked[0]["rank_score"], 999.0)

        # Also test with prefix "Section 155"
        ranked_prefix = self.ranking.rank_candidates(candidates, "Section 155", None)
        self.assertEqual(ranked_prefix[0]["section_id"], 601)
        self.assertEqual(ranked_prefix[0]["_rank_tier"], 1)

    def test_08_deterministic_tie_breaking(self):
        """8. Deterministic tie-breaking orders equal scores stably by law_id ASC, then section_id ASC."""
        query = "powers"
        # Two identical candidates in terms of textual match features but different IDs
        candidates = [
            {
                "section_id": 999,
                "law_id": 20,
                "law_name": "Act B",
                "section_number": "5",
                "section_title": "Powers of State Government.",
                "full_text": "The government has powers.",
            },
            {
                "section_id": 100,
                "law_id": 20,
                "law_name": "Act B",
                "section_number": "4",
                "section_title": "Powers of State Government.",
                "full_text": "The government has powers.",
            },
            {
                "section_id": 500,
                "law_id": 10,
                "law_name": "Act A",
                "section_number": "1",
                "section_title": "Powers of State Government.",
                "full_text": "The government has powers.",
            }
        ]

        # Candidate scores are identical because their titles and bodies match identically
        ranked_first_pass = self.ranking.rank_candidates(candidates, query, None)

        # Expected stable ordering:
        # 1st: law_id 10, section_id 500 (lower law_id)
        # 2nd: law_id 20, section_id 100 (same law_id, lower section_id)
        # 3rd: law_id 20, section_id 999 (same law_id, higher section_id)
        self.assertEqual([c["section_id"] for c in ranked_first_pass], [500, 100, 999])

        # Run 50 times to guarantee 100% deterministic stability
        for _ in range(50):
            ranked_repeat = self.ranking.rank_candidates(candidates, query, None)
            self.assertEqual([c["section_id"] for c in ranked_repeat], [500, 100, 999])

    def test_09_empty_result_set(self):
        """9. Handles empty candidate results cleanly."""
        ranked = self.ranking.rank_candidates([], "test query", None)
        self.assertEqual(ranked, [])

    def test_10_multiple_candidate_results(self):
        """10. Correctly evaluates and sorts a large candidate pool across all priority tiers."""
        query = "pledge"
        analysis = LegalQueryAnalysis(
            original_query=query,
            normalized_query=query,
            matched_terms=[
                MatchedTerm(
                    term_id="pledge",
                    term_en="Pledge",
                    confidence="exact"
                )
            ]
        )

        candidates = [
            {"section_id": 1, "law_id": 1, "section_number": "1", "section_title": "General Preamble", "full_text": "text without keyword"},
            {"section_id": 2, "law_id": 1, "section_number": "172", "section_title": "Pledge defined.", "full_text": "Pledge is bailment of goods"},
            {"section_id": 3, "law_id": 1, "section_number": "173", "section_title": "Pawnee's rights", "full_text": "The pawnee may retain goods for pledge"},
            {"section_id": 4, "law_id": 2, "section_number": "5", "section_title": "The Indian Pledge Act", "full_text": "Special rules for pledge"},
            {"section_id": 5, "law_id": 3, "section_number": "10", "section_title": "Pledge", "full_text": "Direct statutory heading for pledge"},
        ]

        ranked = self.ranking.rank_candidates(candidates, query, analysis)
        self.assertEqual(len(ranked), 5)

        # All scores must be monotonically non-increasing
        for i in range(len(ranked) - 1):
            self.assertGreaterEqual(ranked[i]["rank_score"], ranked[i + 1]["rank_score"])

    def test_11_search_schema_backward_compatibility(self):
        """11. Verifies SearchResultItem and SearchResponse schema serialization with ranking fields."""
        item = SearchResultItem(
            law_id=1,
            law_name="The Indian Contract Act, 1872",
            section_id=10,
            section_number="2",
            section_title="Interpretation-clause.",
            snippet="... an agreement enforceable by law is a contract ...",
            jurisdiction="Central",
            rank_score=882.5,
            rank_reason="exact_legal_term_section_title('Contract')"
        )
        self.assertEqual(item.rank_score, 882.5)
        self.assertEqual(item.rank_reason, "exact_legal_term_section_title('Contract')")

        response = SearchResponse(
            query="contract",
            total=1,
            limit=10,
            offset=0,
            results=[item]
        )
        json_dict = response.model_dump()
        self.assertEqual(json_dict["total"], 1)
        self.assertEqual(len(json_dict["results"]), 1)
        self.assertEqual(json_dict["results"][0]["section_id"], 10)
        self.assertEqual(json_dict["results"][0]["rank_score"], 882.5)

    def test_12_legal_query_service_behavior(self):
        """12. Verifies LegalQueryService normalization, stemming, canonicalization, and confidence ordering."""
        # 1. Normalization
        self.assertEqual(LegalQueryService.normalize("   co-operative    societies   "), "co-operative societies")

        # 2. Tokenization & stemmer
        tokens = LegalQueryService.clean_tokens("contractual obligations under co-operative societies")
        self.assertIn("contractual", tokens)
        self.assertEqual(LegalQueryService.stem_token("contractual"), "contract")
        self.assertEqual(LegalQueryService.stem_token("societies"), "society")
        self.assertEqual(LegalQueryService.stem_token("contracts"), "contract")
        self.assertEqual(LegalQueryService.stem_token("provisions"), "provision")

        # 3. Canonicalization
        self.assertEqual(LegalQueryService.canonicalize("Co-operative Societies, 1960!"), "cooperativesocieties1960")

        # 4. Confidence priority hierarchy preserves Phase 1-7 design
        self.assertLess(CONFIDENCE_PRIORITY["exact"], CONFIDENCE_PRIORITY["normalized"])
        self.assertLess(CONFIDENCE_PRIORITY["normalized"], CONFIDENCE_PRIORITY["phrase"])
        self.assertLess(CONFIDENCE_PRIORITY["phrase"], CONFIDENCE_PRIORITY["multilingual"])
        self.assertLess(CONFIDENCE_PRIORITY["multilingual"], CONFIDENCE_PRIORITY["context"])
        self.assertLess(CONFIDENCE_PRIORITY["context"], CONFIDENCE_PRIORITY["concept"])


if __name__ == "__main__":
    unittest.main()
