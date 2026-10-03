# Vidhik — AI-Native Legal Platform

**Vidhik** is a unified, high-precision legal intelligence and workflow platform for Indian statutory law, integrating modern AI capabilities, comprehensive legal knowledge, hardened security, and a dual-role (Citizen & Advocate) workspace.

---

## Architecture Overview

The standardized Vidhik architecture unifies three primary functional layers:

1. **Phase 16 — Canonical Full-Stack Baseline**:
   - Single-Page Application (SPA) serving Citizen and Lawyer portals at `/`, `/citizen`, `/lawyer`.
   - Comprehensive REST APIs for legal research, citizen workflows, advocate case management, documentation, and document analysis.
   - Preserves `legal_procedures` (25 authoritative citizen procedural guides and checklists).

2. **Phase 15 — Security Foundation & Grounded AI/RAG**:
   - Hardened authentication: modern `bcrypt` password hashing, transparent legacy `SHA-256` migration, and RFC 7519 signed JWT tokens.
   - Role-Based Access Control (`citizen`, `lawyer`, `admin`).
   - Middleware pipeline: `CORSMiddleware`, `RateLimiterMiddleware`, and `SecurityHeadersMiddleware`.
   - Conversational AI Legal Assistant (`/api/assistant/chat`) and Grounded Legal RAG engine (`/api/rag/query`) with `OfflineMockLLMProvider`, `GeminiLLMProvider`, and `OpenAILLMProvider`.

3. **Phase 17 — Advanced Legal Knowledge Layer (BNS, BNSS, BSA & 24 Bare Acts)**:
   - Complete statutory provisions for Bharatiya Nyaya Sanhita (BNS), Bharatiya Nagarik Suraksha Sanhita (BNSS), and Bharatiya Sakshya Adhiniyam (BSA).
   - Repository of **24 Indian Bare Acts** comprising **3,252 sections**.
   - Predecessor mappings (BNS ↔ IPC, BNSS ↔ CrPC, BSA ↔ IEA), verified Supreme Court judgments, and statutory criminal court procedures (`statutory_procedures` in migration `009`).

---

## System Directory Layout

```text
Vidhik/
├── backend/
│   ├── app/
│   │   ├── core/             # Security, JWT cryptographic utilities
│   │   ├── middleware/       # Rate limiting, security headers
│   │   ├── models/           # Data models
│   │   ├── routers/          # 12 unified FastAPI routers (78 functional endpoints)
│   │   ├── schemas/          # Pydantic validation schemas
│   │   ├── services/         # Business logic, NLP query understanding, AI, RAG, knowledge
│   │   ├── static/           # SPA frontend (HTML5, CSS3, Vanilla JS)
│   │   ├── database.py       # Threaded PostgreSQL connection pool
│   │   └── main.py           # FastAPI entry point, middleware registration, SPA routing
│   ├── tests/                # Automated pytest suite (27 passing tests)
│   ├── requirements.txt      # Python dependencies
│   └── .env.example          # Environment configuration template
├── data/
│   └── knowledge_base/       # 24 Bare Acts JSONs, BNS/BNSS/BSA, predecessor mappings, judgments
├── database/
│   └── migrations/           # PostgreSQL SQL migrations (001, 002, 006, 007, 008, 009)
└── scripts/                  # Knowledge build and verification tooling
```

---

## Standardized Modules & Endpoints

| Module | Route Prefix | Key Endpoints | Description |
| :--- | :--- | :--- | :--- |
| **Health** | `/health` | `GET /health` | System status and PostgreSQL database connection probe |
| **Laws & Sections**| `/api/laws`, `/api/sections` | `GET /api/laws`, `GET /api/sections/{id}` | Statutory laws and section text inspection |
| **Search** | `/api/search` | `GET /api/search` | Multi-field legal search across titles, numbers, and text |
| **Authentication** | `/api/auth` | `/register`, `/login`, `/me`, `/logout` | Hardened JWT authentication and session management |
| **Citizen Portal** | `/api/citizen` | `/dashboard`, `/cases`, `/documents`, `/hearings`, `/bookmarks`, `/search-history`, `/notifications`, `/procedures` | Citizen legal workspace, case tracking, procedural guides |
| **Lawyer Portal** | `/api/lawyer` | `/dashboard`, `/clients`, `/cases`, `/documents`, `/hearings`, `/cases/{id}/notes`, `/profile` | Advocate practice management, clients, confidential notes |
| **Documentation** | `/api/documentation`| `/categories`, `/procedures`, `/procedures/{id}/checklist` | 25 citizen administrative and legal procedures |
| **Document Analysis**| `/api/analysis` | `/upload`, `/text`, `/history`, `/{id}`, `/{id}/save-to-case` | Contract/PDF/DOCX analysis, entity extraction, risk score |
| **AI Assistant** | `/api/assistant` | `POST /chat`, `GET /health` | Multi-turn conversational legal assistant grounded in statutes |
| **Legal RAG** | `/api/rag` | `POST /query`, `GET /health` | Grounded retrieval with citation coordinates |
| **Knowledge Base** | `/api/knowledge` | `/overview`, `/offences`, `/punishments`, `/procedures`, `/evidence`, `/predecessors`, `/judgments`, `/acts` | Advanced BNS/BNSS/BSA & 24 Bare Acts knowledge retrieval |

---

## Current Standardization Boundaries & Next Steps

* **AI Assistant Frontend UI**: Backend service and endpoints are complete and tested (27/27 tests passed); frontend chat drawer widget is scheduled for implementation in Step 12.
* **Bare Acts Catalog UI**: 24 Acts JSON datasets and backend APIs are complete; dedicated frontend Acts explorer hub is scheduled for Step 12.
* **Phase 17 Database Live Ingestion**: Schema migration `009` and ingestion scripts are validated; PostgreSQL execution is scheduled for Step 11.
* **Complaint Generator, Voice Input & Lawyer Marketplace**: Documented as future capability additions in the Step 9 feature gap roadmap.
