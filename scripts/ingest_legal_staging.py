"""
VIDHIK - Legal Dataset Deterministic Batch Ingestion Engine
===========================================================
Source Staging Datasets:
  - data/Legal_Dataset/Maharashtra_MVP/staging/laws_staging.json
  - data/Legal_Dataset/Maharashtra_MVP/staging/sections_staging.json
  - data/Legal_Dataset/Maharashtra_MVP/multilingual_staging/multilingual_lexicon_staging.json
  - data/Legal_Dataset/Maharashtra_MVP/multilingual_staging/section_language_alignment_staging.json

Target PostgreSQL Database: vidhik_db (localhost:5432)
Tables Managed:
  1. laws
  2. sections
  3. legal_lexicon
  4. section_alignments

Modes:
  --dry-run (Default) : Simulates full ingestion, tests foreign keys, duplicate detection, zero DB changes.
  --apply             : Executes batch ingestion inside an atomic transaction block.
"""

import os
import sys
import json
import re
import argparse
import hashlib
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict
import psycopg2
from psycopg2.extras import execute_values, Json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
STAGING_DIR = BASE_DIR / "data" / "Legal_Dataset" / "Maharashtra_MVP" / "staging"
MULTILINGUAL_DIR = BASE_DIR / "data" / "Legal_Dataset" / "Maharashtra_MVP" / "multilingual_staging"
REPORTS_DIR = BASE_DIR / "data" / "Legal_Dataset" / "Maharashtra_MVP" / "validation_reports"

LAWS_JSON_PATH = STAGING_DIR / "laws_staging.json"
SECTIONS_JSON_PATH = STAGING_DIR / "sections_staging.json"
LEXICON_JSON_PATH = MULTILINGUAL_DIR / "multilingual_lexicon_staging.json"
ALIGNMENTS_JSON_PATH = MULTILINGUAL_DIR / "section_language_alignment_staging.json"
QUARANTINE_LOG_PATH = REPORTS_DIR / "ingestion_quarantine_log.json"

DB_CONFIG = {
    "host": "localhost",
    "database": "vidhik_db",
    "user": "postgres",
    "password": "postgres",
    "port": "5432"
}


