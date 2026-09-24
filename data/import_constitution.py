import json
import psycopg2

# PostgreSQL connection
conn = psycopg2.connect(
    host="localhost",
    port="5432",
    database="vidhik_db",
    user="postgres",
    password="postgres"
)

cursor = conn.cursor()

# Read JSON
with open("constitution_structured.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Insert Constitution Parts
for part in data:
    cursor.execute(
        """
        INSERT INTO constitution_parts (part_number, title)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING;
        """,
        (
            part.get("part_number"),
            part.get("title")
        )
    )

conn.commit()

cursor.close()
conn.close()

print("Constitution parts imported successfully!")