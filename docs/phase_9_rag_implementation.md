# Phase 9: Grounded Legal Knowledge Retrieval (RAG) Architecture & Implementation Report

## Executive Summary
Phase 9 introduces an end-to-end grounded Retrieval-Augmented Generation (RAG) pipeline to the **VIDHIK AI** platform. Built directly on top of VIDHIK's existing PostgreSQL legal corpus, multilingual query understanding, and deterministic 10-tier legal ranking system, Phase 9 guarantees zero statutory hallucination, explicit legal citations, strict state separation between retrieved evidence and AI synthesis, and seamless offline testing capability.

---

## 1. High-Level Architecture & Pipeline Flow

The Phase 9 RAG workflow reuses existing core search infrastructure without duplication:

```
                      User Legal Question (en / mr / hi)
                                     │
                                     ▼
                ┌──────────────────────────────────────────┐
                │        LegalQueryService.analyze_query()  │
                │  - Multilingual Lexicon & Synonyms       │
                │  - Concept Domains & Stopword Removal    │
                └────────────────────┬─────────────────────┘
                                     │
                                     ▼
                ┌──────────────────────────────────────────┐
                │ LegalSearchService.retrieve_ranked_cands │
                │  - Multi-field phrase & token SQL match  │
                │  - Multilingual candidate expansion      │
                │  - Zero duplicate search logic           │
                └────────────────────┬─────────────────────┘
                                     │
                                     ▼
                ┌──────────────────────────────────────────┐
                │      LegalRankingService.rank_candidates │
                │  - 10-tier deterministic hierarchy       │
                │  - Section number, title, body precedence│
                └────────────────────┬─────────────────────┘
                                     │
                                     ▼
                ┌──────────────────────────────────────────┐
                │        LegalContextBuilder               │
                │  - Law ID + Section deduplication        │
                │  - 3000-char truncation with disclaimer  │
                │  - Structured source coordinate mapping  │
                └────────────────────┬─────────────────────┘
                                     │
                                     ▼
                ┌──────────────────────────────────────────┐
                │          LegalRAGService                 │
                │  - Grounded prompt formulation           │
                │  - State & confidence orchestration     │
                └──────────────┬─────────────┬─────────────┘
                               │             │
                    Success    │             │  Provider Failure
                               ▼             ▼
              ┌──────────────────────┐   ┌──────────────────────────┐
              │ BaseLLMProvider      │   │ Fallback Safe Response   │
              │ (Gemini / Offline)   │   │ - is_grounded: False     │
              │ - is_grounded: True  │   │ - conf: synthesis_failed │
              │ - conf: grounded_high│   │ - Sources retained       │
              └──────────────────────┘   └──────────────────────────┘
```

---

## 2. Key Corrections & Architectural Refinements

### 1. Existing Search Infrastructure Reuse
- **Elimination of Duplicate Search Engine:** `LegalRAGService` does not construct ad-hoc SQL queries or execute custom database searches.
- Instead, `LegalSearchService.retrieve_ranked_candidates()` acts as the single source of truth for query understanding, candidate retrieval, and 10-tier ranking across both `/api/search` and `/api/rag/query`.
- Multilingual expansion (English, Marathi, Hindi terms and synonyms) from `LegalQueryService` feeds directly into the candidate retrieval process.

### 2. Strict LLM Failure State Separation
- If an LLM provider fails (e.g. network timeout, rate limit, quota exhaustion):
  - `is_grounded` is strictly set to `False` (never `True`).
  - `confidence` is set to `"synthesis_failed"`.
  - Retrieved legal sources (`sources`) and provisions (`retrieved_sections`) remain completely intact and available to the user for direct review.
  - The response distinguishes between **context found** and **synthesis status**.

### 3. Error Handling & Security
- Technical exceptions (such as internal stack traces, API keys, database connection strings) are logged internally using Python's `logging` module and are never leaked to end users.
- User-facing responses return safe, sanitized, localized guidance.
- Credentials and settings are loaded strictly via environment variables. `.env` is excluded in `.gitignore`, and `.env.example` contains only placeholder values.

### 4. Deterministic Offline Mock Provider
- `OfflineMockLLMProvider` is registered under `provider_name = "offline_deterministic_fallback"`.
- It acts as a deterministic fallback and local testing engine, assembling authoritative excerpts without claiming to perform neural reasoning.

