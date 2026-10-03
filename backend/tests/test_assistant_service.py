"""
Vidhik Platform - Phase 10 AI Legal Assistant Test Suite
=========================================================
Comprehensive tests validating:
1. Normal legal question processing and grounded response
2. Relevant legal context and source citation preservation
3. Zero database matches / no relevant context handling (zero hallucination)
4. Insufficient context handling
5. English legal question processing
6. Marathi multilingual question processing
7. Follow-up question resolution using prior conversation context
8. Conversation context management, turn bounds, and InMemoryConversationStore
9. LLM provider success state (grounded_high/medium, citations intact)
10. LLM provider failure handling (no error leak, citations preserved, is_grounded=False)
11. Offline deterministic mock LLM provider fallback
12. Validation: empty/whitespace message, excessively large history, invalid request
13. FastAPI endpoint: POST /api/assistant/chat (status 200, schema compliance, session continuity)
14. FastAPI endpoint: GET /api/assistant/health
15. Backward compatibility across all endpoints (/health, /, /api/laws, /api/sections, /api/search, /api/rag/query, /api/rag/health)
"""

import pytest
import uuid
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.schemas.rag import LegalSourceCitation, RetrievedSectionContext
from app.schemas.assistant import (
    ChatMessage,
    AssistantChatRequest,
    AssistantChatResponse
)
from app.services.llm_provider import (
    BaseLLMProvider,
    OfflineMockLLMProvider,
    GeminiLLMProvider
)
from app.services.assistant_service import (
    LegalAssistantService,
    BaseConversationStore,
    InMemoryConversationStore,
    ConversationContextHandler
)


class MockAssistantSuccessLLM(BaseLLMProvider):
    """Predictable mock provider for successful assistant synthesis tests."""
    @property
    def provider_name(self) -> str:
        return "mock_assistant_success_provider"

    def generate(self, prompt: str, system_instruction: str, temperature: float = 0.1, max_output_tokens: int = 1500) -> str:
        if "304" in prompt:
            return (
                "Under Section 304 of the Indian Penal Code, punishment for culpable homicide not amounting to murder "
                "is imprisonment for life or imprisonment of either description for a term which may extend to ten years, and fine."
            )
        return (
            "Under Section 73 of the Indian Contract Act, 1872, the injured party is entitled to compensation "
            "for any loss or damage naturally arising in the usual course of things from a breach of contract."
        )


class MockAssistantFailingLLM(BaseLLMProvider):
    """Predictable mock provider for testing LLM failure states in assistant layer."""
    @property
    def provider_name(self) -> str:
        return "mock_assistant_failing_provider"

    def generate(self, prompt: str, system_instruction: str, temperature: float = 0.1, max_output_tokens: int = 1500) -> str:
        raise RuntimeError("SIMULATED_UPSTREAM_LLM_TIMEOUT_503")


# ==============================================================================
# 1. NORMAL LEGAL QUESTION & GROUNDED RESPONSE
# ==============================================================================

def test_assistant_normal_legal_question_success():
    """Asserts that a standard legal question returns a grounded response with session ID and disclaimer."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.side_effect = [
        # Lexicon query
        [],
        # Candidate rows
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

    req = AssistantChatRequest(
        message="What is the compensation for breach of contract?",
        language="en"
    )
    provider = MockAssistantSuccessLLM()
    store = InMemoryConversationStore()

    resp = LegalAssistantService.chat(
        db=mock_cursor,
        request=req,
        provider=provider,
        store=store
    )

    assert resp.is_grounded is True
    assert resp.grounding_status == "grounded_high"
    assert resp.confidence == "grounded_high"
    assert "Section 73 of the Indian Contract Act, 1872" in resp.answer
    assert resp.conversation_id is not None
    assert len(resp.sources) == 1
    assert resp.sources[0].section_number == "73"
    assert resp.sources[0].law_name == "The Indian Contract Act, 1872"
    assert "Vidhik legal database" in resp.disclaimer


# ==============================================================================
# 2. SOURCE PRESERVATION & CITATIONS
# ==============================================================================

def test_assistant_relevant_legal_context_and_source_preservation():
    """Asserts that all authoritative statutory metadata coordinates are preserved end-to-end."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.side_effect = [
        [],  # Lexicon
        [    # Candidate rows
            {
                "section_id": 3040,
                "law_id": 45,
                "law_name": "The Indian Penal Code",
                "short_name": "IPC",
                "section_number": "304",
                "section_title": "Punishment for culpable homicide not amounting to murder",
                "description": "Culpable homicide punishment",
                "full_text": "Whoever commits culpable homicide not amounting to murder shall be punished with imprisonment for life...",
                "section_uid": "ipc-1860-sec-304",
                "jurisdiction": "Central",
                "source_pdf": "IPC-1860.pdf",
                "source_page_start": 82,
                "source_page_end": 83,
                "manual_review_required": False
            }
        ]
    ]
    mock_cursor.fetchone.return_value = {"total": 1}

    req = AssistantChatRequest(
        message="What is Section 304 of IPC?",
        language="en"
    )
    resp = LegalAssistantService.chat(
        db=mock_cursor,
        request=req,
        provider=MockAssistantSuccessLLM()
    )

    assert resp.is_grounded is True
    assert len(resp.sources) == 1
    source = resp.sources[0]
    assert source.law_id == 45
    assert source.law_name == "The Indian Penal Code"
    assert source.section_number == "304"
    assert source.section_title == "Punishment for culpable homicide not amounting to murder"
    assert source.source_pdf == "IPC-1860.pdf"
    assert source.source_page_start == 82
    assert source.source_page_end == 83
    assert source.jurisdiction == "Central"

    # Verify retrieved sections preserved
    assert len(resp.retrieved_sections) == 1
    sec = resp.retrieved_sections[0]
    assert sec.section_number == "304"
    assert "culpable homicide" in sec.section_text


