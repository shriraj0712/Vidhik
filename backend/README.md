# Vidhik Platform - Backend API Service

FastAPI-powered REST backend for the **Vidhik Legal Platform**, providing unified legal research, citizen & lawyer workflows, hardened JWT/bcrypt authentication, conversational AI assistance, grounded RAG, and an advanced legal knowledge base over Indian statutory laws stored in PostgreSQL (`vidhik_db`).

---

## 1. Directory Structure

```text
backend/
├── app/
│   ├── __init__.py           # Package versioning
│   ├── main.py               # FastAPI entry point, middleware pipeline, SPA routing
│   ├── database.py           # Thread-safe PostgreSQL connection pool (psycopg2)
│   ├── core/
│   │   ├── __init__.py
│   │   └── security.py       # Bcrypt password hashing, SHA-256 upgrade, signed JWT
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── rate_limiter.py   # Token-bucket / IP-based sliding window rate limiter
│   │   └── security_headers.py # HSTS, CSP, XSS, Frame protection headers
│   ├── models/
│   │   ├── __init__.py
│   │   ├── law.py            # Dataclass model representing laws table
│   │   └── section.py        # Dataclass model representing sections table
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── law.py            # Law response schemas
│   │   ├── section.py        # Section response schemas
│   │   ├── search.py         # Search response schemas
│   │   ├── query.py          # Multilingual query analysis schemas
│   │   ├── citizen.py        # Citizen dashboard, cases, profile schemas
│   │   ├── lawyer.py         # Lawyer clients, cases, notes schemas
│   │   ├── documentation.py  # Legal procedures & checklists schemas
│   │   ├── document_analysis.py # Document analysis & entity extraction schemas
│   │   ├── assistant.py      # Conversational AI assistant schemas
│   │   ├── rag.py            # Grounded RAG query schemas
│   │   └── knowledge_base.py # BNS/BNSS/BSA & 24 Bare Acts knowledge schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py   # User registration, login, JWT session, RBAC
│   │   ├── audit_service.py  # Security audit logging
│   │   ├── citizen_service.py # Citizen case and document operations
│   │   ├── lawyer_service.py # Advocate client, case, and note operations
│   │   ├── documentation_service.py # 25 citizen procedures & checklists
│   │   ├── document_analysis_service.py # Contract clause parsing & risk assessment
│   │   ├── document_parser_service.py # PDF (pypdf) and DOCX (python-docx) extraction
│   │   ├── query_service.py  # Multilingual NLP query understanding & Devanagari normalization
│   │   ├── ranking_service.py # Lexicon candidate ranking & TF-IDF scoring
│   │   ├── search_service.py # Legal search and snippet generation
│   │   ├── assistant_service.py # Multi-turn conversational AI legal assistant
│   │   ├── rag_service.py    # Grounded RAG synthesis with source coordinates
│   │   ├── context_builder.py # Statutory context deduplication & disclaimers
│   │   ├── llm_provider.py   # OfflineMock, Gemini, and OpenAI provider implementations
│   │   └── knowledge_service.py # Advanced statutory knowledge retrieval
│   ├── static/               # SPA Frontend assets (index.html, app.js, styles.css)
│   └── routers/
│       ├── __init__.py
│       ├── health.py         # GET /health system status and DB ping
│       ├── laws.py           # GET /api/laws/{law_id}
│       ├── sections.py       # GET /api/sections/{section_id}
│       ├── search.py         # GET /api/search multi-field legal search
│       ├── auth.py           # /api/auth (register, login, me, logout)
│       ├── citizen.py        # /api/citizen (dashboard, cases, docs, bookmarks, etc.)
│       ├── lawyer.py         # /api/lawyer (dashboard, clients, cases, notes, etc.)
│       ├── documentation.py  # /api/documentation (categories, procedures, checklists)
│       ├── document_analysis.py # /api/analysis (upload, text, history, save-to-case)
│       ├── assistant.py      # /api/assistant (chat, health)
│       ├── rag.py            # /api/rag (query, health)
│       └── knowledge_base.py # /api/knowledge (overview, offences, punishments, acts, etc.)
├── tests/                    # 27 automated unit and integration tests
├── .env.example              # Environment variables template
├── requirements.txt          # Python dependencies
└── README.md                 # Backend documentation
```

---

## 2. Prerequisites & Setup

* **Python 3.10+** (Tested on Python 3.14)
* **PostgreSQL 14+** running `vidhik_db`
* Configure `.env`:
```bash
cp .env.example .env
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Run tests:
```bash
pytest tests -v
```

Run the development server:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Access API Documentation:
* **Interactive Swagger UI**: `http://127.0.0.1:8000/docs`
* **ReDoc**: `http://127.0.0.1:8000/redoc`
* **SPA Frontend**: `http://127.0.0.1:8000/`

---

## 3. Core Architecture Guarantees

1. **Security & Cryptography**: Bcrypt password hashing with work factor 12, legacy SHA-256 transparent upgrade detection, and signed RFC 7519 JWT tokens.
2. **Role-Based Access Control**: Granular RBAC supporting `citizen`, `lawyer`, and `admin` roles.
3. **Middleware Pipeline**: Hardened security headers (HSTS, CSP, XSS protection) and sliding-window rate limiting.
4. **Deterministic AI & Offline Mode**: `OfflineMockLLMProvider` ensures full local testability with zero network calls and deterministic responses.
5. **Schema Isolation**: Strict separation between Phase 16 `legal_procedures` (25 citizen procedural guides) and Phase 17 `statutory_procedures` (BNSS criminal procedures).

---

## 4. Current Boundaries & Roadmap

* **AI Assistant UI**: Backend `/api/assistant/chat` complete and tested; frontend chat widget scheduled for Step 12.
* **Bare Acts Catalog UI**: 24 Acts datasets (3,252 sections) and APIs complete; frontend explorer view scheduled for Step 12.
* **Phase 17 Live Ingestion**: Schema migration `009` and ingestion scripts ready; live PostgreSQL ingestion scheduled for Step 11.