### 5. Context Truncation & Integrity Disclaimers
- Lengthy provisions (>3,000 characters) are capped to fit prompt budgets while preserving legal integrity:
  - Marked with `is_truncated = True` in API payloads.
  - Attached with statutory warning headers: `[NOTICE: This provision is lengthy and has been excerpted to preserve context budget. Do not interpret this excerpt as the exhaustive statutory provision. Refer to the complete primary source document.]`.
  - The system prompt explicitly instructs the LLM: `TRUNCATED / EXCERPTED PROVISIONS: If a retrieved statutory provision is marked as '(EXCERPTED)' or contains a truncation disclaimer, you MUST NOT treat it as the complete statutory provision.`

---

## 3. API Specification

### Endpoint: `POST /api/rag/query`
- **Request Body:**
  ```json
  {
    "query": "What compensation is awarded for breach of contract?",
    "language": "en",
    "max_sections": 5,
    "temperature": 0.1
  }
  ```

- **Response Body (Success):**
  ```json
  {
    "query": "What compensation is awarded for breach of contract?",
    "language": "en",
    "answer": "Under Section 73 of the Indian Contract Act, 1872, when a contract has been broken, the party who suffers by such breach is entitled to receive compensation...",
    "confidence": "grounded_high",
    "is_grounded": true,
    "sources": [
      {
        "law_id": 1,
        "law_name": "The Indian Contract Act, 1872",
        "section_id": 101,
        "section_number": "73",
        "section_title": "Compensation for loss or damage caused by breach of contract",
        "section_uid": "indian-contract-act-1872-sec-73",
        "source_pdf": "A1872-09.pdf",
        "source_page_start": 25,
        "source_page_end": 26,
        "jurisdiction": "Central"
      }
    ],
    "retrieved_sections": [
      {
        "law_name": "The Indian Contract Act, 1872",
        "section_number": "73",
        "section_title": "Compensation for loss or damage caused by breach of contract",
        "section_text": "When a contract has been broken...",
        "relevance_rank": 1,
        "is_truncated": false
      }
    ],
    "retrieval_metadata": {
      "total_candidates_found": 1,
      "sections_used": 1,
      "query_terms_matched": ["breach-of-contract"],
      "concept_categories": ["contract_and_commercial"],
      "multilingual_synonyms_applied": ["करारभंग", "संविदा भंग"],
      "retrieval_strategy": "deterministic_lexicon_ranked"
    },
    "disclaimer": "This analysis is generated from statutory provisions indexed in the Vidhik legal database. It is intended solely for legal research and informational purposes and does not constitute formal legal advice or representation."
  }
  ```

### Endpoint: `GET /api/rag/health`
- **Response:**
  ```json
  {
    "status": "operational",
    "subsystem": "Vidhik Legal RAG Engine",
    "llm_provider": "gemini (gemini-2.5-flash)",
    "retrieval_backend": "PostgreSQL (vidhik_db) + Deterministic Ranking",
    "grounding_enforced": true
  }
  ```

---

## 4. Test Suite Coverage

All 13 test scenarios pass with 100% success rate:
- `test_context_builder_deduplication`: Deduplicates identical (law_id, section_number) candidate hits.
- `test_context_builder_truncation_disclaimer`: Validates `is_truncated = True`, truncation notices, and prompt instructions.
- `test_offline_mock_llm_provider`: Verifies deterministic synthesis fallback and error on empty context.
- `test_provider_factory_fallback`: Verifies graceful fallback to offline provider when API keys are absent.
- `test_rag_service_successful_retrieval_and_llm_success`: Validates end-to-end grounded query execution.
- `test_rag_service_llm_failure_state`: Validates `is_grounded=False`, `confidence="synthesis_failed"`, source preservation, and safe error messages.
- `test_rag_service_zero_database_results`: Validates non-hallucinatory `no_context` response.
- `test_rag_service_multilingual_marathi_query`: Validates multilingual terminology expansion (Marathi/Hindi).
- `test_source_citation_preservation`: Validates preservation of PDF coordinates, page ranges, and section UIDs.
- `test_api_rag_query_endpoint_success`: Validates HTTP 200 and schema compliance for `POST /api/rag/query`.
- `test_api_rag_query_empty_validation`: Validates HTTP 422 on whitespace/empty queries.
- `test_api_rag_health_endpoint`: Validates HTTP 200 for `GET /api/rag/health`.
- `test_backward_compatibility_endpoints`: Validates `/health`, `/api/laws`, `/api/sections`, and `/api/search`.