# ==============================================================================
# 3. NO RELEVANT CONTEXT (ZERO HALLUCINATION)
# ==============================================================================

def test_assistant_no_relevant_context():
    """Asserts that queries with zero database matches return no_context and never hallucinate provisions."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.side_effect = [
        [],  # Lexicon
        []   # 0 matching sections
    ]
    mock_cursor.fetchone.return_value = {"total": 0}

    req = AssistantChatRequest(
        message="What are the penalties under Martian Intergalactic Trade Treaty?",
        language="en"
    )
    resp = LegalAssistantService.chat(
        db=mock_cursor,
        request=req,
        provider=MockAssistantSuccessLLM()
    )

    assert resp.is_grounded is False
    assert resp.grounding_status == "no_context"
    assert resp.confidence == "no_context"
    assert len(resp.sources) == 0
    assert len(resp.retrieved_sections) == 0
    assert "No relevant statutory provisions were found in the Vidhik legal database" in resp.answer


# ==============================================================================
# 4. INSUFFICIENT CONTEXT HANDLING
# ==============================================================================

def test_assistant_insufficient_context():
    """Asserts that candidates with blank or insufficient text yield insufficient_context status."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.side_effect = [
        [],  # Lexicon
        [    # Candidate row with whitespace only text
            {
                "section_id": 999,
                "law_id": 1,
                "law_name": "Test Act",
                "short_name": "TA",
                "section_number": "1",
                "section_title": "Short title",
                "description": "",
                "full_text": "   ",
                "section_uid": "test-sec-1",
                "jurisdiction": "Central",
                "source_pdf": None,
                "source_page_start": None,
                "source_page_end": None,
                "manual_review_required": False
            }
        ]
    ]
    mock_cursor.fetchone.return_value = {"total": 1}

    req = AssistantChatRequest(
        message="Explain test act section 1",
        language="en"
    )
    resp = LegalAssistantService.chat(
        db=mock_cursor,
        request=req,
        provider=MockAssistantSuccessLLM()
    )

    assert resp.is_grounded is False
    assert resp.grounding_status == "insufficient_context"


# ==============================================================================
# 5. MULTILINGUAL SUPPORT (ENGLISH & MARATHI)
# ==============================================================================

