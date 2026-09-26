import pymupdf
import re

doc = pymupdf.open('data/Constitution.pdf')

# Let's inspect how titles end in all articles across the PDF
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_refined_tokens as trt
pages = trt.pages

art_start_pattern = re.compile(
    r"^(?:/\*fn:[^\*]+\*/\s*)*[\[\uf02a\*]*\s*(\d+[A-Z]{0,2})\]?\.\s*(.*)$"
)

for p in pages:
    lines = p['lines']
    for idx, (line, pno) in enumerate(lines):
        m = art_start_pattern.match(line)
        if m:
            num = m.group(1)
            rest = m.group(2)
            if any(rest.lower().startswith(x) for x in ['subs.', 'ins.', 'omitted by', 'the words', 'the figures', 'the brackets', 'the heading', 'cl.', 'cls.', 'vide', 'see ']):
                continue
            
            # Check how title is structured
            # Collect lines until .\ufffd or .\u2014 or .— or [Omitted...] or next article
            title_parts = [rest] if rest else []
            full_title = ""
            init_body = ""
            
            combined_text = rest
            if re.search(r'\.\s*[—–\ufffd\u2014]\s*', combined_text):
                parts = re.split(r'\.\s*[—–\ufffd\u2014]\s*', combined_text, maxsplit=1)
                full_title = parts[0]
                init_body = parts[1]
            else:
                j = idx + 1
                while j < len(lines):
                    next_l, _ = lines[j]
                    if art_start_pattern.match(next_l) or next_l.startswith("PART ") or next_l.startswith("CHAPTER "):
                        break
                    if re.search(r'\.\s*[—–\ufffd\u2014]\s*', next_l):
                        parts = re.split(r'\.\s*[—–\ufffd\u2014]\s*', next_l, maxsplit=1)
                        title_parts.append(parts[0])
                        init_body = parts[1]
                        break
                    else:
                        title_parts.append(next_l)
                    j += 1
                full_title = " ".join(title_parts).strip()
                
            if num in ['246', '124', '14', '19', '21', '51A', '370']:
                print(f"Article {num} (P{pno}):")
                print(f"  Title: {repr(full_title)}")
                print(f"  Initial Body: {repr(init_body[:60])}")
