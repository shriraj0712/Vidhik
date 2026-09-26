import re
import json

INPUT_FILE = "data/constitution_clean.txt"
OUTPUT_FILE = "data/constitution_structured.json"

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    text = f.read()

# Normalize spaces
text = re.sub(r"[ \t]+", " ", text)
text = re.sub(r"\n\s*\n+", "\n\n", text)

lines = [line.strip() for line in text.splitlines() if line.strip()]

parts = []
current_part = None
current_article = None

article_pattern = re.compile(
    r"^(\d+[A-Z]?)\.\s+(.+)$"
)

part_pattern = re.compile(
    r"^PART\s+([IVX]+[A-Z]?)\s*$",
    re.IGNORECASE
)

for line in lines:

    # Detect PART
    part_match = part_pattern.match(line)

    if part_match:
        current_part = {
            "part_number": part_match.group(1),
            "title": "",
            "articles": []
        }

        parts.append(current_part)
        current_article = None
        continue

    # Detect Article
    article_match = article_pattern.match(line)

    if article_match and current_part:

        article_number = article_match.group(1)
        title = article_match.group(2).strip()

        current_article = {
            "article_number": article_number,
            "title": title,
            "text": "",
            "clauses": []
        }

        current_part["articles"].append(current_article)
        continue

    # Add text to current article
    if current_article:
        current_article["text"] += " " + line

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(
        parts,
        f,
        indent=4,
        ensure_ascii=False
    )

print("Constitution successfully structured!")
print(f"Parts found: {len(parts)}")

total_articles = sum(
    len(part["articles"])
    for part in parts
)

print(f"Articles found: {total_articles}")