# Vidhik Platform - Authority Recommendation Module

> **Notice:** Authority recommendations are limited to verified authority data available in the project.

---

## 1. Overview & Architecture

The **Authority Recommendation Module** provides deterministic, read-only judicial authority matching for the Vidhik legal platform. Given a user's legal query, specific statutory provision, or candidate sections retrieved from statutory search, the module identifies and recommends controlling judicial authorities exclusively when verified data exists in the project.

The processing pipeline is structured as follows:

```
User Legal Query / Statutory Input
                ↓
        LegalQueryService
                ↓
    LegalSearchService / LegalRankingService
                ↓
    Relevant Statutory Provisions
                ↓
AuthorityRecommendationService
                ↓
5-Tier Deterministic Matching Engine
                ↓
    Ranked Authority Recommendations
                ↓
FastAPI Response: GET /api/authorities/recommend
```

### Core Design Guarantees
- **Zero Hallucination / Zero Fabrication:** Never fabricates or infers judgments, case titles, citations, benches, courts, dates, or propositions.
- **Strict Read-Only:** All operations are strictly read-only (`SELECT` only); zero database modifications, zero table creation, and zero schema changes.
- **Search Pipeline Preservation:** Does not modify or replace `LegalSearchService` or `LegalRankingService`. Functions as an independent, testable analytical layer.
- **Dual-Mode High Availability:** Connects to PostgreSQL when available and seamlessly falls back to verified in-memory statutory knowledge graphs for zero-downtime retrieval.

---

## 2. Authority Data Sources

The module consumes verified data from the following authoritative project sources:

1. **Verified Landmark Decisions Corpus (`data/knowledge_base/verified_judgments.json`):**
   Contains curated, verified Supreme Court of India landmark decisions controlling criminal and evidence law provisions:
   - *Arjun Panditrao Khotkar v. Kailash Kushanrao Gorantyal and Others* ((2020) 7 SCC 1) — Controlling for BSA Section 63 & 57 (Electronic Records Admissibility).
   - *Satender Kumar Antil v. CBI and Another* ((2022) 10 SCC 51) — Controlling for BNSS Section 479 & 35 (Bail Guidelines, Mechanical Arrest Checks & Undertrial Release).
   - *Lalita Kumari v. Govt. of U.P. and Others* ((2014) 2 SCC 1) — Controlling for BNSS Section 173 (Mandatory FIR Registration & 14-day Preliminary Enquiry).
   - *Bachan Singh v. State of Punjab* ((1980) 2 SCC 684) — Controlling for BNS Section 103 & 4 (Rarest of Rare Doctrine in Murder Sentencing).
   - *Shafhi Mohammad v. State of H.P.* ((2018) 2 SCC 801) — Controlling for BNSS Section 105 (Mandatory Videography in Search & Seizure).

2. **24-Act Master Statutory Registry (`data/knowledge_base/phase17_24_acts_registry.json`):**
   Defines the statutory boundaries across all 24 Bare Acts. Acts 1–3 (BNS, BNSS, BSA) link to controlling precedents; Acts 4–24 explicitly designate `judgments_status: "NOT IN SOURCE"`.

3. **Relational PostgreSQL Schema (`database/migrations/008_advanced_legal_knowledge_base.sql`):**
   Tables: `judgments`, `judgment_laws`, `judgment_sections`.

---

## 3. Deterministic Matching Hierarchy

The recommendation engine adheres to a transparent, deterministic 5-tier scoring hierarchy:

| Tier | Matching Strategy | Relevance Score | Description |
| :--- | :--- | :---: | :--- |
| **Tier 1** | **Exact Section Mapping** | `1.00` | The requested or retrieved section has an explicit, verified statutory link to the judgment (e.g. BSA Sec 63 → *Arjun Panditrao Khotkar*). |
| **Tier 2** | **Law + Section Relationship** | `0.85` | The target provision belongs to the parent Act and shares a verified cross-reference or applied relationship. |
| **Tier 3** | **Legal Proposition Match** | `0.70` | The query explicitly matches a core legal doctrine or proposition (e.g. "rarest of rare", "mandatory FIR", "undertrial bail"). |
| **Tier 4** | **Legal Concept / Category Match** | `0.55` | The query matches verified high-level categories (e.g. "electronic evidence", "bail", "search videography"). |
| **Tier 5** | **Citation / Case Title Match** | `0.80 - 0.95` | The query explicitly contains a verified citation (e.g. `(2020) 7 SCC 1`) or party name. |

