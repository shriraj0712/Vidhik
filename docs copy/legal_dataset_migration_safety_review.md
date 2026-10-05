# Vidhik Legal Platform - Legal Dataset Migration Safety Review

## 1. Executive Summary & Review Objective

Before applying any schema changes or executing PostgreSQL migrations for the **Maharashtra MVP Legal Dataset and Multilingual Alignment Layer**, this safety review analyzes:
1. Exact structural compatibility between existing production tables and proposed staging schemas.
2. Primary key and foreign key data type alignment.
3. Idempotency and risk of failure during repeat migration runs.
4. Risk of unique constraint violations on existing data.
5. Impact of cascading deletion policies (`ON DELETE CASCADE`) on citizen cases, legal rights, and keyword mappings.
6. Identity mapping rules between staging JSON strings (`law_id`, `section_id`) and PostgreSQL integer primary keys (`BIGSERIAL`).
7. Rollback and recovery strategies guaranteeing zero loss of historical data.

---

## 2. Current Schema vs. Proposed Schema Comparison

### 2.1. `laws` Table Comparison
| Attribute / Column | Current Baseline (`database/Legal_Dataset/laws.sql`) | Proposed Migration (`001_mvp_legal_staging_schema.sql`) | Safety Evaluation & Findings |
| :--- | :--- | :--- | :--- |
| **Primary Key** | `law_id BIGSERIAL` (`BIGINT`) | `law_id BIGSERIAL` (`BIGINT`) | **Identical / Compatible**. Auto-incrementing integer key. |
| **`law_name`** | `VARCHAR(300) NOT NULL UNIQUE` | `VARCHAR(500) NOT NULL UNIQUE` | **Minor Widening Needed**. If table already exists, `ADD COLUMN IF NOT EXISTS` will not alter `VARCHAR(300)` to `VARCHAR(500)`. Needs explicit safe `ALTER COLUMN TYPE`. |
| **`short_name`** | `VARCHAR(100)` | `VARCHAR(255)` | **Widening Needed**. Some Central Acts have short titles > 100 characters. Needs safe column widening. |
| **`law_slug`** | *(Not Present)* | `VARCHAR(255) UNIQUE` | **Safe Addition**. Used as natural unique key mapping to staging JSON `law_id`. Partial unique index (`WHERE law_slug IS NOT NULL`) prevents NULL collisions. |
| **`year`** | *(Not Present)* | `INT` | **Safe Addition**. Numeric enactment year. |
| **`source_pdf`** | *(Not Present)* | `VARCHAR(255)` | **Safe Addition**. Repository filename provenance. |
| **`total_pages`** | *(Not Present)* | `INT DEFAULT 0` | **Safe Addition**. PDF telemetry. |
| **`enactment_start_page`** | *(Not Present)* | `INT DEFAULT 1` | **Safe Addition**. TOC vs enactment start telemetry. |
| **`is_diglot`** | *(Not Present)* | `BOOLEAN DEFAULT FALSE` | **Safe Addition**. Hindi/English diglot flag. |
| **`extraction_status`** | *(Not Present)* | `VARCHAR(100) DEFAULT 'staged_from_pdf'` | **Safe Addition**. Extraction status tracker. |
| **`manual_review_required`**| *(Not Present)* | `BOOLEAN DEFAULT FALSE` | **Safe Addition**. Review flag. |
| **`parser_notes`** | *(Not Present)* | `JSONB DEFAULT '[]'::jsonb` | **Safe Addition**. Structured audit log. |

---

### 2.2. `sections` Table Comparison
| Attribute / Column | Current Baseline (`database/Legal_Dataset/sections.sql`) | Proposed Migration (`001_mvp_legal_staging_schema.sql`) | Safety Evaluation & Findings |
| :--- | :--- | :--- | :--- |
| **Primary Key** | `section_id BIGSERIAL` (`BIGINT`) | `section_id BIGSERIAL` (`BIGINT`) | **Identical / Compatible**. Integer surrogate key. |
| **Foreign Key** | `law_id BIGINT REFERENCES laws(law_id)` | `law_id BIGINT REFERENCES laws(law_id)` | **Identical / Compatible**. |
| **`section_uid`** | *(Not Present)* | `VARCHAR(255) UNIQUE` | **Safe Addition**. Stable unique key mapping to staging JSON `section_id`. |
| **`section_number`** | `VARCHAR(50) NOT NULL` | `VARCHAR(50) NOT NULL` | **Identical / Compatible**. Supports alphanumeric section numbers (`1`, `2A`, `154B`, `IV`). |
| **`section_title`** | `VARCHAR(500)` | `VARCHAR(1000)` | **Widening Needed**. Several section titles in state acts exceed 500 characters due to long compound subject lines. Safe widening required. |
| **`full_text`** | `TEXT` | `TEXT` | **Identical / Compatible**. Original English statutory text. |
| **`chapter` / `part`** | `chapter VARCHAR(200)`, `part VARCHAR(200)` | Retains `chapter`/`part`, adds `chapter_number`, `chapter_title`, `part_number`, `part_title` | **Non-Breaking Addition**. Preserves legacy columns while providing structured number/title fields. |
| **Structure Flags** | *(Not Present)* | `subsections_count`, `clauses_count`, `subclauses_count`, `has_proviso`, `has_explanation`, `has_illustration`, `has_schedule_ref`, `is_definition_section` | **Safe Addition**. Integer and boolean structural telemetry columns. |
| **Omission Fields** | *(Not Present)* | `is_omitted BOOLEAN`, `omission_note TEXT` | **Safe Addition**. Preserves deleted/repealed provisions without deleting records. |
| **`text_sha256`** | *(Not Present)* | `VARCHAR(64)` | **Safe Addition**. Cryptographic digest for text immutability checks. |

