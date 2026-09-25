"""
Vidhik Platform - Phase 8 Lightweight Verification Script
========================================================
Performs lightweight, zero-hang verification of Phase 8:
1. LegalRankingService imports and weights definition
2. Deterministic ranking on 'contract', 'cooperative', and '155'
3. Tie-breaking guarantees
4. API schemas and backward compatibility
"""

import sys
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.schemas.query import LegalQueryAnalysis, MatchedTerm, MatchedConcept
from app.schemas.search import SearchResultItem, SearchResponse
from app.services.ranking_service import LegalRankingService, RANKING_WEIGHTS

print("=" * 60)
print("PHASE 8 TARGETED VERIFICATION RUNNER")
print("=" * 60)

# 1. Verification of Import and Weights
print("\n[CHECK 1] LegalRankingService Import & Configuration:")
print(f"  - Class: {LegalRankingService.__name__}")
print(f"  - Total defined centralized weights: {len(RANKING_WEIGHTS)}")
print("  - Sample weights:")
for k in ["SECTION_NUMBER_EXACT", "CONFIDENCE_EXACT_SECTION_TITLE", "CONFIDENCE_NORMALIZED_SECTION_TITLE", "CONFIDENCE_PHRASE_SECTION_TITLE"]:
    print(f"    * {k}: {RANKING_WEIGHTS[k]}")
assert len(RANKING_WEIGHTS) > 10, "Weights must be defined"
print("  => PASSED")

# 2. Verification of 'contract' query ranking
print("\n[CHECK 2] Verification of query 'contract':")
analysis_contract = LegalQueryAnalysis(
    original_query="contract",
    normalized_query="contract",
    matched_terms=[
        MatchedTerm(
            term_id="contract",
            term_en="Contract",
            confidence="exact",
            match_types=["exact_term('Contract')"]
        )
    ]
)
candidates_contract = [
    {
        "law_id": 14,
        "law_name": "The Air (Prevention and Control of Pollution) Act, 1981",
        "section_id": 566,
        "section_number": "5",
        "section_title": "Constitution of State Boards.",
        "full_text": "... of this Act, to acquire and dispose of property and to contract, and may by the said name sue or be sued.",
    },
    {
        "law_id": 15,
        "law_name": "The Indian Contract Act, 1872",
        "section_id": 600,
        "section_number": "1",
        "section_title": "Short title and extent.",
        "full_text": "This Act may be called the Indian Contract Act, 1872.",
    },
    {
        "law_id": 15,
        "law_name": "The Indian Contract Act, 1872",
        "section_id": 610,
        "section_number": "10",
        "section_title": "What agreements are contracts.",
        "full_text": "All agreements are contracts if they are made by the free consent of parties competent to contract...",
    }
]
ranked_contract = LegalRankingService.rank_candidates(candidates_contract, "contract", analysis_contract)
print("  Ranked results for 'contract':")
for idx, r in enumerate(ranked_contract, 1):
    print(f"    {idx}. Section {r['section_number']}: '{r['section_title']}' (Score: {r['rank_score']}, Reason: {r['rank_reason']})")

assert ranked_contract[0]["section_id"] == 600 or ranked_contract[0]["section_id"] == 610
assert ranked_contract[-1]["section_id"] == 566, "Air Pollution Act must rank lowest for contract"
print("  => PASSED")

