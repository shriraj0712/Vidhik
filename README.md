# VIDHIK AI — AI-Native Legal Intelligence Platform

**VIDHIK AI** is a unified, high-precision legal intelligence and workflow platform for Indian statutory law, integrating modern AI capabilities, comprehensive legal knowledge, hardened security, and a dual-role (Citizen & Advocate) workspace.

---

## Current Release

```text
VIDHIK AI v1.0.0
Standardized Full-Stack Baseline
Git Checkpoint: a8ef86e
```

---

## Architecture Overview

The standardized VIDHIK architecture unifies three primary functional layers into a cohesive full-stack system:

```text
VIDHIK AI v1.0
│
├── Full-Stack Web UI (Responsive Single-Page Application)
├── FastAPI REST Backend (12 Unified Routers, 78 Endpoints)
├── Authentication & Security (Bcrypt, Signed JWT, RBAC, Rate Limiter)
├── Citizen Workspace (Case Tracking, Document Vault, Procedural Checklists)
├── Lawyer Workspace (Client Management, Case Briefs, Confidential Notes)
├── Legal Document Analysis (PDF/DOCX Parsing, Entity Extraction, Risk Score)
├── Legal Search & Retrieval (Lexicon Tokenizer, Relevance Ranker, Snippets)
├── AI Legal Assistant Backend (Multi-turn Context, Turn Bounding, LLM Fallback)
├── Legal RAG Engine Backend (Grounded Retrieval, Citation Coordinates)
├── BNS / BNSS / BSA Legal Knowledge Layer (Provisions, Offence/Punishment Schemas)
├── 24 Indian Bare Acts Knowledge Base (3,252 Sections, Categorized Registries)
└── PostgreSQL Database (Thread-Safe Pool, Idempotent Migrations 001–009)
```

### Integrated Standardization Lineage:
* **Phase 15 (Security & AI/RAG)**: Bcrypt hashing, legacy SHA-256 upgrade detection, signed JWT session management, RBAC, sliding-window rate limiting, security headers, audit logging, conversational AI assistant, grounded RAG, and `OfflineMockLLMProvider` abstraction.
* **Phase 16 (Full-Stack Baseline)**: Canonical SPA frontend, dual Citizen and Lawyer workspaces, case lifecycle management, 25 citizen administrative and legal procedures in `legal_procedures`, document analysis pipeline, and multi-field legal search.
* **Phase 17 (Advanced Legal Knowledge)**: Bharatiya Nyaya Sanhita (BNS), Bharatiya Nagarik Suraksha Sanhita (BNSS), Bharatiya Sakshya Adhiniyam (BSA), repository of **24 Indian Bare Acts** (3,252 statutory sections), predecessor mappings (BNS ↔ IPC, BNSS ↔ CrPC, BSA ↔ IEA), verified Supreme Court judgments, and statutory criminal court procedures in `statutory_procedures`.

---

## v1.0 Feature Status

