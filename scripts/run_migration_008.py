"""
Vidhik Legal Platform - Run Migration 008
==========================================
Applies database/migrations/008_expand_legal_procedures_phase12.sql
Expands legal procedures to 25 procedures and checklists.
Verifies integrity before and after.
"""

import sys
import os
sys.path.insert(0, os.path.abspath("backend"))

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

from app.database import get_db_cursor

MIGRATION_PATH = os.path.abspath("database/migrations/008_expand_legal_procedures_phase12.sql")

def run_migration():
    print("=" * 70)
    print("APPLYING MIGRATION 008: EXPAND LEGAL PROCEDURES TO 25")
    print("=" * 70)

    if not os.path.exists(MIGRATION_PATH):
        print(f"[ERROR] Migration file not found at: {MIGRATION_PATH}")
        sys.exit(1)

    with open(MIGRATION_PATH, "r", encoding="utf-8") as f:
        sql_content = f.read()

    with get_db_cursor() as cur:
        # Pre-check counts
        cur.execute("SELECT count(*) as cnt FROM legal_procedures;")
        r = cur.fetchone()
        old_proc_count = r["cnt"] if r else 0
        cur.execute("SELECT count(*) as cnt FROM procedure_required_documents;")
        r = cur.fetchone()
        old_doc_count = r["cnt"] if r else 0
        cur.execute("SELECT count(*) as cnt FROM laws;")
        r = cur.fetchone()
        old_laws = r["cnt"] if r else 0
        cur.execute("SELECT count(*) as cnt FROM sections;")
        r = cur.fetchone()
        old_sections = r["cnt"] if r else 0

        print(f"Pre-migration state:")
        print(f"  - legal_procedures: {old_proc_count}")
        print(f"  - procedure_required_documents: {old_doc_count}")
        print(f"  - laws: {old_laws}")
        print(f"  - sections: {old_sections}")

        print("\nExecuting Migration 008 SQL...")
        cur.execute(sql_content)

        # Post-check counts
        cur.execute("SELECT count(*) as cnt FROM legal_procedures;")
        r = cur.fetchone()
        new_proc_count = r["cnt"] if r else 0
        cur.execute("SELECT count(*) as cnt FROM procedure_required_documents;")
        r = cur.fetchone()
        new_doc_count = r["cnt"] if r else 0
        cur.execute("SELECT count(*) as cnt FROM laws;")
        r = cur.fetchone()
        new_laws = r["cnt"] if r else 0
        cur.execute("SELECT count(*) as cnt FROM sections;")
        r = cur.fetchone()
        new_sections = r["cnt"] if r else 0

        print(f"\nPost-migration state:")
        print(f"  - legal_procedures: {new_proc_count} (Expected: 25)")
        print(f"  - procedure_required_documents: {new_doc_count}")
        print(f"  - laws: {new_laws} (Unchanged: {new_laws == old_laws})")
        print(f"  - sections: {new_sections} (Unchanged: {new_sections == old_sections})")

        assert new_proc_count == 25, f"Expected 25 procedures, got {new_proc_count}"
        assert new_laws == 869, f"Laws changed! Expected 869, got {new_laws}"
        assert new_sections == 41442, f"Sections changed! Expected 41442, got {new_sections}"

        # Verify each of the 25 procedures has at least 4 required documents
        for pid in range(1, 26):
            cur.execute("SELECT procedure_name, category FROM legal_procedures WHERE procedure_id = %s;", (pid,))
            p = cur.fetchone()
            assert p is not None, f"Missing procedure ID {pid}!"
            cur.execute("SELECT count(*) as cnt, COUNT(CASE WHEN is_mandatory = TRUE THEN 1 END) as mand FROM procedure_required_documents WHERE procedure_id = %s;", (pid,))
            doc_info = cur.fetchone()
            assert doc_info is not None, f"Missing doc_info for procedure {pid}!"
            assert doc_info["cnt"] >= 4, f"Procedure {pid} has only {doc_info['cnt']} documents!"
            assert doc_info["mand"] >= 1, f"Procedure {pid} has 0 mandatory documents!"
            print(f"  ✓ [{pid:2d}] {p['procedure_name'][:48]:48} ({p['category']:26}) | Docs: {doc_info['cnt']} (Mandatory: {doc_info['mand']})")

    print("\n" + "=" * 70)
    print("MIGRATION 008 COMPLETED AND VERIFIED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_migration()