# 3. Verification of 'cooperative' query ranking
print("\n[CHECK 3] Verification of query 'cooperative':")
analysis_coop = LegalQueryAnalysis(
    original_query="cooperative",
    normalized_query="cooperative",
    matched_terms=[
        MatchedTerm(
            term_id="cooperative_society",
            term_en="Co-operative Society",
            confidence="normalized",
            match_types=["normalized_stem_term('Co-operative Society')"]
        )
    ]
)
candidates_coop = [
    {
        "law_id": 50,
        "law_name": "Maharashtra Co-operative Societies Act, 1960",
        "section_id": 1050,
        "section_number": "4",
        "section_title": "Societies which may be registered.",
        "full_text": "A society which has as its objects the promotion of economic interests...",
    },
    {
        "law_id": 50,
        "law_name": "Maharashtra Co-operative Societies Act, 1960",
        "section_id": 1051,
        "section_number": "9",
        "section_title": "Registration of Co-operative Societies.",
        "full_text": "The Registrar may register the co-operative society...",
    },
    {
        "law_id": 100,
        "law_name": "General Land Revenue Code",
        "section_id": 2001,
        "section_number": "22",
        "section_title": "Disposal of intestate land.",
        "full_text": "Land may be transferred to any cooperative farming group.",
    }
]
ranked_coop = LegalRankingService.rank_candidates(candidates_coop, "cooperative", analysis_coop)
print("  Ranked results for 'cooperative':")
for idx, r in enumerate(ranked_coop, 1):
    print(f"    {idx}. Section {r['section_number']}: '{r['section_title']}' (Score: {r['rank_score']}, Reason: {r['rank_reason']})")

assert ranked_coop[0]["section_id"] == 1051, "Exact title match for Co-operative Societies must rank #1"
assert ranked_coop[-1]["section_id"] == 2001, "Land Revenue code body mention must rank last"
print("  => PASSED")

# 4. Verification of '155' query ranking (Exact section number match)
print("\n[CHECK 4] Verification of query '155':")
candidates_155 = [
    {
        "law_id": 1,
        "law_name": "Code of Criminal Procedure, 1973",
        "section_id": 3155,
        "section_number": "155",
        "section_title": "Information as to non-cognizable cases and investigation of such cases.",
        "full_text": "When information is given to an officer in charge of a police station...",
    },
    {
        "law_id": 1,
        "law_name": "Code of Criminal Procedure, 1973",
        "section_id": 3156,
        "section_number": "156",
        "section_title": "Police officer's power to investigate cognizable case.",
        "full_text": "Any officer in charge... subject to section 155...",
    }
]
ranked_155 = LegalRankingService.rank_candidates(candidates_155, "155", None)
print("  Ranked results for '155':")
for idx, r in enumerate(ranked_155, 1):
    print(f"    {idx}. Section {r['section_number']}: '{r['section_title']}' (Score: {r['rank_score']}, Reason: {r['rank_reason']})")

assert ranked_155[0]["section_id"] == 3155
assert ranked_155[0]["_rank_tier"] == 1
assert "exact_section_number_match" in ranked_155[0]["rank_reason"]
print("  => PASSED")

# 5. Verification of Deterministic Tie-Breaking
print("\n[CHECK 5] Verification of Deterministic Tie-Breaking:")
candidates_tie = [
    {"law_id": 20, "section_id": 50, "section_number": "1", "section_title": "Definitions", "full_text": "text"},
    {"law_id": 10, "section_id": 90, "section_number": "1", "section_title": "Definitions", "full_text": "text"},
    {"law_id": 10, "section_id": 20, "section_number": "1", "section_title": "Definitions", "full_text": "text"},
]
ranked_tie = LegalRankingService.rank_candidates(candidates_tie, "definitions", None)
tie_order = [(r["law_id"], r["section_id"]) for r in ranked_tie]
print(f"  Tie-break order (law_id, section_id): {tie_order}")
assert tie_order == [(10, 20), (10, 90), (20, 50)], f"Tie-break order unexpected: {tie_order}"
print("  => PASSED")

# 6. Verification of API Schemas Backward Compatibility
print("\n[CHECK 6] Verification of API Schemas Backward Compatibility:")
item = SearchResultItem(
    law_id=14,
    law_name="Air Act",
    section_id=566,
    section_number="5",
    section_title="State Boards",
    snippet="sample snippet",
    rank_score=100.5,
    rank_reason="full_text_phrase_match"
)
resp = SearchResponse(
    query="contract",
    total=1,
    limit=5,
    offset=0,
    results=[item]
)
dump = resp.model_dump()
assert "rank_score" in dump["results"][0]
assert "rank_reason" in dump["results"][0]
assert dump["results"][0]["rank_score"] == 100.5
print("  => PASSED")

print("\n" + "=" * 60)
print("ALL PHASE 8 TARGETED VERIFICATIONS PASSED SUCCESSFULLY!")
print("=" * 60)
