# Vidhik Platform - Backend API Service

FastAPI-powered REST backend for the **Vidhik Legal Platform**, providing unified legal research, citizen & lawyer workspaces, hardened JWT/bcrypt authentication, conversational AI assistance, grounded RAG, and an advanced legal knowledge base over Indian statutory laws stored in PostgreSQL (`vidhik_db`).

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
│   ├── static/               # Production Single-Page Application (index.html, app.js, styles.css)
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
├── requirements.txt          # Production Python dependencies
└── README.md                 # Backend documentation
```

---

## 2. Prerequisites & Setup

* **Python 3.10+** (Tested on Python 3.14)
* **PostgreSQL 14+** running with database `vidhik_db`

### Step 1: Navigate to Backend Directory
```bash
cd backend
```

### Step 2: Configure Environment
```bash
cp .env.example .env
```
Edit `.env` to configure your PostgreSQL credentials and optional LLM keys:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=vidhik_db
DB_USER=postgres
DB_PASSWORD=your_password_here

# Security & JWT
JWT_SECRET_KEY=change-me-in-production-use-a-strong-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# Rate Limiter
RATE_LIMIT_REQUESTS_PER_MINUTE=60

# AI Provider ('mock', 'gemini', or 'openai')
LLM_PROVIDER=mock
GEMINI_API_KEY=
OPENAI_API_KEY=
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 3. Running the Server

From inside the `backend` directory:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Or using python module runner:
```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Available Documentation URLs:
* **Interactive Swagger UI**: `http://127.0.0.1:8000/docs`
* **ReDoc Documentation**: `http://127.0.0.1:8000/redoc`
* **Single-Page Application**: `http://127.0.0.1:8000/`

---

## 4. Standardized API Modules (12 Routers)

1. **Health (`/health`)**: System status and PostgreSQL connectivity probe.
2. **Laws (`/api/laws`)**: Central and State statutory law inspection.
3. **Sections (`/api/sections`)**: Statutory section retrieval and hierarchy.
4. **Search (`/api/search`)**: Fast multi-field legal search with snippet extraction.
5. **Authentication (`/api/auth`)**: JWT/bcrypt registration, login, session inspection (`/me`), and logout.
6. **Citizen Module (`/api/citizen`)**: Dashboard metrics, case management, document vault, hearing calendar, bookmarks, search history, in-app notifications, and procedural trackers.
7. **Lawyer Module (`/api/lawyer`)**: Advocate dashboard, client directory, case management, 6-tab case brief detail, document repository, court hearing scheduler, confidential case notes, profile.
8. **Documentation (`/api/documentation`)**: 25 authoritative citizen procedural guides, categories, and checklists.
9. **Document Analysis (`/api/analysis`)**: PDF/DOCX contract parsing, party and date extraction, clause risk scoring, and case attachment.
10. **AI Legal Assistant (`/api/assistant`)**: Multi-turn conversational legal assistant with conversation turn bounding and citation preservation.
11. **Legal RAG Engine (`/api/rag`)**: Grounded statutory retrieval and citation synthesis.
12. **Knowledge Base (`/api/knowledge`)**: Advanced BNS/BNSS/BSA and 24 Bare Acts knowledge retrieval APIs.

---

## 5. Testing & Compilation

Run the test suite from the project root:
```bash
pytest backend/tests -v
```

Run Python compilation across all backend packages:
```bash
python -m compileall backend
```

*Current Verified Baseline*: **27/27 tests passing** with 0 compilation errors.

---

## 6. Security Guarantees

* **Password Hashing**: Bcrypt with work factor 12.
* **Legacy Migration**: Transparent SHA-256 detection and re-hashing.
* **JWT Tokens**: RFC 7519 signed JSON Web Tokens (`HS256`).
* **RBAC**: Enforced role dependencies (`require_citizen`, `require_lawyer`, `require_admin`).
* **Middleware Pipeline**: `SecurityHeadersMiddleware`, `RateLimiterMiddleware`, and `CORSMiddleware`.
* **Audit Logging**: `AuditService` logging auth attempts and security events.
