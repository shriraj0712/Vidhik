# Phase 10: AI Legal Assistant Architecture & Implementation Report

## 1. Executive Summary

Phase 10 introduces the **AI Legal Assistant** layer on top of the completed Phase 9 Grounded Statutory RAG system. The assistant provides an interactive, conversational interface capable of answering natural-language legal inquiries, managing follow-up questions referencing prior dialogue, maintaining conversation state, and delivering authoritative statutory answers strictly grounded in the Vidhik PostgreSQL database.

All retrieval, search, ranking, multilingual expansion, and database querying are delegated to the existing Phase 9 infrastructure without duplication or redundant query pathways.

---

## 2. End-to-End System Architecture

The AI Legal Assistant implements the mandated linear flow:

```
User
  │
  ▼
AI Legal Assistant Orchestration Layer (`LegalAssistantService`)
  │
  ▼
Conversation & Follow-up Context Handler (`ConversationContextHandler`)
  │
  ▼
Existing Phase 9 RAG Engine (`LegalRAGService`)
  │
  ▼
Existing Legal Search & Ranking (`LegalSearchService` + `LegalRankingService`)
  │
  ▼
PostgreSQL Legal Database (`vidhik_db`: `laws`, `law_sections`, `legal_lexicon`)
  │
  ▼
Grounded Answer + Authoritative Statutory Sources (`LegalSourceCitation`)
```

### Architectural Principles:
1. **Delegation, Not Duplication**: The assistant service is strictly an orchestration layer. It does not re-implement full-text search, semantic parsing, or statutory ranking.
2. **Contextual Enrichment**: Follow-up questions that omit statutory references (e.g. *"Does it apply to a minor?"*) are automatically enriched with statutory anchors (e.g. *"Section 304"*, *"The Indian Penal Code"*) extracted from prior conversation turns.
3. **Strict Grounding & Zero Hallucination**: Every substantive legal rule, penalty, or condition must cite verified database records. If statutory context is missing or insufficient, the assistant explicitly reports that without generating speculative advice.
4. **Mandatory Statutory Disclaimer**: Every response carries an authoritative disclaimer clarifying that the assistant provides legal research and information, not formal legal counsel.

---

## 3. API Endpoints

### 3.1 `POST /api/assistant/chat`

The primary conversational endpoint for querying the AI Legal Assistant.

#### Request Schema (`AssistantChatRequest`):
```json
{
  "message": "Does it apply to a minor?",
  "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "history": [
    {
      "role": "user",
      "content": "What is Section 304 of IPC?"
    },
    {
      "role": "assistant",
      "content": "Under Section 304 of the Indian Penal Code, culpable homicide not amounting to murder is punishable with imprisonment for life or up to ten years, and fine."
    }
  ],
  "language": "en",
  "jurisdiction": "Central",
  "law_id": 45,
  "max_sections": 5,
  "temperature": 0.1
}
```

- `message` (*required*): Non-empty string representing the user's natural-language query or follow-up prompt.
- `conversation_id` (*optional*): Client session identifier. If omitted, a UUIDv4 is automatically generated and returned.
- `history` (*optional*): Chronological list of previous conversation turns (`ChatMessage`). Allows stateless frontends to supply conversation history directly. If omitted, history is retrieved from the server-side session store using `conversation_id`.
- `language` (*optional*, default: `"en"`): Target language: `"en"`, `"mr"`, or `"hi"`.
- `jurisdiction`, `law_id`, `max_sections`, `temperature` (*optional*): Passthrough constraints for statutory retrieval and synthesis.

#### Response Schema (`AssistantChatResponse`):
```json
{
  "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "message": "Does it apply to a minor?",
  "answer": "<grounded answer generated from the retrieved statutory context>",
  "language": "en",
  "grounding_status": "grounded_high",
  "confidence": "grounded_high",
  "is_grounded": true,
  "sources": [
    {
      "law_id": 45,
      "law_name": "The Indian Penal Code",
      "section_id": 3040,
      "section_number": "304",
      "section_title": "Punishment for culpable homicide not amounting to murder",
      "section_uid": "ipc-1860-sec-304",
      "source_pdf": "IPC-1860.pdf",
      "source_page_start": 82,
      "source_page_end": 83,
      "jurisdiction": "Central"
    }
  ],
  "retrieved_sections": [ ... ],
  "retrieval_metadata": {
    "total_candidates_found": 1,
    "sections_used": 1,
    "query_terms_matched": [ "culpable-homicide" ],
    "concept_categories": [ "criminal_law" ],
    "multilingual_synonyms_applied": [],
    "retrieval_strategy": "deterministic_lexicon_ranked"
  },
  "disclaimer": "This legal assistant provides informational and research support grounded in Indian statutory law from the Vidhik legal database. It does not constitute formal legal advice or substitute for consultation with a qualified legal professional."
}
```

