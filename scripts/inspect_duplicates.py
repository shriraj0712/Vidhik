import pymupdf
import re
from collections import Counter

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_refined_tokens as trt

pages = trt.pages

# Let's inspect all extracted article numbers
art_start_pattern = re.compile(
    r"^(?:/\*fn:[^\*]+\*/\s*)*[\[\uf02a\*]*\s*(\d+[A-Z]{0,2})\]?\.\s*(.*)$"
)

articles_found = []
for p in pages:
    for line, pno in p['lines']:
        m = art_start_pattern.match(line)
        if m:
            num = m.group(1)
            rest = m.group(2)
            if not any(rest.lower().startswith(x) for x in ['subs.', 'ins.', 'omitted by', 'the words', 'the figures', 'the brackets', 'cl.', 'vide', 'see ', 'for the purpose']):
                articles_found.append((num, rest, pno))

counts = Counter([a[0] for a in articles_found])
duplicates = {k: v for k, v in counts.items() if v > 1}
print(f"Total entries: {len(articles_found)}, Unique article numbers: {len(counts)}")
print(f"Duplicates count: {len(duplicates)}")
if duplicates:
    print("Duplicate article numbers:", duplicates)
    for dup in duplicates:
        print(f"--- Matches for {dup} ---")
        for num, rest, pno in articles_found:
            if num == dup:
                print(f"  P{pno}: {rest[:60]}")