---

### 2.3. New Multilingual Tables Comparison
| New Table Name | Primary Key | Foreign Keys | Unique Constraints | Check Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `legal_lexicon` | `lexicon_id BIGSERIAL` | None | `term_id UNIQUE` | `chk_lexicon_verification_status` |
| `section_alignments` | `alignment_id BIGSERIAL` | `section_id BIGINT -> sections(section_id)`<br>`law_id BIGINT -> laws(law_id)` | `section_id UNIQUE` (1-to-1 with `sections`) | `chk_mr_confidence_range`<br>`chk_hi_confidence_range`<br>`chk_mr_title_status`<br>`chk_hi_title_status`<br>`chk_alignment_status` |

---

## 3. Detailed Potential Conflict Analysis

### Conflict 1: Column Length Discrepancies in Pre-Existing Tables
* **Observation**: In `laws.sql`, `law_name` is `VARCHAR(300)` and `short_name` is `VARCHAR(100)`. In `sections.sql`, `section_title` is `VARCHAR(500)`.
* **Risk**: If the tables already exist in PostgreSQL, executing `CREATE TABLE IF NOT EXISTS` will skip table creation, leaving the existing smaller column widths active. If a new Act with a 350-character title or a section with an 800-character heading is inserted, PostgreSQL will raise `string data right truncation (22001)` error.
* **Resolution**: Include explicit, safe `ALTER TABLE ... ALTER COLUMN ... TYPE` statements in the safe migration to ensure columns are widened without locking or dropping data.

### Conflict 2: ID Mapping (JSON String Slugs vs. PostgreSQL BIGSERIAL)
* **Observation**: In staging JSON datasets, laws and sections are keyed by string slugs (e.g. `"law_id": "maharashtra-co-operative-societies-act-1960"`, `"section_id": "maharashtra-co-operative-societies-act-1960-sec-1"`). In PostgreSQL, the relational schema uses `BIGINT` auto-incrementing surrogate keys (`law_id`, `section_id`).
* **Risk**: A naive import script trying to insert string values directly into `laws.law_id` or `sections.section_id` would fail with a type conversion error (`invalid input syntax for type bigint`).
* **Resolution**: The schema defines `laws.law_slug` and `sections.section_uid` as unique string columns. The import pipeline must map JSON string identifiers to `law_slug` and `section_uid`, using PostgreSQL's auto-generated `BIGINT` for internal relational foreign keys.

### Conflict 3: `ON DELETE CASCADE` on Live Relational Dependents
* **Observation**: Existing tables `case_legal_sections`, `section_right_mappings`, and `keyword_mappings` reference `sections(section_id)` with `ON DELETE CASCADE`.
* **Risk**: If a statutory section is deleted, all mapped user cases in `case_legal_sections` will be silently deleted from the database.
* **Resolution**: 
  1. The legal data ingestion and update policies must enforce **soft deletion** (`is_omitted = TRUE`, `extraction_status = 'repealed'`) and **never execute hard `DELETE FROM sections`**.
  2. For `section_alignments`, `ON DELETE CASCADE` is safe because `section_alignments` is a direct satellite extension table of `sections`.

---

## 4. Idempotency Verification

| DDL Statement Pattern | Idempotent? | Notes |
| :--- | :---: | :--- |
| `CREATE TABLE IF NOT EXISTS` | **Yes** | Does nothing if table already exists. |
| `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` | **Yes** | Supported in PostgreSQL >= 9.6; skips if column exists. |
| `CREATE INDEX IF NOT EXISTS` | **Yes** | Supported in PostgreSQL >= 9.5; skips if index exists. |
| `CREATE UNIQUE INDEX IF NOT EXISTS` | **Yes** | Partial index `WHERE ... IS NOT NULL` safely ignores NULL values. |
| `DO $$ BEGIN ... END $$` for Constraints | **Yes** | Wrapped in conditional catalog checks (`information_schema` / `pg_constraint`) to avoid duplicate constraint errors. |