def test_assistant_marathi_multilingual_question():
    """Asserts that Marathi legal queries reuse multilingual terminology and return Marathi responses."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.side_effect = [
        # 1. Lexicon query matching Marathi term 'करारभंग'
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
        # 2. Candidate rows
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

    class MarathiMockProvider(BaseLLMProvider):
        @property
        def provider_name(self) -> str:
            return "marathi_mock"

        def generate(self, prompt: str, system_instruction: str, temperature: float = 0.1, max_output_tokens: int = 1500) -> str:
            assert "मराठीत" in prompt or "language" in prompt.lower()
            return "भारतीय करार कायदा, १८७२ च्या कलम ७३ नुसार कराराचा भंग झाल्यास नुकसान भरपाई मिळण्याचा अधिकार आहे."

    req = AssistantChatRequest(
        message="करारभंग झाल्यास नुकसान भरपाईची तरतूद काय आहे?",
        language="mr"
    )
    resp = LegalAssistantService.chat(
        db=mock_cursor,
        request=req,
        provider=MarathiMockProvider()
    )

    assert resp.is_grounded is True
    assert resp.language == "mr"
    assert "कलम ७३" in resp.answer or "भारतीय करार कायदा" in resp.answer
    assert len(resp.sources) == 1
    assert resp.sources[0].section_number == "73"


# ==============================================================================
# 6. FOLLOW-UP QUESTIONS & CONVERSATION CONTEXT RESOLUTION
# ==============================================================================

def test_conversation_context_handler_unit():
    """Unit tests for ConversationContextHandler detection, extraction, and query resolution."""
    # 1. No history: not a follow up
    assert ConversationContextHandler.is_follow_up("What is Section 304?", []) is False
    assert ConversationContextHandler.resolve_query("What is Section 304?", []) == "What is Section 304?"

    # 2. History with Section 304
    history = [
        ChatMessage(role="user", content="What is Section 304 of IPC?"),
        ChatMessage(role="assistant", content="Under Section 304 of the Indian Penal Code, culpable homicide is punishable...")
    ]

    # Follow-up: "Does it apply to a minor?"
    assert ConversationContextHandler.is_follow_up("Does it apply to a minor?", history) is True
    resolved = ConversationContextHandler.resolve_query("Does it apply to a minor?", history)
    assert "Section 304" in resolved
    assert "Does it apply to a minor?" in resolved

    # Marathi follow-up: "हे अल्पवयीन मुलास लागू होते का?"
    history_mr = [
        ChatMessage(role="user", content="कलम ३०४ काय आहे?"),
        ChatMessage(role="assistant", content="भारतीय दंड संहितेच्या कलम ३०४ नुसार...")
    ]
    assert ConversationContextHandler.is_follow_up("हे अल्पवयीन मुलास लागू होते का?", history_mr) is True
    resolved_mr = ConversationContextHandler.resolve_query("हे अल्पवयीन मुलास लागू होते का?", history_mr)
    assert "Section 304" in resolved_mr or "304" in resolved_mr

    # Self-contained question after history: should NOT be treated as follow-up to Section 304
    self_contained = "What is Section 420 of the Indian Penal Code regarding cheating?"
    assert ConversationContextHandler.is_follow_up(self_contained, history) is False
    assert ConversationContextHandler.resolve_query(self_contained, history) == self_contained


def test_assistant_follow_up_question_end_to_end():
    """
    End-to-end follow up test:
    Turn 1: User asks "What is Section 304?" -> Assistant responds about Section 304.
    Turn 2: User asks "Does it apply to a minor?" -> Assistant contextualizes with Section 304.
    """
    mock_cursor = MagicMock()

    # Query 1 DB calls: Lexicon, Candidates
    # Query 2 DB calls: Lexicon, Candidates
    mock_cursor.fetchall.side_effect = [
        [],  # Lexicon Q1
        [    # Candidate IPC Sec 304
            {
                "section_id": 304,
                "law_id": 45,
                "law_name": "The Indian Penal Code",
                "short_name": "IPC",
                "section_number": "304",
                "section_title": "Punishment for culpable homicide not amounting to murder",
                "description": "Culpable homicide",
                "full_text": "Whoever commits culpable homicide not amounting to murder shall be punished...",
                "section_uid": "ipc-1860-sec-304",
                "jurisdiction": "Central",
                "source_pdf": "IPC-1860.pdf",
                "source_page_start": 82,
                "source_page_end": 83,
                "manual_review_required": False
            }
        ],
        [],  # Lexicon Q2
        [    # Candidate IPC Sec 304 retrieved again because follow-up enriched with Section 304
            {
                "section_id": 304,
                "law_id": 45,
                "law_name": "The Indian Penal Code",
                "short_name": "IPC",
                "section_number": "304",
                "section_title": "Punishment for culpable homicide not amounting to murder",
                "description": "Culpable homicide",
                "full_text": "Whoever commits culpable homicide not amounting to murder shall be punished...",
                "section_uid": "ipc-1860-sec-304",
                "jurisdiction": "Central",
                "source_pdf": "IPC-1860.pdf",
                "source_page_start": 82,
                "source_page_end": 83,
                "manual_review_required": False
            }
        ]
    ]
    mock_cursor.fetchone.side_effect = [{"total": 1}, {"total": 1}]

    session_id = "test-session-conv-123"
    custom_store = InMemoryConversationStore()
    provider = MockAssistantSuccessLLM()

    # Turn 1
    req1 = AssistantChatRequest(
        message="What is Section 304?",
        conversation_id=session_id
    )
    resp1 = LegalAssistantService.chat(
        db=mock_cursor,
        request=req1,
        provider=provider,
        store=custom_store
    )
    assert resp1.conversation_id == session_id
    assert resp1.sources[0].section_number == "304"

    # Verify session store recorded turn 1
    stored_history = custom_store.get_history(session_id)
    assert len(stored_history) == 2
    assert stored_history[0].role == "user"
    assert stored_history[1].role == "assistant"

    # Turn 2: Follow-up question without naming Section 304
    req2 = AssistantChatRequest(
        message="Does it apply to a minor?",
        conversation_id=session_id
    )
    resp2 = LegalAssistantService.chat(
        db=mock_cursor,
        request=req2,
        provider=provider,
        store=custom_store
    )
    assert resp2.conversation_id == session_id
    assert resp2.is_grounded is True
    # The retrieved source must still be Section 304 because context was preserved
    assert len(resp2.sources) == 1
    assert resp2.sources[0].section_number == "304"
    assert resp2.sources[0].law_name == "The Indian Penal Code"

    # Verify session store recorded turn 2 (now 4 turns total)
    updated_history = custom_store.get_history(session_id)
    assert len(updated_history) == 4
    assert updated_history[2].content == "Does it apply to a minor?"


# ==============================================================================
# 7. CONVERSATION STORE BOUNDS & LRU EVICTION
# ==============================================================================

def test_conversation_store_turn_and_capacity_bounds():
    """Asserts that InMemoryConversationStore bounds per-conversation turns and evicts old sessions."""
    store = InMemoryConversationStore(max_conversations=3, max_turns_per_conversation=4)

    # 1. Per-session bounds
    for i in range(10):
        store.add_message("session-A", ChatMessage(role="user", content=f"msg {i}"))
    h_a = store.get_history("session-A")
    assert len(h_a) == 4
    assert h_a[-1].content == "msg 9"

    # 2. Capacity eviction
    store.add_message("session-B", ChatMessage(role="user", content="B"))
    store.add_message("session-C", ChatMessage(role="user", content="C"))
    # Max conversations is 3 (A, B, C)
    store.add_message("session-D", ChatMessage(role="user", content="D"))
    # Oldest (session-A) must have been evicted
    assert len(store.get_history("session-A")) == 0
    assert len(store.get_history("session-D")) == 1

    # 3. Clear session
    store.clear("session-D")
    assert len(store.get_history("session-D")) == 0


# ==============================================================================
# 8. FAILURE HANDLING (LLM FAILURE & ZERO LEAKAGE)
# ==============================================================================

def test_assistant_llm_failure_handling_and_no_leakage():
    """
    CRITICAL: Asserts that when LLM provider throws an exception:
    1. is_grounded is False
    2. grounding_status is 'synthesis_failed'
    3. Sources and citations remain preserved for legal review
    4. Internal technical exception details (e.g. SIMULATED_UPSTREAM_LLM_TIMEOUT_503) are NOT exposed
    """
    mock_cursor = MagicMock()
    mock_cursor.fetchall.side_effect = [
        [],  # Lexicon
        [    # Candidate row
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

    req = AssistantChatRequest(
        message="What is breach of contract?",
        language="en"
    )
    failing_provider = MockAssistantFailingLLM()

    resp = LegalAssistantService.chat(
        db=mock_cursor,
        request=req,
        provider=failing_provider
    )

    assert resp.is_grounded is False
    assert resp.grounding_status == "synthesis_failed"
    assert resp.confidence == "synthesis_failed"
    # Citations MUST still be preserved for the user
    assert len(resp.sources) == 1
    assert resp.sources[0].section_number == "73"
    # Technical exception string MUST NOT leak into the answer
    assert "SIMULATED_UPSTREAM_LLM_TIMEOUT_503" not in resp.answer
    assert "automated AI synthesis could not be completed" in resp.answer


# ==============================================================================
# 9. OFFLINE MOCK LLM PROVIDER FALLBACK
# ==============================================================================

def test_assistant_offline_mock_provider_fallback():
    """Asserts that Assistant works seamlessly with OfflineMockLLMProvider."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.side_effect = [
        [],  # Lexicon
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

    req = AssistantChatRequest(message="What is Section 73?")
    resp = LegalAssistantService.chat(
        db=mock_cursor,
        request=req,
        provider=OfflineMockLLMProvider()
    )

    assert resp.is_grounded is True
    assert "[DETERMINISTIC FALLBACK SYNTHESIS - TEST/OFFLINE MODE]" in resp.answer
    assert len(resp.sources) == 1
    assert resp.sources[0].section_number == "73"


