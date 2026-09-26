import json
from collections import Counter
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_stream_extraction as tse

articles = tse.articles
articles_map = {a['article_number']: a for a in articles}

# Check base articles 1-395
missing_base = []
for i in range(1, 396):
    if str(i) not in articles_map and str(i) != '238':
        missing_base.append(str(i))

print(f"Missing base articles (excluding 238): {missing_base}")

# Check key landmark articles
key_articles = [
    "PREAMBLE", "1", "14", "15", "19", "21", "21A", "25", "32", "39A", "44", "48A", 
    "51A", "124", "131", "132", "136", "174", "214", "222", "226", "239AA", "243A", 
    "246", "246A", "279A", "280", "300A", "352", "356", "360", "368", "370", "395"
]

print("\n--- Landmark Articles Audit ---")
for k in key_articles:
    if k in articles_map:
        a = articles_map[k]
        print(f"[{k}] (Part: {a['part_number']}, Chap: {a['chapter_number']}) -> Title: '{a['title']}' | Text Len: {len(a['full_text'])} | Status: {a['verification_status']}")
    else:
        print(f"[{k}] -> MISSING!")

# Check for any short texts / possible issues
short_texts = [a for a in articles if len(a['full_text']) < 30 and not a['is_omitted']]
print(f"\nNon-omitted articles with text < 30 chars ({len(short_texts)}):")
for st in short_texts:
    print(f"  Art {st['article_number']} ({st['title']}): len={len(st['full_text'])}, snippet={repr(st['full_text'])}")