| Capability | Status in v1.0 | Implementation Evidence |
| :--- | :--- | :--- |
| **User Authentication & Security** | ✅ **Available / Integrated** | Bcrypt work factor 12, signed JWT, RBAC (`citizen`, `lawyer`, `admin`), security headers, sliding-window rate limiting, audit logging. |
| **Citizen Module** | ✅ **Available / Integrated** | Citizen dashboard, case tracking, document storage, hearing schedule, bookmarks, search history, in-app notifications, and procedural guides. |
| **Lawyer Module** | ✅ **Available / Integrated** | Advocate dashboard, client directory, case management, 6-tab case brief detail, document repository, court hearing scheduler, confidential case notes, profile. |
| **Case Tracking Dashboard** | ✅ **Available / Integrated** | End-to-end case tracking with hearing dates, timeline stages, legal status badges, and document attachments for both Citizens and Advocates. |
| **Legal Document Analyzer** | ✅ **Available / Integrated** | Upload drag-and-drop zone, raw text analysis, PDF (`pypdf`) and DOCX (`python-docx`) parsing, party/date extraction, clause risk scoring, and save-to-case. |
| **Legal Search & Retrieval** | ✅ **Available / Integrated** | Fast multi-field search over statutes, section numbers, titles, and descriptions with snippet extraction, jurisdiction filtering, and relevance ranking. |
| **Section & Act Identification** | ✅ **Available / Integrated** | Automated statutory extraction from queries, contracts, and legal drafts, with predecessor mapping (e.g. BNS Section 103 ↔ IPC Section 302). |
| **Personalized Legal History** | ✅ **Available / Integrated** | User-scoped search query history, bookmarked statutory provisions, and document analysis records with one-click re-search execution. |
| **In-App Notifications** | ✅ **Available / Integrated** | Real-time notification feed, unread badge counter, and read-state management. |
| **Full-Stack Web UI** | ✅ **Available / Integrated** | Responsive Single-Page Application (HTML5, CSS3, Vanilla JS) with 18 view panels and 12 interactive modal dialogs. |
| **Backend REST APIs** | ✅ **Available / Integrated** | 12 unified FastAPI routers exposing 78 functional API endpoints with zero method/path collisions and OpenAPI Swagger docs. |
| **AI Legal Assistant** | ⚠️ **Backend Available (UI Pending)** | Multi-turn conversational assistant with conversation turn bounding and citation preservation fully operational in backend; frontend chat drawer UI pending. |
| **Legal RAG Engine** | ⚠️ **Backend Available (UI Pending)** | Grounded retrieval and statutory citation synthesis fully tested in backend with `OfflineMockLLMProvider` fallback; chat UI pending. |
| **24 Bare Acts Knowledge Base** | ⚠️ **Data & API Available (UI Pending)** | 24 structured JSON Bare Acts (3,252 sections), registry, and `/api/knowledge/acts` endpoints available; dedicated Bare Acts browsing hub pending. |
| **BNS / BNSS / BSA Knowledge** | ⚠️ **Data & API Available (Ingestion Pending)** | BNS, BNSS, BSA datasets, schemas, and 11 `/api/knowledge/*` endpoints built; PostgreSQL migration `009` and ingestion script ready for v1.1 execution. |
| **Authority Recommendation** | ⚠️ **Procedural Mapping Available** | Deterministic competent authority and official portal mapping integrated for 25 citizen procedures; dynamic ML recommendation engine planned. |
| **Constitutional Rights Mapping** | ⚠️ **Dataset Available (UI Pending)** | Structured Indian Constitution dataset (Articles 1–395) and NLP query recognition available; dedicated Rights Explorer UI planned. |
| **Multilingual Support** | ⚠️ **Backend NLP Available (UI i18n Planned)**| Query normalization and prompt handling support Marathi and Hindi; full dynamic UI localization planned. |
| **Lawyer Marketplace** | 📋 **Planned** | Advocate client management exists; public directory search and direct citizen booking planned for v1.3. |
| **Complaint Generator** | 📋 **Planned** | Procedural checklists exist; automated dynamic FIR / consumer grievance drafting engine planned for v1.3. |
| **Voice & Speech Input** | 📋 **Planned** | Text inputs supported throughout all panels; Web Speech API and backend audio transcription planned for v1.4. |
| **Traffic Fine Calculator** | 📋 **Planned** | Motor Vehicles Act data and challan contest guides available; dedicated interactive fine calculator planned for later roadmap. |
| **External Reminders** | 📋 **Planned** | In-app notifications functional; scheduled external SMS/email cron reminders planned for later roadmap. |

---

## 24 Indian Bare Acts Knowledge Base

The repository includes a curated, machine-readable repository of **24 Indian Bare Acts** comprising **3,252 statutory sections**:

