import json
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port="5432",
    database="vidhik_db",
    user="postgres",
    password="postgres"
)

cursor = conn.cursor()

with open("articles.json", "r", encoding="utf-8") as f:
    articles = json.load(f)

for article in articles:

    cursor.execute(
        """
        INSERT INTO articles
        (article_number, title, article_text)
        VALUES (%s, %s, %s);
        """,
        (
            article.get("article_number"),
            article.get("title"),
            article.get("text")
        )
    )

conn.commit()

cursor.close()
conn.close()

print(f"{len(articles)} articles imported successfully!")