# ==============================================================================
# 10. FASTAPI API ENDPOINT: POST /api/assistant/chat
# ==============================================================================

def test_api_assistant_chat_endpoint_success():
    """Asserts that POST /api/assistant/chat returns 200 with schema compliance."""
    client = TestClient(app)

    mock_db = MagicMock()
    mock_db.fetchall.side_effect = [
        [],  # Lexicon
        [
            {
                "section_id": 55,
                "law_id": 10,
                "law_name": "The Transfer of Property Act, 1882",
                "short_name": "TP Act",
                "section_number": "54",
                "section_title": "Sale defined",
                "description": "Definition of sale",
                "full_text": "Sale is a transfer of ownership in exchange for a price paid or promised...",
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
            "/api/assistant/chat",
            json={
                "message": "How is sale defined under Indian law?",
                "language": "en"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "How is sale defined under Indian law?"
        assert data["is_grounded"] is True
        assert data["conversation_id"] is not None
        assert len(data["sources"]) == 1
        assert data["sources"][0]["section_number"] == "54"
        assert data["sources"][0]["law_name"] == "The Transfer of Property Act, 1882"
        assert "Sale is a transfer of ownership" in data["retrieved_sections"][0]["section_text"]
        assert "Vidhik legal database" in data["disclaimer"]

    finally:
        app.dependency_overrides.clear()


def test_api_assistant_chat_validation_empty_and_invalid():
    """Asserts that empty or invalid requests return 422 Unprocessable Entity."""
    client = TestClient(app)
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        # 1. Empty message
        res1 = client.post("/api/assistant/chat", json={"message": "   "})
        assert res1.status_code in (422, 400)

        # 2. Missing message
        res2 = client.post("/api/assistant/chat", json={"language": "en"})
        assert res2.status_code in (422, 400)

        # 3. Excessively large history payload (> 100 turns)
        huge_history = [{"role": "user", "content": f"msg {i}"} for i in range(105)]
        res3 = client.post("/api/assistant/chat", json={"message": "test", "history": huge_history})
        assert res3.status_code == 422
        assert "exceeds maximum permitted length" in res3.json()["detail"]

    finally:
        app.dependency_overrides.clear()


# ==============================================================================
# 11. FASTAPI API ENDPOINT: GET /api/assistant/health
# ==============================================================================

def test_api_assistant_health_endpoint():
    """Asserts that GET /api/assistant/health returns operational status and provider details."""
    client = TestClient(app)
    response = client.get("/api/assistant/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert data["subsystem"] == "Vidhik AI Legal Assistant"
    assert "llm_provider" in data
    assert "conversation_store" in data
    assert data["grounding_enforced"] is True


# ==============================================================================
# 12. BACKWARD COMPATIBILITY ENDPOINTS
# ==============================================================================

def test_backward_compatibility_existing_endpoints_with_assistant():
    """
    Asserts that all pre-existing endpoints continue functioning normally:
    /health, /, /api/laws, /api/sections, /api/search, /api/rag/query, /api/rag/health
    """
    client = TestClient(app)

    mock_db = MagicMock()
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
                "section_title": "Compensation for breach",
                "section_uid": "indian-contract-act-1872-sec-73",
                "section_text": "When a contract has been broken...",
                "full_text": "When a contract has been broken...",
                "description": "Compensation for breach",
                "chapter_number": "VI",
                "chapter_title": "Breach",
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
            res_health = client.get("/health")
            assert res_health.status_code == 200
            assert res_health.json()["status"] == "healthy"

            # 2. Root SPA / Application Entry Point
            res_root = client.get("/")
            assert res_root.status_code == 200
            assert "text/html" in res_root.headers.get("content-type", "")
            assert "<!DOCTYPE html>" in res_root.text or "<html" in res_root.text

            # 3. Laws
            res_laws = client.get("/api/laws?limit=1")
            assert res_laws.status_code == 200

            # 4. Sections
            res_sections = client.get("/api/sections?limit=1")
            assert res_sections.status_code == 200

            # 5. Search
            res_search = client.get("/api/search?q=contract")
            assert res_search.status_code == 200

            # 6. RAG Query
            res_rag = client.post("/api/rag/query", json={"query": "contract breach"})
            assert res_rag.status_code == 200

            # 7. RAG Health
            res_rag_health = client.get("/api/rag/health")
            assert res_rag_health.status_code == 200

            # 8. Assistant Health
            res_asst_health = client.get("/api/assistant/health")
            assert res_asst_health.status_code == 200

        finally:
            app.dependency_overrides.clear()
