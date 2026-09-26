import re
import json

input_file = "data/constitution_clean.txt"
output_file = "data/articles.json"

with open(input_file, "r", encoding="utf-8") as file:
    text = file.read()

pattern = r'(?m)^\s*(\d+[A-Z]?)\.\s+(.+?)(?=\n)'

matches = list(re.finditer(pattern, text))

articles = []

for i, match in enumerate(matches):
    article_number = match.group(1)
    title = match.group(2).strip()

    start = match.end()
    end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

    article_text = text[start:end].strip()

    articles.append({
        "article_number": article_number,
        "title": title,
        "text": article_text
    })

with open(output_file, "w", encoding="utf-8") as file:
    json.dump(articles, file, indent=4, ensure_ascii=False)

print(f"{len(articles)} articles extracted successfully!")