def compute_sha256(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def score_section_candidate(idx, sec):
    """
    Computes a substantive statutory quality score for a section candidate.
    Prioritizes:
      1. Real statutory section heading and substantive body text.
      2. Longest valid substantive section text.
      3. Valid source page range (earlier enactment pages over back-of-book schedules/notes).
      4. Non-footnote and non-schedule-reference content.
      5. Non-amendment-reference content.
      6. Deterministic tie-breaking.
    """
    score = 0
    title = (sec.get("section_title") or "").strip()
    text = (sec.get("full_text") or "").strip()
    chap_title = (sec.get("chapter_title") or "").strip()
    chap_num = (sec.get("chapter_number") or "").strip()
    page_start = sec.get("source_page_start") or 0
    text_len = len(text)
    
    # 1. Base Text Substance (Highest Priority)
    if text_len == 0:
        score -= 1000  # Extreme penalty for empty text
    elif text_len < 30:
        score -= 400   # Penalty for fragment/single-word species/book names
    elif text_len >= 100:
        score += 300 + min(text_len // 10, 500) # Big boost for substantial statutory text
    else: # 30 <= text_len < 100
        score += 100

    # 2. Title Substance & Quality
    if title:
        score += 30
        # Positive indicators: Standard section titles
        if re.search(r'^[A-Z\u0900-\u097F][a-zA-Z\u0900-\u097F\s\(\)\,\-\–\—\.\'\"]+$', title):
            score += 50
        # Negative title indicators:
        # Footnote/amendment fragments like "10A or, section 144", "6A ; or", "8 ; or]"
        if re.search(r'^\d+[A-Z]?\s*(?:or|and|\;|\,)', title, re.IGNORECASE):
            score -= 300
        if re.search(r'(?:was inserted by|were deleted by|substituted for|w\.e\.f\.)', title, re.IGNORECASE):
            score -= 400
        # Illustration titles like "A owes B", "A sells a property"
        if re.search(r'^[A-Z]\s+(?:owes|sells|mortgages|contracts|agrees)\b', title):
            score -= 250

    # 3. Chapter / Location Quality
    if chap_num or chap_title:
        if re.search(r'(?:inserted by|deleted by|w\.e\.f\.)', chap_title, re.IGNORECASE) or re.search(r'(?:inserted by|deleted by|w\.e\.f\.)', chap_num, re.IGNORECASE):
            score -= 350
        if "schedule" in chap_title.lower() or "schedule" in chap_num.lower():
            score -= 300
        else:
            score += 50

    # 4. Proviso / Explanation / Subsections Structure
    if sec.get("subsections_count", 0) > 0 or sec.get("clauses_count", 0) > 0:
        score += 80
    if sec.get("has_proviso") or sec.get("has_explanation"):
        score += 40

    # 5. Footnote text penalty
    if re.search(r'^(?:1|2|3|4|5|6|7|8|9)\s+(?:These figures|Subs\.|Ins\.|Added by|Deleted by)', text):
        score -= 400

    # Earlier enactment pages are preferred over schedules at the end of the document
    return (score, text_len, -page_start, -idx)


def resolve_canonical_sections(staged_sections):
    """
    Groups all staged sections by (law_id, section_number) and selects the
    substantive canonical section for each group using score_section_candidate.
    Returns:
      canonical_sections: list of canonical section objects
      quarantine_log: list of quarantined duplicate records with diagnostics
      uid_to_canonical_uid: mapping from any section_uid to canonical section_uid
    """
    groups = defaultdict(list)
    for idx, sec in enumerate(staged_sections):
        key = (sec['law_id'], str(sec['section_number']).strip())
        groups[key].append((idx, sec))

    canonical_sections = []
    quarantine_log = []
    uid_to_canonical_uid = {}

    for key, candidates in groups.items():
        if len(candidates) == 1:
            idx, sec = candidates[0]
            canonical_sections.append(sec)
            uid_to_canonical_uid[sec["section_id"]] = sec["section_id"]
        else:
            # Score all candidates deterministically
            scored = [(score_section_candidate(idx, s), idx, s) for idx, s in candidates]
            scored.sort(key=lambda x: x[0], reverse=True)
            
            canonical_entry = scored[0]
            canonical_sec = canonical_entry[2]
            canonical_sections.append(canonical_sec)
            
            canon_uid = canonical_sec["section_id"]
            uid_to_canonical_uid[canon_uid] = canon_uid

            for q in scored[1:]:
                q_sec = q[2]
                q_uid = q_sec["section_id"]
                uid_to_canonical_uid[q_uid] = canon_uid
                
                quarantine_log.append({
                    "law_id": key[0],
                    "section_number": key[1],
                    "quarantined_idx": q[1],
                    "quarantined_uid": q_uid,
                    "quarantined_title": q_sec.get("section_title"),
                    "quarantined_score": q[0][0],
                    "quarantined_text_len": len(q_sec.get("full_text", "")),
                    "quarantined_pages": f"{q_sec.get('source_page_start')}-{q_sec.get('source_page_end')}",
                    "canonical_idx": canonical_entry[1],
                    "canonical_uid": canon_uid,
                    "canonical_title": canonical_sec.get("section_title"),
                    "canonical_score": canonical_entry[0][0],
                    "canonical_text_len": len(canonical_sec.get("full_text", "")),
                    "canonical_pages": f"{canonical_sec.get('source_page_start')}-{canonical_sec.get('source_page_end')}"
                })

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(QUARANTINE_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(quarantine_log, f, indent=2, ensure_ascii=False)

    return canonical_sections, quarantine_log, uid_to_canonical_uid


def run_ingestion(dry_run=True):
    mode_str = "DRY RUN (Simulation Only - ZERO DB Changes)" if dry_run else "LIVE APPLY (Transactional Ingestion)"
    print("=" * 80)
    print(f"VIDHIK - LEGAL DATASET BATCH INGESTION: {mode_str}")
    print("=" * 80)
    print(f"Execution Timestamp: {datetime.now().isoformat()}")
    print(f"Target Database    : {DB_CONFIG['database']} on {DB_CONFIG['host']}:{DB_CONFIG['port']}")

    # 1. Load Staged JSON Data
    print("\n--- 1. LOADING STAGED ARTIFACTS ---")
    with open(LAWS_JSON_PATH, encoding="utf-8") as f:
        staged_laws = json.load(f)
    print(f"  Loaded Laws Staging        : {len(staged_laws)} laws")

    with open(SECTIONS_JSON_PATH, encoding="utf-8") as f:
        staged_sections = json.load(f)
    print(f"  Loaded Sections Staging    : {len(staged_sections)} total section objects")

    with open(LEXICON_JSON_PATH, encoding="utf-8") as f:
        staged_lexicon = json.load(f)
    print(f"  Loaded Lexicon Staging     : {len(staged_lexicon)} terms")

    with open(ALIGNMENTS_JSON_PATH, encoding="utf-8") as f:
        staged_alignments = json.load(f)
    print(f"  Loaded Alignments Staging  : {len(staged_alignments)} alignments")

    # 2. Canonical Resolution & Quarantine
    print("\n--- 2. CANONICAL RESOLUTION & DEDUPLICATION ---")
    canonical_sections, quarantine_log, uid_to_canonical_uid = resolve_canonical_sections(staged_sections)
    print(f"  Total Unique Section Provisions : {len(canonical_sections)} canonical sections")
    print(f"  Total Quarantined Duplicates    : {len(quarantine_log)} records logged to:")
    print(f"    -> {QUARANTINE_LOG_PATH}")

    # 3. Connect to Database & Pre-Ingestion Row Counts
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    db_tables = [r[0] for r in cur.fetchall()]

    pre_counts = {}
    for t in ["laws", "sections", "legal_lexicon", "section_alignments"]:
        if t in db_tables:
            cur.execute(f"SELECT COUNT(*) FROM {t};")
            pre_counts[t] = cur.fetchone()[0]
        else:
            pre_counts[t] = 0

    print("\n--- 3. PRE-INGESTION DATABASE ROW COUNTS ---")
    for t, cnt in pre_counts.items():
        print(f"  - {t:<22}: {cnt:>6} rows")

    # Ingestion Telemetry
    telemetry = {
        "laws_inserted": 0,
        "laws_updated": 0,
        "laws_manual_review": 0,
        "sections_inserted": 0,
        "sections_updated": 0,
        "sections_quarantined": len(quarantine_log),
        "sections_manual_review": 0,
        "sections_omitted": 0,
        "lexicon_inserted": 0,
        "lexicon_updated": 0,
        "alignments_inserted": 0,
        "alignments_updated": 0,
        "alignments_quarantined": len(quarantine_log),
        "alignments_manual_review": 0,
        "fk_law_errors": 0,
        "fk_section_errors": 0,
        "sha256_mismatches": 0
    }

    law_slug_to_id = {}
    canonical_uid_to_db_id = {}

    try:
        # =====================================================================
        # STEP 1: INGEST LAWS
        # =====================================================================
        print("\n--- 4. PROCESSING STEP 1: LAWS ---")
        cur.execute("SELECT law_id, law_name, law_slug FROM laws;")
        existing_laws = cur.fetchall()
        existing_laws_by_name = {r[1].lower().strip(): r[0] for r in existing_laws}
        existing_laws_by_slug = {r[2]: r[0] for r in existing_laws if r[2]}

        for law in staged_laws:
            slug = law["law_id"]
            name = law["law_name"]
            short_name = law.get("short_name", name[:255])
            year = law.get("year")
            law_type = law.get("law_type", "Central Act")
            jurisdiction = law.get("jurisdiction", "India")
            source_pdf = law.get("source_pdf")
            total_pages = law.get("total_pages", 0)
            enact_start = law.get("enactment_start_page", 1)
            total_secs = law.get("total_sections_extracted", 0)
            is_diglot = law.get("is_diglot", False)
            ext_status = law.get("extraction_status", "staged_from_pdf")
            man_rev = law.get("manual_review_required", False)
            notes = Json(law.get("parser_notes", []))

            if man_rev:
                telemetry["laws_manual_review"] += 1

            matched_id = existing_laws_by_slug.get(slug) or existing_laws_by_name.get(name.lower().strip())

            if matched_id:
                telemetry["laws_updated"] += 1
                law_slug_to_id[slug] = matched_id
                if not dry_run:
                    cur.execute("""
                        UPDATE laws SET
                            law_slug = %s,
                            short_name = %s,
                            year = %s,
                            law_type = %s,
                            jurisdiction = %s,
                            source_pdf = %s,
                            total_pages = %s,
                            enactment_start_page = %s,
                            total_sections_extracted = %s,
                            is_diglot = %s,
                            extraction_status = %s,
                            manual_review_required = %s,
                            parser_notes = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE law_id = %s;
                    """, (
                        slug, short_name, year, law_type, jurisdiction, source_pdf,
                        total_pages, enact_start, total_secs, is_diglot, ext_status,
                        man_rev, notes, matched_id
                    ))
            else:
                telemetry["laws_inserted"] += 1
                if not dry_run:
                    cur.execute("""
                        INSERT INTO laws (
                            law_name, law_slug, short_name, year, law_type,
                            jurisdiction, source_pdf, total_pages, enactment_start_page,
                            total_sections_extracted, is_diglot, extraction_status,
                            manual_review_required, parser_notes, created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        ) RETURNING law_id;
                    """, (
                        name, slug, short_name, year, law_type,
                        jurisdiction, source_pdf, total_pages, enact_start,
                        total_secs, is_diglot, ext_status, man_rev, notes
                    ))
                    new_law_id = cur.fetchone()[0]
                    law_slug_to_id[slug] = new_law_id
                else:
                    law_slug_to_id[slug] = 900000 + len(law_slug_to_id)

        print(f"  Laws Plan: {telemetry['laws_inserted']} to insert, {telemetry['laws_updated']} to update, {telemetry['laws_manual_review']} flagged for review.")

        # =====================================================================
        # STEP 2: INGEST CANONICAL SECTIONS
        # =====================================================================
        print("\n--- 5. PROCESSING STEP 2: CANONICAL SECTIONS ---")
        cur.execute("SELECT section_id, law_id, section_number, section_uid FROM sections;")
        existing_sections = cur.fetchall()
        db_secs_by_uid = {r[3]: r[0] for r in existing_sections if r[3]}
        db_secs_by_law_secnum = {(r[1], str(r[2]).strip()): r[0] for r in existing_sections}

        simulated_sec_id_counter = 800000

        for sec in canonical_sections:
            sec_uid = sec["section_id"]
            law_slug = sec["law_id"]
            sec_num = str(sec["section_number"]).strip()
            title = sec.get("section_title")
            full_text = sec.get("full_text", "")
            chap_num = sec.get("chapter_number")
            chap_title = sec.get("chapter_title")
            part_num = sec.get("part_number")
            part_title = sec.get("part_title")
            source_pdf = sec.get("source_pdf")
            page_start = sec.get("source_page_start")
            page_end = sec.get("source_page_end")
            jurisdiction = sec.get("jurisdiction", "India")
            is_omitted = sec.get("is_omitted", False)
            omission_note = sec.get("omission_note")
            is_def = sec.get("is_definition_section", False)
            subs_cnt = sec.get("subsections_count", 0)
            cl_cnt = sec.get("clauses_count", 0)
            subcl_cnt = sec.get("subclauses_count", 0)
            has_prov = sec.get("has_proviso", False)
            has_expl = sec.get("has_explanation", False)
            has_ill = sec.get("has_illustration", False)
            has_sched = sec.get("has_schedule_ref", False)
            ext_status = sec.get("extraction_status", "staged_from_pdf")
            man_rev = sec.get("manual_review_required", False)
            notes = Json(sec.get("parser_notes", []))
            text_sha = compute_sha256(full_text)

            if is_omitted:
                telemetry["sections_omitted"] += 1
            if man_rev:
                telemetry["sections_manual_review"] += 1

            parent_law_id = law_slug_to_id.get(law_slug)
            if not parent_law_id:
                telemetry["fk_law_errors"] += 1
                continue

            sec_key = (parent_law_id, sec_num)
            matched_sec_id = db_secs_by_uid.get(sec_uid) or db_secs_by_law_secnum.get(sec_key)

            if matched_sec_id:
                telemetry["sections_updated"] += 1
                canonical_sec_id = matched_sec_id
                canonical_uid_to_db_id[sec_uid] = canonical_sec_id
                if not dry_run:
                    cur.execute("""
                        UPDATE sections SET
                            section_uid = %s,
                            section_title = %s,
                            full_text = %s,
                            chapter_number = %s,
                            chapter_title = %s,
                            part_number = %s,
                            part_title = %s,
                            source_pdf = %s,
                            source_page_start = %s,
                            source_page_end = %s,
                            jurisdiction = %s,
                            is_omitted = %s,
                            omission_note = %s,
                            is_definition_section = %s,
                            subsections_count = %s,
                            clauses_count = %s,
                            subclauses_count = %s,
                            has_proviso = %s,
                            has_explanation = %s,
                            has_illustration = %s,
                            has_schedule_ref = %s,
                            extraction_status = %s,
                            manual_review_required = %s,
                            parser_notes = %s,
                            text_sha256 = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE section_id = %s;
                    """, (
                        sec_uid, title, full_text, chap_num, chap_title, part_num,
                        part_title, source_pdf, page_start, page_end, jurisdiction,
                        is_omitted, omission_note, is_def, subs_cnt, cl_cnt, subcl_cnt,
                        has_prov, has_expl, has_ill, has_sched, ext_status, man_rev,
                        notes, text_sha, matched_sec_id
                    ))
            else:
                telemetry["sections_inserted"] += 1
                if not dry_run:
                    cur.execute("""
                        INSERT INTO sections (
                            law_id, section_number, section_uid, section_title, full_text,
                            chapter_number, chapter_title, part_number, part_title,
                            source_pdf, source_page_start, source_page_end, jurisdiction,
                            is_omitted, omission_note, is_definition_section, subsections_count,
                            clauses_count, subclauses_count, has_proviso, has_explanation,
                            has_illustration, has_schedule_ref, extraction_status,
                            manual_review_required, parser_notes, text_sha256,
                            created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        ) RETURNING section_id;
                    """, (
                        parent_law_id, sec_num, sec_uid, title, full_text,
                        chap_num, chap_title, part_num, part_title,
                        source_pdf, page_start, page_end, jurisdiction,
                        is_omitted, omission_note, is_def, subs_cnt,
                        cl_cnt, subcl_cnt, has_prov, has_expl,
                        has_ill, has_sched, ext_status,
                        man_rev, notes, text_sha
                    ))
                    canonical_sec_id = cur.fetchone()[0]
                    canonical_uid_to_db_id[sec_uid] = canonical_sec_id
                else:
                    canonical_sec_id = simulated_sec_id_counter
                    simulated_sec_id_counter += 1
                    canonical_uid_to_db_id[sec_uid] = canonical_sec_id

        print(f"  Canonical Sections Plan: {telemetry['sections_inserted']} to insert, {telemetry['sections_updated']} to update (Total Canonical: {len(canonical_sections)}).")

        # =====================================================================
        # STEP 3: INGEST LEGAL LEXICON
        # =====================================================================
        print("\n--- 6. PROCESSING STEP 3: LEGAL LEXICON ---")
        cur.execute("SELECT lexicon_id, term_id FROM legal_lexicon;")
        existing_lex = {r[1]: r[0] for r in cur.fetchall()}

        for item in staged_lexicon:
            term_id = item["term_id"]
            cat = item["category"]
            t_en = item["term_en"]
            t_mr = item["term_mr"]
            t_hi = item["term_hi"]
            gram_type = item.get("grammatical_type")
            ctx = item.get("context_usage")
            source = item["official_source"]
            v_status = item.get("verification_status", "verified_authoritative")
            aliases_mr = Json(item.get("aliases_mr", []))
            aliases_hi = Json(item.get("aliases_hi", []))

            if term_id in existing_lex:
                telemetry["lexicon_updated"] += 1
                if not dry_run:
                    cur.execute("""
                        UPDATE legal_lexicon SET
                            category = %s,
                            term_en = %s,
                            term_mr = %s,
                            term_hi = %s,
                            grammatical_type = %s,
                            context_usage = %s,
                            official_source = %s,
                            verification_status = %s,
                            aliases_mr = %s,
                            aliases_hi = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE term_id = %s;
                    """, (
                        cat, t_en, t_mr, t_hi, gram_type, ctx, source,
                        v_status, aliases_mr, aliases_hi, term_id
                    ))
            else:
                telemetry["lexicon_inserted"] += 1
                if not dry_run:
                    cur.execute("""
                        INSERT INTO legal_lexicon (
                            term_id, category, term_en, term_mr, term_hi,
                            grammatical_type, context_usage, official_source,
                            verification_status, aliases_mr, aliases_hi,
                            created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        );
                    """, (
                        term_id, cat, t_en, t_mr, t_hi,
                        gram_type, ctx, source, v_status,
                        aliases_mr, aliases_hi
                    ))

        print(f"  Lexicon Plan: {telemetry['lexicon_inserted']} to insert, {telemetry['lexicon_updated']} to update.")

        # =====================================================================
        # STEP 4: INGEST SECTION ALIGNMENTS
        # =====================================================================
        print("\n--- 7. PROCESSING STEP 4: SECTION ALIGNMENTS ---")
        cur.execute("SELECT alignment_id, section_id FROM section_alignments;")
        existing_aligns = {r[1]: r[0] for r in cur.fetchall()}
        seen_alignment_db_ids = set()

        for align in staged_alignments:
            sec_uid = align["section_id"]
            law_slug = align["law_id"]
            title_en = align.get("title_en")
            text_en = align["text_en"]
            text_sha = align["text_en_sha256"]
            title_mr = align.get("title_mr")
            text_mr = align.get("text_mr")
            mr_t_stat = align.get("mr_title_status", "translation_unavailable")
            mr_b_stat = align.get("mr_body_status", "translation_unavailable")
            mr_conf = align.get("mr_confidence_score", 0.0)
            mr_prov = Json(align.get("mr_provenance")) if align.get("mr_provenance") else None
            title_hi = align.get("title_hi")
            text_hi = align.get("text_hi")
            hi_t_stat = align.get("hi_title_status", "translation_unavailable")
            hi_b_stat = align.get("hi_body_status", "translation_unavailable")
            hi_conf = align.get("hi_confidence_score", 0.0)
            hi_prov = Json(align.get("hi_provenance")) if align.get("hi_provenance") else None
            matched_terms = Json(align.get("matched_lexicon_terms", []))
            align_stat = align.get("alignment_status", "translation_unavailable")
            man_rev = align.get("manual_review_required", False)
            rev_notes = Json(align.get("review_notes", []))

            # Hash check
            if compute_sha256(text_en) != text_sha:
                telemetry["sha256_mismatches"] += 1

            if man_rev:
                telemetry["alignments_manual_review"] += 1

            # Resolve canonical UID and database target_sec_id
            canon_uid = uid_to_canonical_uid.get(sec_uid, sec_uid)
            target_sec_id = canonical_uid_to_db_id.get(canon_uid)
            target_law_id = law_slug_to_id.get(law_slug)

            if not target_sec_id:
                telemetry["fk_section_errors"] += 1
                continue
            if not target_law_id:
                telemetry["fk_law_errors"] += 1
                continue

            # Deduplicate alignment rows targeting the same canonical section
            if target_sec_id in seen_alignment_db_ids:
                continue
            seen_alignment_db_ids.add(target_sec_id)

            if target_sec_id in existing_aligns:
                telemetry["alignments_updated"] += 1
                if not dry_run:
                    cur.execute("""
                        UPDATE section_alignments SET
                            section_uid = %s,
                            law_id = %s,
                            title_en = %s,
                            text_en = %s,
                            text_en_sha256 = %s,
                            title_mr = %s,
                            text_mr = %s,
                            mr_title_status = %s,
                            mr_body_status = %s,
                            mr_confidence_score = %s,
                            mr_provenance = %s,
                            title_hi = %s,
                            text_hi = %s,
                            hi_title_status = %s,
                            hi_body_status = %s,
                            hi_confidence_score = %s,
                            hi_provenance = %s,
                            matched_lexicon_terms = %s,
                            alignment_status = %s,
                            manual_review_required = %s,
                            review_notes = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE section_id = %s;
                    """, (
                        canon_uid, target_law_id, title_en, text_en, text_sha,
                        title_mr, text_mr, mr_t_stat, mr_b_stat, mr_conf, mr_prov,
                        title_hi, text_hi, hi_t_stat, hi_b_stat, hi_conf, hi_prov,
                        matched_terms, align_stat, man_rev, rev_notes, target_sec_id
                    ))
            else:
                telemetry["alignments_inserted"] += 1
                if not dry_run:
                    cur.execute("""
                        INSERT INTO section_alignments (
                            section_id, section_uid, law_id, title_en, text_en,
                            text_en_sha256, title_mr, text_mr, mr_title_status,
                            mr_body_status, mr_confidence_score, mr_provenance,
                            title_hi, text_hi, hi_title_status, hi_body_status,
                            hi_confidence_score, hi_provenance, matched_lexicon_terms,
                            alignment_status, manual_review_required, review_notes,
                            created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        );
                    """, (
                        target_sec_id, canon_uid, target_law_id, title_en, text_en,
                        text_sha, title_mr, text_mr, mr_t_stat, mr_b_stat, mr_conf,
                        mr_prov, title_hi, text_hi, hi_t_stat, hi_b_stat, hi_conf,
                        hi_prov, matched_terms, align_stat, man_rev, rev_notes
                    ))

        print(f"  Canonical Alignments Plan: {telemetry['alignments_inserted']} to insert, {telemetry['alignments_updated']} to update (Total Unique: {len(seen_alignment_db_ids)}).")

        if not dry_run:
            conn.commit()
            print("\n  -> TRANSACTION COMMITTED SUCCESSFULLY!")
        else:
            conn.rollback()
            print("\n  -> DRY-RUN COMPLETE: TRANSACTION ROLLED BACK (ZERO DB CHANGES).")

    except Exception as e:
        conn.rollback()
        print(f"\n  -> ERROR OCCURRED: {e}")
        print("  -> Transaction rolled back safely.")
        conn.close()
        raise e

    conn.close()

    # Summary Display
    print("\n" + "=" * 80)
    print("INGESTION TELEMETRY SUMMARY")
    print("=" * 80)
    print(f"Mode                            : {mode_str}")
    print(f"Laws Plan                       : {telemetry['laws_inserted']} new / {telemetry['laws_updated']} updated (Total: {len(staged_laws)})")
    print(f"Canonical Sections Plan         : {telemetry['sections_inserted']} new / {telemetry['sections_updated']} updated (Total Canonical: {len(canonical_sections)})")
    print(f"Quarantined Duplicate Sections  : {telemetry['sections_quarantined']} duplicate occurrences safely quarantined")
    print(f"Legal Lexicon Plan              : {telemetry['lexicon_inserted']} new / {telemetry['lexicon_updated']} updated (Total: {len(staged_lexicon)})")
    print(f"Canonical Alignments Plan       : {telemetry['alignments_inserted']} new / {telemetry['alignments_updated']} updated (Total Canonical: {len(seen_alignment_db_ids)})")
    print(f"Foreign Key Resolution Errors   : Laws: {telemetry['fk_law_errors']}, Sections: {telemetry['fk_section_errors']}")
    print(f"SHA-256 Digest Mismatches       : {telemetry['sha256_mismatches']}")
    print(f"Manual Review Tracked Records   : Laws: {telemetry['laws_manual_review']}, Sections: {telemetry['sections_manual_review']}, Alignments: {telemetry['alignments_manual_review']}")
    print("=" * 80)

    return telemetry, pre_counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vidhik Legal Dataset Deterministic Batch Ingestion Engine")
    parser.add_argument("--apply", action="store_true", help="Execute live database ingestion (default is dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="Run simulation only (default)")
    args = parser.parse_args()

    is_dry = True if not args.apply or args.dry_run else False
    if args.apply and not args.dry_run:
        is_dry = False

    run_ingestion(dry_run=is_dry)
