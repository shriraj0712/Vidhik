# Vidhik Platform - Backend API Service

FastAPI-powered REST backend for the **Vidhik Legal Platform**, providing low-latency, read-only query capabilities over Indian statutory laws, statutory sections, legal lexicon, and constitutional provisions stored in PostgreSQL (`vidhik_db`).

---

## 1. Directory Structure

```text
backend/
├── app/
│   ├── __init__.py           # Package versioning
│   ├── main.py               # FastAPI application entry point, CORS, lifespan
│   ├── database.py           # Thread-safe PostgreSQL connection pool (psycopg2)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── law.py            # Dataclass model representing the laws table
│   │   └── section.py        # Dataclass model representing the sections table
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── law.py            # Pydantic response schemas (LawResponse, LawListResponse)
│   │   ├── section.py        # Pydantic response schemas (SectionResponse, SectionListResponse)
│   │   ├── search.py         # Pydantic response schemas (SearchResponse, SearchResultItem)
│   │   └── query.py          # Pydantic models for LegalQueryAnalysis & Lexicon Matching
│   ├── services/
│   │   ├── __init__.py
│   │   ├── search_service.py # Dedicated service layer for legal search logic
│   │   └── query_service.py  # Legal query understanding & terminology expansion service
│   └── routers/
│       ├── __init__.py
│       ├── health.py         # GET /health service and DB ping endpoint
│       ├── laws.py           # GET /api/laws and GET /api/laws/{law_id} endpoints
│       ├── sections.py       # GET /api/sections and GET /api/sections/{section_id} endpoints
│       └── search.py         # GET /api/search multi-field legal search endpoint
├── .env.example              # Environment variables template
├── .env                      # Local environment configuration (ignored in git)
├── requirements.txt          # Python dependencies
└── README.md                 # Backend documentation
```

---

## 2. Prerequisites

* **Python 3.10+** (Tested on Python 3.14)
* **PostgreSQL 14+** running with the existing `vidhik_db` database
* Network access to `localhost:5432`

---

## 3. Setup & Installation

### Step 1: Navigate to the Backend Directory
```bash
cd backend
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env` and adjust credentials if needed:
```bash
cp .env.example .env
```

Environment variables supported in `.env`:
```env
# Database Credentials
DB_HOST=localhost
DB_PORT=5432
DB_NAME=vidhik_db
DB_USER=postgres
DB_PASSWORD=your_secure_password_here

# Connection Pool Settings
DB_MIN_CONN=1
DB_MAX_CONN=10

# Server Settings
APP_HOST=127.0.0.1
APP_PORT=8000
APP_ENV=development
DEBUG=True

# CORS Settings (comma-separated origins)
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 4. Running the Backend Server

### Option A: Using Uvicorn CLI (Recommended for Development)
```bash
# From inside the backend directory:
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Option B: Using Python Module Runner
```bash
# From inside the backend directory:
python -m app.main
```

The server will be available at:
* **Base URL**: `http://127.0.0.1:8000`
* **Swagger Interactive UI**: `http://127.0.0.1:8000/docs`
* **ReDoc Documentation**: `http://127.0.0.1:8000/redoc`

---

## 5. Available API Endpoints

### 1. Root Information
* **Endpoint:** `GET /`
* **Description:** Returns API platform metadata and available routes.

### 2. Health Check
* **Endpoint:** `GET /health`
* **Description:** Pings the PostgreSQL database and returns service and database connection status.
* **Sample Response:**
```json
{
  "status": "healthy",
  "service": "Vidhik Legal Platform API",
  "version": "1.0.0",
  "timestamp": "2026-09-15T14:35:00.000000Z",
  "database": {
    "status": "connected",
    "database": "vidhik_db",
    "version": "PostgreSQL 18.1"
  }
}
```

