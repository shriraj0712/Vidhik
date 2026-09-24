import json
import psycopg2
from collections import Counter

DB_CONFIG = {
    "host": "localhost",
    "database": "vidhik_db",
    "user": "postgres",
    "password": "postgres",
    "port": "5432"
}

INPUT_FILE = "../data/articles_nlp.json"

# Load NLP data
with open(INPUT_FILE, "r", encoding="utf-8") as file:
    articles = json.load(file)

conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

print("Connected to PostgreSQL!")

for article in articles:

    article_number = article.get("article_number")
    lemmas = article.get("lemmas", [])

    # Remove very short terms and duplicates
    keywords = set()

    for word in lemmas:
        word = word.lower().strip()

        if len(word) >= 3:
            keywords.add(word)

    # Find corresponding article
    cursor.execute(
        """
        SELECT article_id
        FROM articles
        WHERE article_number = %s
        ORDER BY article_id
        LIMIT 1;
        """,
        (article_number,)
    )

    result = cursor.fetchone()

    if not result:
        continue

    article_id = result[0]

    for keyword in keywords:

        # Insert keyword
        cursor.execute(
            """
            INSERT INTO legal_keywords (keyword)
            VALUES (%s)
            ON CONFLICT (keyword) DO NOTHING;
            """,
            (keyword,)
        )

        # Get keyword ID
        cursor.execute(
            """
            SELECT keyword_id
            FROM legal_keywords
            WHERE keyword = %s;
            """,
            (keyword,)
        )

        keyword_result = cursor.fetchone()

        if not keyword_result:
            continue

        keyword_id = keyword_result[0]

        # Connect keyword with article
        cursor.execute(
            """
            INSERT INTO article_keywords
            (article_id, keyword_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING;
            """,
            (article_id, keyword_id)
        )

conn.commit()

cursor.close()
conn.close()

print("NLP keywords inserted successfully!")