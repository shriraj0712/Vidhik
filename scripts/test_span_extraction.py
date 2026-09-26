import pymupdf
import re
from pathlib import Path

doc = pymupdf.open('data/Constitution.pdf')

def extract_clean_page_lines(doc, start_p, end_p):
    all_pages = []
    for pno in range(start_p, end_p):
        p = doc[pno]
        d = p.get_text('dict')
        page_lines = []
        page_footnotes = []
        
        for b in d['blocks']:
            if 'lines' not in b:
                continue
            y0_block = b['bbox'][1]
            y1_block = b['bbox'][3]
            
            # Skip running headers
            if y0_block < 50:
                continue
            # Skip page numbers at bottom
            if y1_block > 470 and len(b['lines']) == 1:
                # check if single digit
                txt = "".join(s['text'] for s in b['lines'][0]['spans']).strip()
                if txt.isdigit():
                    continue
            
            # Check if this block is footnote block (usually at bottom of page with smaller font ~8pt and starting with 1., 2. etc.)
            block_text = "".join("".join(s['text'] for s in l['spans']) for l in b['lines']).strip()
            is_footnote_block = False
            if y0_block > 350 and re.match(r'^\d+\.\s+(Subs\.|Ins\.|The |Omitted|Cl\.|Added|Certain|Re-numbered|For |See |Vide |Renumbered|Paragraph|Article|In article|The brackets|Original|Section|Art\.|In exercise|Proviso)', block_text, re.IGNORECASE):
                is_footnote_block = True
            
            for l in b['lines']:
                line_text_parts = []
                line_y0 = l['bbox'][1]
                line_y1 = l['bbox'][3]
                
                for s in l['spans']:
                    txt = s['text']
                    sz = s['size']
                    fl = s['flags']
                    
                    # If span is superscript footnote marker (font size <= 6.5 pt)
                    if sz <= 6.8 and (txt.strip().isdigit() or txt.strip() in ('*', '**', '***', '\uf02a', '\uf02a\uf02a')):
                        # Superscript footnote reference
                        line_text_parts.append(f" /*fn:{txt.strip()}*/ ")
                    else:
                        line_text_parts.append(txt)
                
                line_str = "".join(line_text_parts).strip()
                if not line_str:
                    continue
                
                if is_footnote_block or (line_y0 > 380 and re.match(r'^\d+\.\s+(Subs\.|Ins\.|The |Omitted|Cl\.|Added|Certain|Re-numbered|For |See |Vide |Renumbered|Paragraph|Article|In article|The brackets|Original|Section|Art\.|In exercise|Proviso)', line_str, re.IGNORECASE)):
                    page_footnotes.append(line_str)
                else:
                    page_lines.append((line_str, pno + 1))
                    
        all_pages.append({
            'page_number': pno + 1,
            'lines': page_lines,
            'footnotes': page_footnotes
        })
    return all_pages

pages = extract_clean_page_lines(doc, 31, 283)
print(f"Extracted {len(pages)} pages.")

# Test article matching
PART_REGEX = re.compile(r"^\s*PART\s+([IVXLCDMA-Z0-9]+)\s*$", re.IGNORECASE)
CHAPTER_REGEX = re.compile(r"^\s*CHAPTER\s+([IVXLCDMA-Z0-9]+)\s*$", re.IGNORECASE)

# Line starting with article pattern
# Notice line might have /*fn:...*/ stripped
CLEAN_ART_REGEX = re.compile(
    r"^(?:/\*fn:\d+\*/\s*)?(?:\[|\uf02a)?\s*(\d+[A-Z]{0,2})\]?\.\s*(.*)$"
)

found_articles = []
for p in pages:
    for line, pno in p['lines']:
        # clean out inline fn markers at start
        l_clean = re.sub(r'^(?:/\*fn:\d+\*/\s*)+', '', line).strip()
        m = CLEAN_ART_REGEX.match(l_clean)
        if m:
            art_num = m.group(1)
            rest = m.group(2)
            # filter out footnotes or false positives
            if not any(rest.lower().startswith(x) for x in ['subs.', 'ins.', 'omitted by', 'the words', 'cl.', 'vide', 'see ', 'for the purpose']):
                found_articles.append((art_num, rest[:40], pno))

print(f"Total potential articles matched: {len(found_articles)}")
print("First 10:", found_articles[:10])
print("Sample around 30-40:", [x for x in found_articles if re.match(r'^(3[0-9]|4[0-9]|5[0-9])', x[0])])
print("Sample around 243:", [x for x in found_articles if x[0].startswith('243')])
print("Sample around 370-395:", [x for x in found_articles if re.match(r'^(37[0-9]|38[0-9]|39[0-9])', x[0])])