### 3. List Laws (Paginated & Filterable)
* **Endpoint:** `GET /api/laws`
* **Query Parameters:**
  * `limit` (int, default=20, max=100): Maximum records to retrieve.
  * `offset` (int, default=0): Number of records to skip.
  * `jurisdiction` (string, optional): Filter by jurisdiction (e.g. `India`, `Maharashtra`).
  * `search` (string, optional): Search by law name or slug.

### 4. Get Law by ID
* **Endpoint:** `GET /api/laws/{law_id}`
* **Path Parameter:** `law_id` (integer)
* **Description:** Returns complete record metadata for a single law.

### 5. List Sections (Paginated & Filterable)
* **Endpoint:** `GET /api/sections`
* **Query Parameters:**
  * `limit` (int, default=20, max=100): Maximum records to retrieve.
  * `offset` (int, default=0): Number of records to skip.
  * `law_id` (int, optional): Filter sections by parent statutory law ID.
  * `section_number` (string, optional): Filter by exact or partial section number (e.g. `144`, `302`, `10A`).
  * `section_title` (string, optional): Search keyword matching section title.
* **Sample Request:**
  `GET http://127.0.0.1:8000/api/sections?limit=5&law_id=1178`
* **Sample Response:**
```json
{
  "total": 1,
  "limit": 5,
  "offset": 0,
  "sections": [
    {
      "section_id": 1,
      "law_id": 1178,
      "section_number": "1",
      "section_title": "Extending Acts 24,1841 and 17,1843 to Straits Settlements.",
      "section_uid": null,
      "chapter_number": null,
      "chapter_title": null,
      "source_pdf": null,
      "source_page_start": null,
      "source_page_end": null,
      "page_start": null,
      "page_end": null,
      "manual_review_required": false,
      "is_omitted": false
    }
  ]
}
```

### 6. Get Section by ID
* **Endpoint:** `GET /api/sections/{section_id}`
* **Path Parameter:** `section_id` (integer)
* **Description:** Returns full section record including statutory text (`full_text`/`section_text`), structural counts, chapter/part hierarchy, and PDF coordinates.

### 7. Search Legal Corpus (Multi-Field Relational ILIKE Search)
* **Endpoint:** `GET /api/search`
* **Query Parameters:**
  * `q` (string, required): Search query text matching law name, short name, section number, section title, description, or full text.
  * `limit` (int, default=10, max=50): Maximum search results to return (1-50).
  * `offset` (int, default=0): Number of records to skip.
  * `law_id` (int, optional, >0): Filter search results by parent statute ID.
  * `jurisdiction` (string, optional): Filter search results by jurisdiction (e.g. `India`, `Maharashtra`).
* **Sample Request:**
  `GET http://127.0.0.1:8000/api/search?q=contract&limit=5`
* **Sample Response:**
```json
{
  "query": "contract",
  "total": 315,
  "limit": 5,
  "offset": 0,
  "results": [
    {
      "law_id": 14,
      "law_name": "The Air (Prevention and Control of Pollution) Act, 1981",
      "section_id": 566,
      "section_number": "5",
      "section_title": "Constitution of State Boards.",
      "snippet": "... of this Act, to acquire and dispose of property and to contract, and may by the said name sue or be sued.",
      "jurisdiction": "Central",
      "source_pdf": "A1981-14.pdf",
      "source_page_start": 3,
      "source_page_end": 4,
      "manual_review_required": false
    }
  ]
}
```

---

## 6. Architectural & Security Guarantees

1. **No Hardcoded Passwords**: All credentials and connection strings are read securely from `.env` via `python-dotenv`.
2. **Read-Only Database Operations**: Endpoints perform only parameterized `SELECT` queries. No `INSERT`, `UPDATE`, `DELETE`, `DROP`, or schema modification can be executed via the API.
3. **Connection Pooling**: Uses `psycopg2.pool.ThreadedConnectionPool` to manage database connections efficiently across concurrent requests.
4. **SQL Injection Protection**: All database queries use parameterized SQL tuples (`%s` placeholders).

