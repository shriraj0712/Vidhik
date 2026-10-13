from pathlib import Path
from app.database import get_db_connection, release_db_connection

sql_path = Path(__file__).resolve().parent.parent / "database" / "migrations" / "009_case_intelligence_and_context.sql"
print(f"Reading SQL from {sql_path}")
with open(sql_path, "r", encoding="utf-8") as f:
    sql_content = f.read()

conn = get_db_connection()
try:
    with conn.cursor() as cur:
        cur.execute(sql_content)
    conn.commit()
    print("Migration 009 applied successfully!")
except Exception as e:
    conn.rollback()
    print(f"Error applying migration 009: {e}")
finally:
    release_db_connection(conn)