Every recommendation returned includes a human-readable `reason` identifying the exact tier and matching justification.

---

## 4. Verification Policy & "NOT IN SOURCE" Handling

- **Acts 1–3 (BNS, BNSS, BSA):** Verified Supreme Court decisions are linked to their statutory provisions and legal propositions.
- **Acts 4–24 (IT Act, POCSO, JJ Act, PWDVA, DPA, POSH, HMA, HSA, SMA, ICA, SRA, TPA, Registration Act, NI Act, CPA, MVA, RTI, LSAA, Arbitration Act, Companies Act, IBC):**
  When a query or statute filter targets one of these Acts (e.g. `law_id=17` or `q="cheque bounce"`):
  - The API returns:
    ```json
    {
      "source_status": "NOT IN SOURCE",
      "total": 0,
      "recommendations": []
    }
    ```
- **Irrelevant / Unknown Queries:**
  Non-legal queries or unknown terms return:
  ```json
  {
    "source_status": "NO MATCH",
    "total": 0,
    "recommendations": []
  }
  ```

---

## 5. API Specification

### Endpoint: `GET /api/authorities/recommend`

#### Query Parameters:
- `q` (*optional*, `str`): Search query or legal proposition.
- `law_id` (*optional*, `int`): Parent Law ID (e.g. 1 for BNS, 2 for BNSS, 3 for BSA, 17 for NI Act).
- `section_number` (*optional*, `str`): Statutory section number (e.g. `"63"`, `"103"`, `"173"`).
- `limit` (*optional*, `int`, default: `10`): Maximum recommendations to return.

#### Example Request 1: Exact Section Mapping (BSA Section 63)
```http
GET /api/authorities/recommend?section_number=63&law_id=3 HTTP/1.1
Host: 127.0.0.1:8000
```

#### Example Response 1:
```json
{
  "query": null,
  "law_id": 3,
  "section_number": "63",
  "total": 1,
  "source_status": "verified",
  "recommendations": [
    {
      "authority_id": 1,
      "case_name": "Arjun Panditrao Khotkar v. Kailash Kushanrao Gorantyal and Others",
      "court": "Supreme Court of India",
      "judgment_date": "2020-07-14",
      "citation": "(2020) 7 SCC 1",
      "legal_proposition": "Electronic Evidence - Production of Certificate under Section 65B(4) is mandatory condition precedent for secondary electronic records. When original hardware/device produced, primary evidence rules apply.",
      "linked_law_id": 3,
      "linked_law_name": "Bharatiya Sakshya Adhiniyam, 2023",
      "linked_section_number": "63",
      "matched_sections": [
        "Bharatiya Sakshya Adhiniyam, 2023 Section 63"
      ],
      "relevance_score": 1.0,
      "match_type": "exact_section_mapping",
      "reason": "Tier 1: Exact verified section-to-authority mapping for Section 63 of Bharatiya Sakshya Adhiniyam, 2023 (Authoritative interpretation settling the mandatory nature of electronic certificates for secondary computer outputs, codified in Section 63 BSA.)",
      "source": "Supreme Court of India Official Repository",
      "verification_status": "verified"
    }
  ],
  "statutory_results": []
}
```

#### Example Request 2: Unsupported Statute (NI Act Cheque Bounce)
```http
GET /api/authorities/recommend?q=cheque+bounce HTTP/1.1
Host: 127.0.0.1:8000
```

#### Example Response 2:
```json
{
  "query": "cheque bounce",
  "law_id": 17,
  "section_number": null,
  "total": 0,
  "source_status": "NOT IN SOURCE",
  "recommendations": [],
  "statutory_results": []
}
```

---

## 6. Limitations

1. **Verified Dataset Boundaries:** Recommendations are restricted to landmark decisions verified and included in the project corpus. Case law is not dynamically scraped, synthesized, or hallucinated.
2. **Statute Coverage:** Case-law mappings are currently available for the three core criminal enactments (BNS, BNSS, BSA). For the remaining 21 Acts, case law is transparently reported as `NOT IN SOURCE`.
3. **Read-Only Scope:** The module does not insert or alter legal database records.
