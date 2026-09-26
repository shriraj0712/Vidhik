"""
VIDHIK - Database State Inspector
Checks PostgreSQL connection, lists existing tables, columns, constraints, and row counts.
READ-ONLY probe - makes ZERO modifications.
"""

import sys
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

DB_CONFIG = {
    "host": "localhost",
    "database": "vidhik_db",
    "user": "postgres",
    "password": "postgres",
    "port": "5432"
}

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT current_database(), version();")
    db, ver = cur.fetchone()
    print("=" * 60)
    print(f"Connected to PostgreSQL Database: {db}")
    print(f"Version: {ver}")
    print("=" * 60)
    
    # List all tables in public schema
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    tables = [r[0] for r in cur.fetchall()]
    print(f"\nExisting Tables in 'public' schema ({len(tables)} found):")
    
    row_counts = {}
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t};")
        cnt = cur.fetchone()[0]
        row_counts[t] = cnt
        print(f"  - {t:<30}: {cnt:>6} rows")
        
    print("\nLaws Table Schema Details:")
    if "laws" in tables:
        cur.execute("""
            SELECT column_name, data_type, character_maximum_length, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'laws'
            ORDER BY ordinal_position;
        """)
        for col in cur.fetchall():
            print(f"  - {col[0]:<25} {col[1]:<15} max_len: {str(col[2]):<6} nullable: {col[3]}")
    else:
        print("  [laws table does not exist yet]")
        
    print("\nSections Table Schema Details:")
    if "sections" in tables:
        cur.execute("""
            SELECT column_name, data_type, character_maximum_length, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'sections'
            ORDER BY ordinal_position;
        """)
        for col in cur.fetchall():
            print(f"  - {col[0]:<25} {col[1]:<15} max_len: {str(col[2]):<6} nullable: {col[3]}")
    else:
        print("  [sections table does not exist yet]")

    conn.close()
except Exception as e:
    print(f"PostgreSQL Inspection Error: {e}")