```text
data/knowledge_base/acts/
├── act_01_bns.json                    # Bharatiya Nyaya Sanhita, 2023 (362 sections)
├── act_02_bnss.json                   # Bharatiya Nagarik Suraksha Sanhita, 2023 (531 sections)
├── act_03_bsa.json                    # Bharatiya Sakshya Adhiniyam, 2023 (170 sections)
├── act_04_cpc.json                    # Code of Civil Procedure, 1908 (158 sections)
├── act_05_constitution.json           # Constitution of India (395 articles)
├── act_06_contract_act.json           # Indian Contract Act, 1872 (238 sections)
├── act_07_specific_relief.json        # Specific Relief Act, 1963 (44 sections)
├── act_08_transfer_of_property.json   # Transfer of Property Act, 1882 (137 sections)
├── act_09_arbitration.json            # Arbitration and Conciliation Act, 1996 (86 sections)
├── act_10_commercial_courts.json      # Commercial Courts Act, 2015 (23 sections)
├── act_11_negotiable_instruments.json # Negotiable Instruments Act, 1881 (147 sections)
├── act_12_consumer_protection.json    # Consumer Protection Act, 2019 (107 sections)
├── act_13_motor_vehicles_act.json     # Motor Vehicles Act, 1988 (217 sections)
├── act_14_it_act.json                 # Information Technology Act, 2000 (94 sections)
├── act_15_dpdp_act.json               # Digital Personal Data Protection Act, 2023 (44 sections)
├── act_16_hindu_marriage_act.json     # Hindu Marriage Act, 1955 (30 sections)
├── act_17_special_marriage_act.json   # Special Marriage Act, 1954 (51 sections)
├── act_18_dv_act.json                 # Protection of Women from Domestic Violence Act, 2005 (37 sections)
├── act_19_posh_act.json               # POSH Act, 2013 (30 sections)
├── act_20_industrial_disputes.json    # Industrial Disputes Act, 1947 (40 sections)
├── act_21_companies_act.json          # Companies Act, 2013 (470 sections)
├── act_22_epf_act.json                # EPF & Miscellaneous Provisions Act, 1952 (22 sections)
├── act_23_maternity_benefit.json      # Maternity Benefit Act, 1961 (30 sections)
└── act_24_environment_protection.json # Environment (Protection) Act, 1986 (26 sections)
```

> **Important Boundary Clarification**:
> * **Dataset Availability ≠ Live Database Ingestion**: The 24 Bare Act JSON files and verification scripts are validated. Ingesting all 3,252 sections into the PostgreSQL database is scheduled for **v1.1**.
> * **API Availability ≠ Dedicated Frontend Catalog**: Backend knowledge retrieval endpoints (`/api/knowledge/acts`) are registered. A dedicated Bare Acts browsing hub on the frontend is scheduled for **v1.2**.

---

## BNS / BNSS / BSA Legal Knowledge Layer

VIDHIK integrates the complete transformed criminal law framework of India:
* **Bharatiya Nyaya Sanhita, 2023 (BNS)**: Offence provisions, punishment scales, classifications, and predecessor mappings replacing the Indian Penal Code, 1860.
* **Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)**: Procedural timeline mandates, investigation protocols, and arrest safeguards replacing the Code of Criminal Procedure, 1973.
* **Bharatiya Sakshya Adhiniyam, 2023 (BSA)**: Electronic records admissibility, secondary evidence provisions, and forensic rules replacing the Indian Evidence Act, 1872.
* **Predecessor Mappings**: 22 mapped transitions (BNS ↔ IPC, BNSS ↔ CrPC, BSA ↔ IEA).
* **Verified Supreme Court Judgments**: 5 landmark precedents linked directly to corresponding statutory sections.
* **Database Migration**: Schema definitions provided in `database/migrations/009_advanced_legal_knowledge_base.sql`.

---

## Security & Governance

VIDHIK implements a multi-tiered security and authentication architecture:
1. **Password Hashing**: Modern `bcrypt` with work factor 12 and salt generation.
2. **Transparent Legacy Upgrade**: Automatic detection of legacy `SHA-256` password hashes upon successful login with seamless database re-hashing to bcrypt.
3. **Cryptographic JWT Sessions**: RFC 7519 signed JSON Web Tokens (`HS256`) containing explicit user identity, role, lawyer association, and expiration claims.
4. **Role-Based Access Control (RBAC)**: Enforced endpoint dependencies (`require_citizen`, `require_lawyer`, `require_admin`).
5. **Security Middleware**:
   - `SecurityHeadersMiddleware`: Enforces `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`, and `Content-Security-Policy`.
   - `RateLimiterMiddleware`: IP-based and token-bucket sliding-window rate limiter protecting sensitive authentication and analysis endpoints.
   - `CORSMiddleware`: Strict origin whitelisting.