### 3.2 `GET /api/assistant/health`

Diagnostic endpoint returning the operational state of the assistant layer.

#### Response:
```json
{
  "status": "operational",
  "subsystem": "Vidhik AI Legal Assistant",
  "underlying_rag_engine": "Phase 9 Grounded Statutory RAG",
  "llm_provider": "offline_deterministic_fallback",
  "conversation_store": "InMemoryConversationStore (Bounded)",
  "multilingual_support": ["en", "mr", "hi"],
  "grounding_enforced": true
}
```

---

## 4. Conversation & Follow-Up Context Handling

### 4.1 Storage Abstraction (`BaseConversationStore`)

A decoupled interface allows persistent storage (Redis, PostgreSQL, DynamoDB) to be introduced later without changing assistant orchestration:

```python
class BaseConversationStore(ABC):
    @abstractmethod
    def get_history(self, conversation_id: str) -> List[ChatMessage]: ...
    
    @abstractmethod
    def add_message(self, conversation_id: str, message: ChatMessage) -> None: ...
    
    @abstractmethod
    def clear(self, conversation_id: str) -> None: ...
```

The default implementation, `InMemoryConversationStore`:
- Uses thread-safe locking (`threading.Lock`).
- Limits history to 20 messages per session to prevent unbounded memory growth.
- Limits total active sessions (default: 1,000) with oldest-session eviction.

### 4.2 Contextual Follow-Up Resolution (`ConversationContextHandler`)

When users submit follow-up questions like:
- *"Does it apply to a minor?"*
- *"What is the punishment under this?"*
- *"Is that bailable?"*
- *"हे अल्पवयीन मुलास लागू होते का?"* (Marathi)

The handler executes deterministic analysis:
1. **Follow-Up Detection**: Checks for referential tokens (*"it"*, *"this"*, *"that"*, *"punishment"*, *"minor"*, *"हे"*, *"याची"*, etc.) or short interrogative phrases when no statute or section is explicitly named.
2. **Anchor Extraction**: Scans the conversation history from newest to oldest for statutory entities:
   - Section regex: `(?:section|sec\.?|कलम|धारा)\s*([0-9०-९]+[A-Za-z\-]*)`
   - Article regex: `(?:article|art\.?|अनुच्छेद)\s*([0-9०-९]+[A-Za-z\-]*)`
   - Act titles: Common central/state statutory codes in English and Marathi.
   - Devanagari numerals are normalized to ASCII.
3. **Query Enrichment**: Synthesizes an augmented query for the retrieval engine:
   - Input: *"Does it apply to a minor?"*
   - Context: Section 304, The Indian Penal Code
   - Augmented Query: `"Section 304 The Indian Penal Code Does it apply to a minor?"`
4. **Self-Contained Query Protection**: If the user asks a complete, new question (e.g. *"What is Section 420 regarding cheating?"*), the handler preserves it as-is without cross-polluting prior context.

---

## 5. Grounding & Failure Handling

### 5.1 Strict Grounding & No Hallucination
- If no statutory provisions match the query (`total_candidates == 0`), the assistant returns:
  - `grounding_status = "no_context"`
  - `is_grounded = false`
  - Safe, polite message indicating that no relevant provisions were located in the database.
- If provisions are located but lack textual body, it returns `insufficient_context`.

### 5.2 Failure Shielding & Zero Technical Leakage
- If upstream LLM providers (Gemini / OpenAI) fail, timeout, or hit rate limits:
  - The internal exception is caught and logged to server logs with full stack trace.
  - The API response returns `grounding_status = "synthesis_failed"` and `is_grounded = false`.
  - All retrieved statutory sections and citations (`sources`) are preserved and returned to the user for direct manual inspection.
  - Internal exception traces, API keys, and credential strings are never exposed in the user-facing answer or JSON response.

