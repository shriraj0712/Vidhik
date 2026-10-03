"""
Vidhik Platform - Phase 9 Legal RAG Test Suite
==============================================
Validates:
1. Reused Search Infrastructure integration (LegalSearchService.retrieve_ranked_candidates)
2. Successful retrieval and LLM generation
3. No-results / zero database matches handling (no hallucination)
4. Multilingual query understanding and lexicon expansion
5. LLM success state (is_grounded=True, grounded_high/medium)
6. LLM failure state (is_grounded=False, synthesis_failed, citations preserved, no error leak)
7. Offline deterministic mock provider behavior
8. Source & citation coordinate preservation
9. Context truncation with statutory disclaimers
10. FastAPI API endpoints (/api/rag/query, /api/rag/health) and validation
11. Backward compatibility for existing endpoints (/health, /api/laws, /api/sections, /api/search)
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.schemas.rag import (
    RAGQueryRequest,
    RAGResponse,
    LegalSourceCitation,
    RetrievedSectionContext
)
from app.services.context_builder import LegalContextBuilder
from app.services.llm_provider import (
    BaseLLMProvider,
    OfflineMockLLMProvider,
    GeminiLLMProvider,
    get_llm_provider
)
from app.services.rag_service import LegalRAGService
from app.services.query_service import LegalQueryService


class MockSuccessLLMProvider(BaseLLMProvider):
    """Predictable mock provider for successful synthesis tests."""
    @property
    def provider_name(self) -> str:
        return "test_success_provider"

    def generate(self, prompt: str, system_instruction: str, temperature: float = 0.1, max_output_tokens: int = 1500) -> str:
        return (
            "Under Section 73 of the Indian Contract Act, 1872, the party suffering from a breach of contract "
            "is entitled to receive compensation for any loss or damage naturally arising from such breach."
        )


class MockFailingLLMProvider(BaseLLMProvider):
    """Predictable mock provider for testing LLM failure states."""
    @property
    def provider_name(self) -> str:
        return "test_failing_provider"

    def generate(self, prompt: str, system_instruction: str, temperature: float = 0.1, max_output_tokens: int = 1500) -> str:
        raise RuntimeError("CRITICAL_INTERNAL_MODEL_PROVIDER_TIMEOUT_503")


# ==============================================================================
# 1. CONTEXT BUILDER & TRUNCATION TESTS
# ==============================================================================

def test_context_builder_deduplication():
    """Asserts that duplicate provisions with identical (law_id, section_number) are deduplicated."""
    raw_candidates = [
        {
            "law_id": 1,
            "law_name": "The Indian Contract Act, 1872",
            "section_id": 101,
            "section_number": "73",
            "section_title": "Compensation for loss or damage caused by breach of contract",
            "full_text": "When a contract has been broken, the party who suffers by such breach is entitled to receive compensation.",
            "source_pdf": "A1872-09.pdf",
            "source_page_start": 25,
            "source_page_end": 26,
            "jurisdiction": "Central",
            "_rank_explanation": "exact_phrase_title('breach of contract')"
        },
        # Duplicate occurrence of Section 73
        {
            "law_id": 1,
            "law_name": "The Indian Contract Act, 1872",
            "section_id": 102,
            "section_number": "73",
            "section_title": "Compensation for loss or damage caused by breach of contract (Duplicate entry)",
            "full_text": "Duplicate text from footnote reference.",
            "source_pdf": "A1872-09.pdf",
            "source_page_start": 27,
            "source_page_end": 27,
            "jurisdiction": "Central",
            "_rank_explanation": "full_text_phrase_match"
        },
        # Distinct provision (Section 74)
        {
            "law_id": 1,
            "law_name": "The Indian Contract Act, 1872",
            "section_id": 103,
            "section_number": "74",
            "section_title": "Compensation for breach of contract where penalty stipulated for",
            "full_text": "When a contract has been broken, if a sum is named in the contract as the amount to be paid in case of such breach...",
            "source_pdf": "A1872-09.pdf",
            "source_page_start": 27,
            "source_page_end": 28,
            "jurisdiction": "Central",
            "_rank_explanation": "exact_phrase_title('breach of contract')"
        }
    ]

    retrieved, citations, prompt_text = LegalContextBuilder.build_context(
        ranked_candidates=raw_candidates,
        max_sections=5
    )

    # Must only retain 2 unique provisions (Section 73 and Section 74)
    assert len(retrieved) == 2
    assert len(citations) == 2
    assert retrieved[0].section_number == "73"
    assert retrieved[1].section_number == "74"
    assert retrieved[0].relevance_rank == 1
    assert retrieved[1].relevance_rank == 2

    # Verify source citations preserved
    assert citations[0].source_pdf == "A1872-09.pdf"
    assert citations[0].source_page_start == 25
    assert citations[0].source_page_end == 26
    assert citations[0].law_name == "The Indian Contract Act, 1872"

    # Verify prompt context formatting
    assert "[STATUTORY PROVISION #1]" in prompt_text
    assert "Section: Section 73 — Compensation for loss or damage" in prompt_text
    assert "[STATUTORY PROVISION #2]" in prompt_text


def test_context_builder_truncation_disclaimer():
    """Asserts that provisions exceeding character limits are explicitly marked as truncated."""
    huge_text = "Statutory section text content for testing truncation behavior. " * 200  # ~12,800 chars
    candidates = [
        {
            "law_id": 2,
            "law_name": "Maharashtra Co-operative Societies Act, 1960",
            "section_id": 501,
            "section_number": "73",
            "section_title": "Committee, its powers and functions",
            "full_text": huge_text,
            "source_pdf": "M1960-24.pdf",
            "source_page_start": 48,
            "source_page_end": 60,
            "jurisdiction": "Maharashtra"
        }
    ]

    retrieved, citations, prompt_text = LegalContextBuilder.build_context(
        ranked_candidates=candidates,
        max_sections=1,
        max_context_chars=10000
    )

    assert len(retrieved) == 1
    assert retrieved[0].is_truncated is True
    # Statutory warning notice present in section text
    assert "[NOTICE: This provision is lengthy and has been excerpted to preserve context budget." in retrieved[0].section_text
    assert "Do not interpret this excerpt as the exhaustive statutory provision." in retrieved[0].section_text
    # Prompt context contains explicit truncation banner and status line
    assert "(EXCERPTED)" in prompt_text
    assert "[EXCERPTED PROVISION - DO NOT ASSUME EXHAUSTIVE]" in prompt_text


# ==============================================================================
# 2. OFFLINE MOCK LLM PROVIDER TESTS
# ==============================================================================

def test_offline_mock_llm_provider():
    """Asserts that OfflineMockLLMProvider acts as a deterministic fallback and does not claim neural reasoning."""
    provider = OfflineMockLLMProvider()
    assert provider.provider_name == "offline_deterministic_fallback"

    # With statutory context
    prompt_with_context = (
        "LEGAL QUESTION:\nWhat is breach of contract?\n\n"
        "=== RETRIEVED STATUTORY PROVISIONS ===\n"
        "[STATUTORY PROVISION #1]\n"
        "Act: Indian Contract Act\n"
        "Section: Section 73\n"
        "Text: When a contract has been broken..."
    )
    ans = provider.generate(prompt=prompt_with_context, system_instruction="test")
    assert "[DETERMINISTIC FALLBACK SYNTHESIS - TEST/OFFLINE MODE]" in ans
    assert "Indian Contract Act" in ans
    assert "Section 73" in ans
    assert "offline deterministic synthesis fallback engine" in ans

    # Without statutory context
    empty_prompt = "LEGAL QUESTION:\nWhat is breach of contract?\n\n=== RETRIEVED STATUTORY PROVISIONS ===\n"
    no_ctx_ans = provider.generate(prompt=empty_prompt, system_instruction="test")
    assert "Insufficient statutory context" in no_ctx_ans


def test_provider_factory_fallback():
    """Asserts that get_llm_provider defaults to offline deterministic provider when API keys are absent."""
    with patch.dict("os.environ", {"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": "", "LLM_API_KEY": ""}):
        provider = get_llm_provider()
        assert isinstance(provider, OfflineMockLLMProvider)
        assert provider.provider_name == "offline_deterministic_fallback"


# ==============================================================================
# 3. RAG SERVICE REUSED SEARCH & GROUNDING TESTS
# ==============================================================================

def test_rag_service_successful_retrieval_and_llm_success():
    """Asserts successful retrieval reusing search infrastructure and grounded LLM answer."""
    mock_cursor = MagicMock()

    # Mock LegalQueryService lexicon fetch
    mock_cursor.fetchall.side_effect = [
        # 1. Lexicon query
        [
            {
                "lexicon_id": 1,
                "term_id": "breach-of-contract",
                "category": "contract_and_commercial",
                "term_en": "Breach of contract",
                "term_mr": "करारभंग",
                "term_hi": "संविदा भंग",
                "grammatical_type": "noun_phrase",
                "context_usage": "Failure to perform contractual obligation",
                "official_source": "Ministry of Law and Justice",
                "verification_status": "verified_authoritative",
                "aliases_mr": ["करार मोडणे"],
                "aliases_hi": ["अनुबंध भंग"]
            }
        ],
        # 2. Candidate rows query
        [
            {
                "section_id": 101,
                "law_id": 1,
                "law_name": "The Indian Contract Act, 1872",
                "short_name": "Contract Act",
                "section_number": "73",
                "section_title": "Compensation for loss or damage caused by breach of contract",
                "description": "Compensation for breach",
                "full_text": "When a contract has been broken, the party who suffers by such breach is entitled to receive compensation.",
                "section_uid": "indian-contract-act-1872-sec-73",
                "jurisdiction": "Central",
                "source_pdf": "A1872-09.pdf",
                "source_page_start": 25,
                "source_page_end": 26,
                "manual_review_required": False
            }
        ]
    ]
    mock_cursor.fetchone.return_value = {"total": 1}

    req = RAGQueryRequest(query="What is the compensation for breach of contract?", language="en")
    mock_provider = MockSuccessLLMProvider()

    response = LegalRAGService.query(
        db=mock_cursor,
        request=req,
        provider=mock_provider
    )

    assert response.is_grounded is True
    assert response.confidence == "grounded_high"
    assert "Section 73 of the Indian Contract Act, 1872" in response.answer
    assert len(response.sources) == 1
    assert response.sources[0].law_name == "The Indian Contract Act, 1872"
    assert response.sources[0].section_number == "73"
    assert response.sources[0].source_pdf == "A1872-09.pdf"
    assert response.retrieval_metadata.total_candidates_found == 1
    assert response.retrieval_metadata.sections_used == 1
    assert "breach-of-contract" in response.retrieval_metadata.query_terms_matched


def test_rag_service_llm_failure_state():
    """
    CRITICAL TEST: When LLM provider fails, asserts that:
    1. is_grounded is FALSE (must NOT falsely claim AI synthesis succeeded).
    2. confidence is 'synthesis_failed'.
    3. Retrieved sources and section context are preserved and returned.
    4. Internal technical exception details are NOT exposed to the user.
    """
    mock_cursor = MagicMock()

    mock_cursor.fetchall.side_effect = [
        # 1. Lexicon query
        [],
        # 2. Candidate rows query
        [
            {
                "section_id": 101,
                "law_id": 1,
                "law_name": "The Indian Contract Act, 1872",
                "short_name": "Contract Act",
                "section_number": "73",
                "section_title": "Compensation for loss or damage caused by breach of contract",
                "description": "Compensation for breach",
                "full_text": "When a contract has been broken, the party who suffers by such breach is entitled to receive compensation.",
                "section_uid": "indian-contract-act-1872-sec-73",
                "jurisdiction": "Central",
                "source_pdf": "A1872-09.pdf",
                "source_page_start": 25,
                "source_page_end": 26,
                "manual_review_required": False
            }
        ]
    ]
    mock_cursor.fetchone.return_value = {"total": 1}

    req = RAGQueryRequest(query="breach of contract penalty", language="en")
    failing_provider = MockFailingLLMProvider()

    response = LegalRAGService.query(
        db=mock_cursor,
        request=req,
        provider=failing_provider
    )

    # 1. Verification of grounded and confidence state
    assert response.is_grounded is False
    assert response.confidence == "synthesis_failed"

    # 2. Retrieved sources and sections MUST be preserved
    assert len(response.sources) == 1
    assert response.sources[0].section_number == "73"
    assert response.sources[0].law_name == "The Indian Contract Act, 1872"
    assert len(response.retrieved_sections) == 1
    assert response.retrieval_metadata.total_candidates_found == 1

    # 3. User answer must be safe and generic; zero leak of internal exception details
    assert "CRITICAL_INTERNAL_MODEL_PROVIDER_TIMEOUT_503" not in response.answer
    assert "automated AI synthesis could not be completed at this time" in response.answer
    assert "authoritative statutory provisions and official citations are provided below" in response.answer


def test_rag_service_zero_database_results():
    """Asserts that RAG service returns structured no_context response without hallucinations."""
    mock_cursor = MagicMock()

    # 1. Lexicon query returns empty
    mock_cursor.fetchall.return_value = []
    # 2. Count query returns 0
    mock_cursor.fetchone.return_value = {"total": 0}

    req = RAGQueryRequest(query="Non-existent provision 999XYZABC", language="en")
    response = LegalRAGService.query(db=mock_cursor, request=req)

    assert response.is_grounded is False
    assert response.confidence == "no_context"
    assert "No relevant statutory provisions were found in the Vidhik legal database" in response.answer
    assert len(response.sources) == 0
    assert len(response.retrieved_sections) == 0
    assert response.retrieval_metadata.total_candidates_found == 0


def test_rag_service_multilingual_marathi_query():
    """Asserts that queries in Marathi trigger multilingual terminology expansion in search."""
    mock_cursor = MagicMock()

    mock_cursor.fetchall.side_effect = [
        # Lexicon includes Marathi legal term
        [
            {
                "lexicon_id": 1,
                "term_id": "breach-of-contract",
                "category": "contract_and_commercial",
                "term_en": "Breach of contract",
                "term_mr": "करारभंग",
                "term_hi": "संविदा भंग",
                "grammatical_type": "noun_phrase",
                "context_usage": "Failure to perform contractual obligation",
                "official_source": "Ministry of Law and Justice",
                "verification_status": "verified_authoritative",
                "aliases_mr": ["करार मोडणे"],
                "aliases_hi": []
            }
        ],
        # Candidates
        [
            {
                "section_id": 101,
                "law_id": 1,
                "law_name": "The Indian Contract Act, 1872",
                "short_name": "Contract Act",
                "section_number": "73",
                "section_title": "Compensation for loss or damage caused by breach of contract",
                "description": "Compensation for breach",
                "full_text": "When a contract has been broken, the party who suffers by such breach is entitled to receive compensation.",
                "section_uid": "indian-contract-act-1872-sec-73",
                "jurisdiction": "Central",
                "source_pdf": "A1872-09.pdf",
                "source_page_start": 25,
                "source_page_end": 26,
                "manual_review_required": False
            }
        ]
    ]
    mock_cursor.fetchone.return_value = {"total": 1}

    req = RAGQueryRequest(query="करारभंग झाल्यास काय नुकसानभरपाई मिळते?", language="mr")
    response = LegalRAGService.query(db=mock_cursor, request=req, provider=MockSuccessLLMProvider())

    assert response.language == "mr"
    assert response.is_grounded is True
    assert "breach-of-contract" in response.retrieval_metadata.query_terms_matched
    assert len(response.sources) == 1
    assert response.sources[0].section_number == "73"


def test_source_citation_preservation():
    """Asserts full preservation of primary source coordinates and metadata."""
    cand = {
        "law_id": 5,
        "law_name": "The Code of Civil Procedure, 1908",
        "section_id": 205,
        "section_number": "9",
        "section_title": "Courts to try all civil suits unless barred",
        "full_text": "The Courts shall have jurisdiction to try all suits of a civil nature...",
        "section_uid": "cpc-1908-sec-9",
        "source_pdf": "A1908-05.pdf",
        "source_page_start": 12,
        "source_page_end": 14,
        "jurisdiction": "Central"
    }

    retrieved, citations, _ = LegalContextBuilder.build_context([cand], max_sections=1)

    assert len(citations) == 1
    cit = citations[0]
    assert cit.law_id == 5
    assert cit.law_name == "The Code of Civil Procedure, 1908"
    assert cit.section_number == "9"
    assert cit.section_title == "Courts to try all civil suits unless barred"
    assert cit.section_uid == "cpc-1908-sec-9"
    assert cit.source_pdf == "A1908-05.pdf"
    assert cit.source_page_start == 12
    assert cit.source_page_end == 14
    assert cit.jurisdiction == "Central"


# ==============================================================================
# 4. FASTAPI ENDPOINT INTEGRATION TESTS
# ==============================================================================

def test_api_rag_query_endpoint_success():
    """Asserts that POST /api/rag/query returns 200 with schema compliance."""
    client = TestClient(app)

    mock_db = MagicMock()
    mock_db.fetchall.side_effect = [
        # Lexicon query
        [],
        # Candidate sections
        [
            {
                "section_id": 55,
                "law_id": 10,
                "law_name": "The Transfer of Property Act, 1882",
                "short_name": "TP Act",
                "section_number": "54",
                "section_title": "Sale defined",
                "description": "Definition of sale of immovable property",
                "full_text": "Sale is a transfer of ownership in exchange for a price paid or promised or part-paid and part-promised.",
                "section_uid": "transfer-of-property-act-1882-sec-54",
                "jurisdiction": "Central",
                "source_pdf": "A1882-04.pdf",
                "source_page_start": 14,
                "source_page_end": 15,
                "manual_review_required": False
            }
        ]
    ]
    mock_db.fetchone.return_value = {"total": 1}

    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.post(
            "/api/rag/query",
            json={
                "query": "How is sale defined under transfer of property?",
                "language": "en"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "How is sale defined under transfer of property?"
        assert data["is_grounded"] is True
        assert len(data["sources"]) == 1
        assert data["sources"][0]["section_number"] == "54"
        assert data["sources"][0]["law_name"] == "The Transfer of Property Act, 1882"
        assert "Sale is a transfer of ownership" in data["retrieved_sections"][0]["section_text"]
        assert "Vidhik legal database" in data["disclaimer"]

    finally:
        app.dependency_overrides.clear()


def test_api_rag_query_empty_validation():
    """Asserts that empty or whitespace query returns 422 Unprocessable Entity."""
    client = TestClient(app)
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.post("/api/rag/query", json={"query": "   "})
        assert response.status_code in (422, 400)
    finally:
        app.dependency_overrides.clear()


def test_api_rag_health_endpoint():
    """Asserts that GET /api/rag/health returns operational status and provider metadata."""
    client = TestClient(app)
    response = client.get("/api/rag/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "llm_provider" in data
    assert data["grounding_enforced"] is True


def test_backward_compatibility_endpoints():
    """Asserts that existing API endpoints (/health, /, /api/laws, /api/sections, /api/search) are completely operational."""
    client = TestClient(app)

    mock_db = MagicMock()
    # Universal fetchone returning keys expected by any endpoint
    mock_db.fetchone.return_value = {
        "total": 1,
        "ping": 1,
        "db_name": "vidhik_db",
        "version": "PostgreSQL 18.1"
    }
    last_sql = {"query": ""}

    def fake_execute(query, params=None):
        last_sql["query"] = str(query)

    def fake_fetchall():
        if "legal_lexicon" in last_sql["query"]:
            return []
        return [
            {
                "law_id": 1,
                "law_name": "The Indian Contract Act, 1872",
                "law_slug": "indian-contract-act-1872",
                "short_name": "Contract Act",
                "year": 1872,
                "law_type": "Central",
                "jurisdiction": "Central",
                "total_sections_extracted": 266,
                "is_diglot": False,
                "section_id": 101,
                "section_number": "73",
                "section_title": "Compensation for loss or damage caused by breach of contract",
                "section_uid": "indian-contract-act-1872-sec-73",
                "section_text": "When a contract has been broken...",
                "full_text": "When a contract has been broken...",
                "description": "Compensation for breach",
                "chapter_number": "VI",
                "chapter_title": "Of the Consequences of Breach of Contract",
                "source_pdf": "A1872-09.pdf",
                "source_page_start": 25,
                "source_page_end": 26,
                "page_start": 25,
                "page_end": 26,
                "manual_review_required": False,
                "is_omitted": False
            }
        ]

    mock_db.execute.side_effect = fake_execute
    mock_db.fetchall.side_effect = fake_fetchall

    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.routers.health.check_db_connection", return_value={"status": "connected", "database": "vidhik_db", "version": "PostgreSQL 18.1"}):
        try:
            # 1. Health
            res = client.get("/health")
            assert res.status_code == 200
            assert res.json()["status"] == "healthy"

            # 2. Root SPA / Application Entry Point
            res_root = client.get("/")
            assert res_root.status_code == 200
            assert "text/html" in res_root.headers.get("content-type", "")
            assert "<!DOCTYPE html>" in res_root.text or "<html" in res_root.text

            # 3. Laws
            res_laws = client.get("/api/laws?limit=1")
            assert res_laws.status_code == 200
            assert res_laws.json()["total"] == 1

            # 4. Sections
            res_secs = client.get("/api/sections?limit=1")
            assert res_secs.status_code == 200
            assert res_secs.json()["total"] == 1

            # 5. Search
            res_search = client.get("/api/search?q=contract&limit=1")
            assert res_search.status_code == 200
            assert res_search.json()["query"] == "contract"

        finally:
            app.dependency_overrides.clear()
