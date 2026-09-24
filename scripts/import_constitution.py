import json
import psycopg2

# PostgreSQL configuration
DB_CONFIG = {
    "host": "localhost",
    "database": "vidhik_db",
    "user": "postgres",
    "password": "postgres",
    "port": "5432"
}

# Load NLP-processed articles
with open(
    "../data/articles_nlp.json",
    "r",
    encoding="utf-8"
) as file:
    articles = json.load(file)

# Connect to PostgreSQL
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

print("Connected to PostgreSQL!")

# Insert articles
for article in articles:

    article_number = article.get("article_number")
    title = article.get("title", "")
    article_text = article.get("text", "").strip()

    # Skip empty articles
    if not article_text:
        continue

    cursor.execute(
        """
        INSERT INTO articles
        (
            article_number,
            title,
            article_text,
            source
        )
        VALUES (%s, %s, %s, %s)
        RETURNING article_id;
        """,
        (
            article_number,
            title,
            article_text,
            "Constitution of India"
        )
    )

    article_id = cursor.fetchone()[0]

    # Insert NLP entities
    for entity in article.get("entities", []):

        entity_text = entity.get("text")
        entity_type = entity.get("label")

        if not entity_text:
            continue

        # Create entity if it doesn't already exist
        cursor.execute(
            """
            INSERT INTO legal_entities
            (entity_text, entity_type)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            RETURNING entity_id;
            """,
            (entity_text, entity_type)
        )

        result = cursor.fetchone()

        if result:
            entity_id = result[0]
        else:
            cursor.execute(
                """
                SELECT entity_id
                FROM legal_entities
                WHERE entity_text = %s
                AND entity_type = %s;
                """,
                (entity_text, entity_type)
            )

            result = cursor.fetchone()

            if result:
                entity_id = result[0]
            else:
                continue

        # Link entity to article
        cursor.execute(
            """
            INSERT INTO article_entities
            (article_id, entity_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING;
            """,
            (article_id, entity_id)
        )

# Save changes
conn.commit()

cursor.close()
conn.close()

print("Constitution imported successfully!")
print("Articles imported:", len(articles))