6. **Audit Trail**: `AuditService` logging authentication events, password updates, and session revocations.

---

## Project Directory Structure

```text
Vidhik/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── security.py           # Bcrypt hashing, SHA-256 migration, signed JWT
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── rate_limiter.py       # Sliding-window rate limiter
│   │   │   └── security_headers.py   # HSTS, CSP, XSS protection headers
│   │   ├── models/                   # Dataclass entity models
│   │   ├── routers/                  # 12 unified FastAPI routers (78 endpoints)
│   │   │   ├── __init__.py
│   │   │   ├── health.py             # GET /health
│   │   │   ├── laws.py               # GET /api/laws/{law_id}
│   │   │   ├── sections.py           # GET /api/sections/{section_id}
│   │   │   ├── search.py             # GET /api/search
│   │   │   ├── auth.py               # /api/auth (register, login, me, logout)
│   │   │   ├── citizen.py            # /api/citizen (cases, documents, bookmarks, etc.)
│   │   │   ├── lawyer.py             # /api/lawyer (clients, cases, notes, etc.)
│   │   │   ├── documentation.py      # /api/documentation (procedures, checklists)
│   │   │   ├── document_analysis.py  # /api/analysis (upload, text, history)
│   │   │   ├── assistant.py          # /api/assistant (chat, health)
│   │   │   ├── rag.py                # /api/rag (query, health)
│   │   │   └── knowledge_base.py     # /api/knowledge (overview, acts, offences, etc.)
│   │   ├── schemas/                  # Pydantic request/response models
│   │   ├── services/                 # Business logic, AI, RAG, search, knowledge services
│   │   ├── static/                   # Production Single-Page Application (index.html, app.js, styles.css)
│   │   ├── database.py               # Threaded PostgreSQL connection pool
│   │   └── main.py                   # FastAPI entry point & middleware registration
│   ├── tests/                        # Automated test suite (27 passing tests)
│   ├── requirements.txt              # Production Python dependencies
│   └── .env.example                  # Environment configuration template
├── data/
│   └── knowledge_base/               # 24 Bare Acts JSONs, BNS/BNSS/BSA, predecessor mappings
├── database/
│   └── migrations/                   # SQL migrations (001, 002, 006, 007, 008, 009)
└── scripts/                          # Knowledge compilation and verification tools
```

---

## Database Architecture & Migration Safety

VIDHIK uses PostgreSQL with sequential, idempotent SQL migrations in `database/migrations/`:

```text
001_mvp_legal_staging_schema.sql         # Laws, sections, legal lexicon, section alignments
002_mvp_legal_staging_schema_safe.sql    # Idempotent staging schema verification
006_document_analysis_schema.sql         # Document analysis records & legal references
007_citizen_user_module_schema.sql       # User profiles, cases, documents, bookmarks, notifications
008_expand_legal_procedures_phase12.sql  # 25 citizen administrative procedural guides
009_advanced_legal_knowledge_base.sql    # Statutory procedures, offences, punishments, evidence, judgments
```

### Critical Separation Guarantee:
* **`legal_procedures` (Phase 16)**: Preserves the 25 citizen-facing administrative guides, citizen checklists, and document prerequisite trackers.
* **`statutory_procedures` (Phase 17)**: Isolated table in migration `009` dedicated to statutory BNSS criminal court and trial procedure steps.
* *Note*: Migration `009` is verified and prepared for live execution in **v1.1**.

---

## Installation & Quickstart

### 1. Prerequisites
* **Python 3.10+** (Tested on Python 3.14)
* **PostgreSQL 14+** running with database `vidhik_db`

### 2. Configure Environment
```bash
cd backend
cp .env.example .env
```
Edit `backend/.env` to configure your database connection and optional LLM API keys:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=vidhik_db
DB_USER=postgres
DB_PASSWORD=your_postgres_password