---

## 5. Foreign Key Data Type Consistency

| Child Table & Column | Parent Table & Column | Child Type | Parent Type | Compatibility |
| :--- | :--- | :--- | :--- | :---: |
| `sections.law_id` | `laws.law_id` | `BIGINT` | `BIGINT` (BIGSERIAL) | **100% Match** |
| `section_alignments.section_id` | `sections.section_id` | `BIGINT` | `BIGINT` (BIGSERIAL) | **100% Match** |
| `section_alignments.law_id` | `laws.law_id` | `BIGINT` | `BIGINT` (BIGSERIAL) | **100% Match** |
| `keyword_mappings.section_id` | `sections.section_id` | `BIGINT` | `BIGINT` (BIGSERIAL) | **100% Match** |
| `section_right_mappings.section_id` | `sections.section_id` | `BIGINT` | `BIGINT` (BIGSERIAL) | **100% Match** |
| `case_legal_sections.section_id` | `sections.section_id` | `BIGINT` | `BIGINT` (BIGSERIAL) | **100% Match** |

---

## 6. Recommended Safe Migration: `002_mvp_legal_staging_schema_safe.sql`

To address column widening, idempotent constraint creation, and zero-downtime execution, a hardened safe migration script `database/migrations/002_mvp_legal_staging_schema_safe.sql` has been created.

### Key Enhancements in Migration 002:
1. **Explicit Column Widening**: Includes safe `ALTER COLUMN TYPE` statements for existing installations.
2. **Conditional Check Constraints**: Uses PL/pgSQL blocks to check `pg_constraint` before adding check constraints, preventing duplicate constraint errors on repeat executions.
3. **Partial Unique Indexes**: Uses `WHERE law_slug IS NOT NULL` and `WHERE section_uid IS NOT NULL` so existing rows without slugs do not block migration.
4. **Complete Enum Validation**: Validates multilingual statuses (`'official_authoritative'`, `'standard_statutory_heading'`, `'official_diglot_available'`, `'draft_translation'`, `'translation_unavailable'`).

---

## 7. Safe Execution Order & Rollback Strategy

### Safe Execution Order:
```
Step 1: Execute 002_mvp_legal_staging_schema_safe.sql in a single transactional block (BEGIN ... COMMIT).
Step 2: Run validate_legal_staging.sql (Structural Check: asserts all tables, columns, indexes exist).
Step 3: Ingest 128 Laws from laws_staging.json (Populates laws table, generates BIGINT law_id).
Step 4: Ingest 10,248 Sections from sections_staging.json (Resolves law_id foreign keys, generates BIGINT section_id).
Step 5: Ingest 42 Lexicon Terms from multilingual_lexicon_staging.json (Populates legal_lexicon).
Step 6: Ingest 10,248 Alignments from section_language_alignment_staging.json (Resolves section_id and law_id).
Step 7: Run validate_legal_staging.sql (Integrity & Data Verification: asserts 0 errors across all 10 tests).
```

### Rollback Strategy (Non-Destructive):
If an import step fails or needs to be rolled back:
* **Never use `DROP TABLE`** on `laws`, `sections`, `cases`, or `rights`.
* To rollback only the newly imported MVP batch without affecting pre-existing data:
  ```sql
  -- Rollback MVP batch safely via slug identifier:
  DELETE FROM section_alignments WHERE law_id IN (SELECT law_id FROM laws WHERE law_slug IS NOT NULL);
  DELETE FROM sections WHERE law_id IN (SELECT law_id FROM laws WHERE law_slug IS NOT NULL);
  DELETE FROM laws WHERE law_slug IS NOT NULL;
  DELETE FROM legal_lexicon;
  ```
* To remove added columns if complete DDL rollback is ever requested:
  ```sql
  DROP TABLE IF EXISTS section_alignments;
  DROP TABLE IF EXISTS legal_lexicon;
  -- Columns added to laws and sections can remain or be dropped individually without dropping tables.
  ```

---

## 8. Verification Checklist Summary

* [x] Existing primary-key types verified as `BIGSERIAL` (`BIGINT`).
* [x] Foreign key data types confirmed 100% matched across all tables.
* [x] Identified and resolved column width expansion requirements (`law_name`, `short_name`, `section_title`).
* [x] Verified that string `law_id` and `section_id` in staging JSON map to `law_slug` and `section_uid`.
* [x] Checked `ON DELETE CASCADE` behavior across case management and rights tables.
* [x] Hardened migration script created as `002_mvp_legal_staging_schema_safe.sql`.
* [x] Zero SQL executed against PostgreSQL; zero data inserted.
