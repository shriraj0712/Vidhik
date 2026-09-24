import json
import spacy

INPUT_FILE = "../data/constitution_structured.json"
OUTPUT_FILE = "../data/constitution_nlp.json"

# Load English NLP model
nlp = spacy.load("en_core_web_sm")

# Load structured Constitution
with open(INPUT_FILE, "r", encoding="utf-8") as file:
    constitution = json.load(file)

total_articles = 0

for part in constitution:

    for article in part.get("articles", []):

        total_articles += 1

        text = article.get("text", "")

        doc = nlp(text)

        # Tokens
        article["tokens"] = [
            token.text
            for token in doc
            if not token.is_space
        ]

        # Lemmas
        article["lemmas"] = [
            token.lemma_
            for token in doc
            if not token.is_stop
            and not token.is_punct
            and not token.is_space
        ]

        # Named Entities
        article["entities"] = [
            {
                "text": entity.text,
                "label": entity.label_
            }
            for entity in doc.ents
        ]

print("NLP processing completed.")
print("Total articles processed:", total_articles)

# Save NLP output
with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    json.dump(
        constitution,
        file,
        indent=4,
        ensure_ascii=False
    )

print("Saved to:", OUTPUT_FILE)