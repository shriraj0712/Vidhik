from app.database import get_db_cursor

with get_db_cursor() as cur:
    cur.execute("SELECT lawyer_id, full_name, city, specialization FROM lawyers ORDER BY lawyer_id;")
    print("=== CURRENT LAWYERS IN DB ===")
    for r in cur.fetchall():
        print(f"  ID {r['lawyer_id']}: {r['full_name']} ({r['city']}) - {r['specialization']}")

    cur.execute("SELECT COUNT(*) FROM case_contexts;")
    print("Case contexts count:", cur.fetchone()['count'])

    cur.execute("SELECT COUNT(*) FROM user_active_cases;")
    print("User active cases count:", cur.fetchone()['count'])
