import sys
from pathlib import Path

# Ensure backend root is in sys.path for direct script execution
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import get_db_connection, release_db_connection

sql_path = (
    BACKEND_DIR.parent
    / "database"
    / "migrations"
    / "011_ecourts_case_tracking_schema.sql"
)

conn = None

try:
    if not sql_path.exists():
        raise FileNotFoundError(f"Migration file not found: {sql_path}")

    sql_content = sql_path.read_text(encoding="utf-8-sig")
    conn = get_db_connection()

    with conn.cursor() as cur:
        cur.execute(sql_content)

    conn.commit()
    print("eCourts migration 011 applied successfully.")

except Exception as exc:
    if conn is not None:
        try:
            conn.rollback()
        except Exception:
            pass
    print(f"eCourts migration 011 failed: {exc}")
    raise

finally:
    if conn is not None:
        release_db_connection(conn)