# Security & JWT
JWT_SECRET_KEY=your-secure-random-jwt-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# AI / LLM Provider ('mock', 'gemini', or 'openai')
LLM_PROVIDER=mock
GEMINI_API_KEY=
OPENAI_API_KEY=
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
From the `backend` directory:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Or using python module syntax:
```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 5. Access the Platform
* **Full-Stack Web SPA**: `http://127.0.0.1:8000/`
* **Citizen Portal**: `http://127.0.0.1:8000/citizen`
* **Lawyer Portal**: `http://127.0.0.1:8000/lawyer`
* **Interactive API Documentation (Swagger)**: `http://127.0.0.1:8000/docs`
* **ReDoc Documentation**: `http://127.0.0.1:8000/redoc`
* **Health Probe**: `http://127.0.0.1:8000/health`

---

## Testing & Verification

Run the automated backend test suite from the repository root:
```bash
pytest backend/tests -v
```

Run complete Python compilation across all backend packages:
```bash
python -m compileall backend
```

*Current Verified Baseline*: **27 of 27 tests passing** (100% pass rate) with 0 compilation errors.

---

## Current Limitations

In accordance with the v1.0 architecture audit, the following limitations are explicitly noted:
1. **AI Legal Assistant UI**: Backend `/api/assistant/chat` and RAG services are fully tested; interactive frontend chat drawer UI is pending.
2. **24 Bare Acts Catalog UI**: All 24 Acts datasets and backend APIs are complete; dedicated frontend catalog view is pending.
3. **Phase 17 Live Database Ingestion**: Migration `009` and ingestion scripts are verified; live ingestion into PostgreSQL is scheduled for v1.1.
4. **Complaint Generator**: Automated template drafting engine (FIR / consumer grievance generator) is not yet implemented.
5. **Voice Input**: Web Speech API recording and backend speech-to-text audio transcription are not yet implemented.
6. **Public Lawyer Marketplace**: Advocate practice management is complete; public search directory and client booking are planned.
7. **Multilingual UI Localization**: NLP query understanding supports Marathi/Hindi; dynamic interface translation (i18n) is planned.
8. **Constitutional Rights Hub**: Structured dataset (Articles 1–395) exists; dedicated rights exploration hub is planned.
9. **Traffic Fine Calculator**: Motor Vehicles Act data exists; interactive fine calculator is planned.
10. **External Scheduled Reminders**: In-app notifications are operational; background SMS/email cron reminders are planned.

---

## Roadmap After v1.0

The planned development sequence for upcoming releases:

* **v1.1 — Database Migration & Knowledge Ingestion**:
  Execute migration `009_advanced_legal_knowledge_base.sql` and run `ingest_phase17_24_acts.py` to make all 3,252 sections and criminal provisions live in PostgreSQL.
* **v1.2 — AI Assistant & Bare Acts UI Integration**:
  Mount the interactive AI Legal Assistant chat drawer and the 24 Bare Acts catalog browser into the SPA frontend.
* **v1.3 — Lawyer Marketplace & Complaint Generator**:
  Implement the public advocate discovery directory and automated legal complaint/FIR template generator.
* **v1.4 — Multilingual UI & Voice Input**:
  Integrate Web Speech audio input and full dynamic UI localization (English, Hindi, Marathi).
* **Future Enhancements**:
  Dedicated Constitutional Rights visualization hub, interactive traffic fine calculator, and background SMS/Email reminder scheduler.

---

## Responsible Use & Legal Disclaimer

> **IMPORTANT NOTICE**:
> **VIDHIK AI is an automated legal information, intelligence, and workflow assistance tool.**
>
> * VIDHIK provides legal information and research capabilities based on Indian statutory law and public legal data.
> * **VIDHIK DOES NOT PROVIDE FORMAL LEGAL ADVICE.** Nothing in this software constitutes legal counsel, statutory certification, or a substitute for consultation with a qualified Advocate or legal practitioner.
> * Users, citizens, and legal professionals must independently verify statutory provisions, section applicability, and court procedures with official government gazettes and competent authorities.
> * AI-generated outputs, summaries, and risk assessments are informational assistance tools and must be reviewed by qualified human advocates before being relied upon in legal proceedings.
