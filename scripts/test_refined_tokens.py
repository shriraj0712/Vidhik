import pymupdf
import re
from pathlib import Path

doc = pymupdf.open('data/Constitution.pdf')

def extract_tokens(doc, start_p, end_p):
    # Parse each page into structured lines with metadata
    pages = []
    for pno in range(start_p, end_p):
        p = doc[pno]
        d = p.get_text('dict')
        page_lines = []
        page_footnotes = []
        
        for b in d['blocks']:
            if 'lines' not in b:
                continue
            y0_b, y1_b = b['bbox'][1], b['bbox'][3]
            if y0_b < 50:
                continue
            if y1_b > 470 and len(b['lines']) == 1:
                txt = "".join(s['text'] for s in b['lines'][0]['spans']).strip()
                if txt.isdigit():
                    continue
            
            # Check for footnote block
            block_text = "".join("".join(s['text'] for s in l['spans']) for l in b['lines']).strip()
            is_footnote_block = False
            # Check if font size in block is <= 8.2 and starts with footnote pattern
            first_span_size = b['lines'][0]['spans'][0]['size'] if b['lines'][0]['spans'] else 9.0
            if (y0_b > 350 and first_span_size <= 8.2 and 
                re.match(r'^\d+\.\s+(Subs\.|Ins\.|The words|The figures|The brackets|The heading|The proviso|Omitted|Cl\.|Cls\.|Added|Certain|Re-numbered|For |See |Vide |Renumbered|Paragraph|Article|Articles|In article|Original|Section|Art\.|Arts\.|In exercise|Proviso|\*)', block_text, re.IGNORECASE)):
                is_footnote_block = True
                
            for l in b['lines']:
                line_y0 = l['bbox'][1]
                spans = l['spans']
                line_parts = []
                for s in spans:
                    t = s['text']
                    sz = s['size']
                    if sz <= 6.8 and (t.strip().isdigit() or t.strip() in ('*', '**', '***', '\uf02a', '\uf02a\uf02a')):
                        line_parts.append(f" /*fn:{t.strip()}*/ ")
                    else:
                        line_parts.append(t)
                l_str = "".join(line_parts).strip()
                if not l_str:
                    continue
                    
                if is_footnote_block or (line_y0 > 380 and spans[0]['size'] <= 8.2 and re.match(r'^\d+\.\s+(Subs\.|Ins\.|The words|The figures|The brackets|The heading|The proviso|Omitted|Cl\.|Cls\.|Added|Certain|Re-numbered|For |See |Vide |Renumbered|Paragraph|Article|Articles|In article|Original|Section|Art\.|Arts\.|In exercise|Proviso|\*)', l_str, re.IGNORECASE)):
                    page_footnotes.append(l_str)
                else:
                    page_lines.append((l_str, pno + 1))
        pages.append({'pno': pno + 1, 'lines': page_lines, 'footnotes': page_footnotes})
    return pages

pages = extract_tokens(doc, 31, 283)
print(f"Parsed {len(pages)} pages.")

# Scan for articles
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
            if not any(rest.lower().startswith(x) for x in ['subs.', 'ins.', 'omitted by', 'the words', 'the figures', 'the brackets', 'cl.', 'vide', 'see ']):
                articles_found.append((num, rest, pno))

print(f"Total articles found: {len(articles_found)}")
# Check all 1 to 395
found_nums = {a[0] for a in articles_found}
missing = [str(i) for i in range(1, 396) if str(i) not in found_nums]
print(f"Missing base numbers ({len(missing)}):", missing)
