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

# Load NLP JSON
with open("articles_nlp.json", "r", encoding="utf-8") as f:
    data = json.load(f)

keyword_count = 0
entity_count = 0
mapping_count = 0
entity_mapping_count = 0

for item in data:

    article_number = item.get("article_number")

    # Find article_id
    cursor.execute(
        """
        SELECT article_id
        FROM articles
        WHERE article_number = %s
        """,
        (article_number,)
    )

    result = cursor.fetchone()

    if not result:
        print(f"Article {article_number} not found. Skipping.")
        continue

    article_id = result[0]

# -------------------------
# KEYWORDS FROM LEMMAS
# -------------------------

lemmas = item.get("lemmas", [])

for lemma in lemmas:

    if not lemma:
        continue

    keyword = lemma.strip()

    # Find keyword in legal_keywords
    cursor.execute(
        """
        SELECT keyword_id
        FROM legal_keywords
        WHERE keyword = %s
        """,
        (keyword,)
    )

    result = cursor.fetchone()

    if result:
        keyword_id = result[0]

    else:
        cursor.execute(
            """
            INSERT INTO legal_keywords
            (keyword)
            VALUES (%s)
            RETURNING keyword_id
            """,
            (keyword,)
        )

        keyword_id = cursor.fetchone()[0]
        keyword_count += 1

    # Create article-keyword mapping
    cursor.execute(
        """
        SELECT 1
        FROM article_keywords
        WHERE article_id = %s
        AND keyword_id = %s
        """,
        (article_id, keyword_id)
    )

    if not cursor.fetchone():

        cursor.execute(
            """
            INSERT INTO article_keywords
            (article_id, keyword_id)
            VALUES (%s, %s)
            """,
            (article_id, keyword_id)
        )

        mapping_count += 1

    # -------------------------
    # ENTITIES
    # -------------------------

    entities = item.get("entities", [])

    for entity in entities:

        entity_text = entity.get("text", "").strip()
        entity_type = entity.get("label", "").strip()

        if not entity_text:
            continue

        # Check whether entity already exists
        cursor.execute(
            """
            SELECT entity_id
            FROM legal_entities
            WHERE entity_text = %s
            AND entity_type = %s
            """,
            (entity_text, entity_type)
        )

        result = cursor.fetchone()

        if result:
            entity_id = result[0]
        else:
            cursor.execute(
                """
                INSERT INTO legal_entities
                (entity_text, entity_type)
                VALUES (%s, %s)
                RETURNING entity_id
                """,
                (entity_text, entity_type)
            )

            entity_id = cursor.fetchone()[0]
            entity_count += 1

        # Create article-entity mapping
        cursor.execute(
            """
            SELECT 1
            FROM article_entities
            WHERE article_id = %s
            AND entity_id = %s
            """,
            (article_id, entity_id)
        )

        if not cursor.fetchone():

            cursor.execute(
                """
                INSERT INTO article_entities
                (article_id, entity_id)
                VALUES (%s, %s)
                """,
                (article_id, entity_id)
            )

            entity_mapping_count += 1


conn.commit()

cursor.close()
conn.close()

print("====================================")
print("NLP DATA IMPORT COMPLETED")
print("====================================")
print("New keywords:", keyword_count)
print("Article-keyword mappings:", mapping_count)
print("New entities:", entity_count)
print("Article-entity mappings:", entity_mapping_count)