### 5.3 Offline Deterministic Mock Mode
When external LLM API keys are not configured, the assistant automatically routes through `OfflineMockLLMProvider`, constructing deterministic synthesis directly from retrieved statutory text:
- `OfflineMockLLMProvider` is intended for local development/testing.
- It is a deterministic fallback.
- It is not equivalent to production-quality LLM synthesis.

---

## 6. Verification & Test Results

The backend test suite was run via `pytest -v`, executing all Phase 9 and Phase 10 tests.

### Test Summary:
- **Phase 10 tests**: 14/14 passing
- **Phase 9 regression tests**: 13/13 passing
- **Total**: 27/27 passing

### Test Breakdown:
- **Phase 10 Assistant Tests** (`tests/test_assistant_service.py`):
  1. `test_assistant_normal_legal_question_success`: PASSED
  2. `test_assistant_relevant_legal_context_and_source_preservation`: PASSED
  3. `test_assistant_no_relevant_context`: PASSED
  4. `test_assistant_insufficient_context`: PASSED
  5. `test_assistant_marathi_multilingual_question`: PASSED
  6. `test_conversation_context_handler_unit`: PASSED
  7. `test_assistant_follow_up_question_end_to_end`: PASSED
  8. `test_conversation_store_turn_and_capacity_bounds`: PASSED
  9. `test_assistant_llm_failure_handling_and_no_leakage`: PASSED
  10. `test_assistant_offline_mock_provider_fallback`: PASSED
  11. `test_api_assistant_chat_endpoint_success`: PASSED
  12. `test_api_assistant_chat_validation_empty_and_invalid`: PASSED
  13. `test_api_assistant_health_endpoint`: PASSED
  14. `test_backward_compatibility_existing_endpoints_with_assistant`: PASSED
- **Phase 9 Regression Tests** (`tests/test_rag_service.py`):
  15. `test_context_builder_deduplication`: PASSED
  16. `test_context_builder_truncation_disclaimer`: PASSED
  17. `test_offline_mock_llm_provider`: PASSED
  18. `test_provider_factory_fallback`: PASSED
  19. `test_rag_service_successful_retrieval_and_llm_success`: PASSED
  20. `test_rag_service_llm_failure_state`: PASSED
  21. `test_rag_service_zero_database_results`: PASSED
  22. `test_rag_service_multilingual_marathi_query`: PASSED
  23. `test_source_citation_preservation`: PASSED
  24. `test_api_rag_query_endpoint_success`: PASSED
  25. `test_api_rag_query_empty_validation`: PASSED
  26. `test_api_rag_health_endpoint`: PASSED
  27. `test_backward_compatibility_endpoints`: PASSED

---

## 7. Frontend Architecture Inspection & Integration Plan

### Current Workspace State
An inspection of the workspace confirmed that the repository currently contains:
- `backend/`: FastAPI application, routers, services, database models, schemas, and pytest suites.
- `database/`: Database initialization SQL schemas and migrations.
- `data/`: Extracted acts, legal dataset text, and diglot gazettes.
- `scripts/`: Data ingestion, validation, and parsing scripts.
- `docs/`: Technical specifications and reports.

There is currently no frontend application bundle (e.g., React, Next.js, or Vue) committed to this repository.

### Frontend Integration Roadmap
When a client application is added, the AI Legal Assistant API is ready for immediate integration via the following design contract:

1. **State Management**:
   - Maintain `conversationId: string | null` in client state (e.g. `localStorage` or session store).
   - Maintain `messages: Array<{ role: 'user' | 'assistant', content: string, sources?: LegalSourceCitation[] }>`.
2. **API Client Integration**:
   - Submit user messages to `POST /api/assistant/chat`.
   - Pass existing `conversation_id` and the last $N$ turns in `history`.
3. **UI Presentation Guidelines**:
   - **Assistant Answer**: Display formatted Markdown text.
   - **Citation Badges**: Render expandable citation chips for each item in `sources` showing `law_name`, `section_number`, and page coordinates.
   - **Grounding Indicator**: Display a visual badge (e.g., green shield for `grounded_high`, yellow for `grounded_medium`, gray for `no_context`).
   - **Legal Disclaimer**: Affix the statutory disclaimer footer at the base of the assistant response container.
