# Vidhik Legal Platform - Legal Dataset Batch Ingestion Dry-Run Report

## 1. Dry-Run Execution Summary

| Parameter | Value |
| :--- | :--- |
| **Execution Mode** | **DRY RUN (Simulation Only - ZERO Database Modifications)** |
| **Target Database** | `vidhik_db` on `localhost:5432` |
| **Ingestion Script** | [`scripts/ingest_legal_staging.py`](file:///c:/Users/aditi/Desktop/Capstone/Vidhik/scripts/ingest_legal_staging.py) |
| **Source Datasets Staged** | 128 Laws, 10,248 Sections, 42 Lexicon Terms, 10,248 Alignments |
| **Execution Timestamp** | `2026-09-13T23:06:16` |
| **Transaction Status** | **Rolled Back (Zero DB Rows Inserted, Modified, or Dropped)** |

---

## 2. Pre-Ingestion Database Row Counts vs. Ingestion Plan

| Table Name | Pre-Ingestion DB Rows | Planned Inserts (New) | Planned Updates (Existing) | Planned Total MVP Rows | Post-Ingestion Expected Total |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `laws` | `852` | `17` | `111` | `128` | **869** (`852 + 17`) |
| `sections` | `39,245` | `2,289` | `7,959` | `10,248` | **41,534** (`39,245 + 2,289`) |
| `legal_lexicon` | `0` | `42` | `0` | `42` | **42** |
| `section_alignments`| `0` | `10,248` | `0` | `10,248` | **10,248** |

---

## 3. Detailed Step-by-Step Simulation Results

### Step 1: Laws (`laws` table)
* **111 Existing Laws Matched**: Matched by exact `law_name` from prior baseline imports. Ingestion safely updates staging telemetry (`law_slug`, `year`, `law_type`, `jurisdiction`, `source_pdf`, `total_pages`, `enactment_start_page`, `total_sections_extracted`, `is_diglot`, `extraction_status`, `parser_notes`) without altering `law_id`.
* **17 New Laws**: Inserted with new `BIGSERIAL` `law_id`.
* **Laws Foreign Key Validation Errors**: **0**.

### Step 2: Sections (`sections` table)
* **7,959 Existing Sections Matched**: Matched by `(law_id, section_number)` against existing database rows. Ingestion safely enriches existing sections with `section_uid`, verified `full_text`, structural counts (`subsections_count`, `clauses_count`), provenance (`source_pdf`, `source_page_start`), and `text_sha256` without modifying existing `section_id`.
* **2,289 New Sections**: Inserted for newly segmented state acts, newly added acts, and alphanumeric provisions (`73A`, `154B`, `IV`).
* **Sections Foreign Key Validation Errors**: **0**.
* **Omitted / Repealed Sections Tracked**: **441** provisions marked with `is_omitted = TRUE` and explicit omission notes.

### Step 3: Legal Lexicon (`legal_lexicon` table)
* **42 Controlled Terms**: Inserted across 7 categories (`statutory_structure`, `court_and_procedure`, `penal_and_offences`, `governance_and_authorities`, `revenue_and_property`, `commercial_and_cooperatives`, `commercial_and_contracts`).
* **Duplicate Terms Detected**: **0**.

### Step 4: Section Alignments (`section_alignments` table)
* **10,248 Alignments Processed**: 100% 1-to-1 foreign key resolution to `sections(section_id)` and `laws(law_id)`.
* **SHA-256 Digest Mismatches**: **0** (100% cryptographic parity with `sections_staging.json`).
* **Manual Review Tracked Records**: **9,869** non-standard section titles tracked for human domain review; **379** standardized titles aligned in Marathi and Hindi; **1,065** official diglot Hindi gazette sections linked.

---

## 4. Integrity & Validation Gate Summary

| Validation Check | Simulation Result | Status |
| :--- | :---: | :---: |
| **Law Foreign Key Resolution** | 0 missing parent laws | **PASSED** |
| **Section Foreign Key Resolution** | 0 missing parent sections | **PASSED** |
| **SHA-256 Digest Consistency** | 0 text mismatches | **PASSED** |
| **Lexicon Term ID Uniqueness** | 0 duplicate keys | **PASSED** |
| **Database State Preservation** | 0 rows modified or inserted | **CONFIRMED** |
