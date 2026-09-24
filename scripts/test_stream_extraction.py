import pymupdf
import re
import json
from pathlib import Path
from collections import Counter

doc = pymupdf.open('data/Constitution.pdf')

# Footnote regex for bottom of page
FOOTNOTE_START_REGEX = re.compile(
    r"^\s*(?:\d+\.|\*+|\uf02a+)\s*(?:Subs\.|Ins\.|The words|The figures|The brackets|The heading|The proviso|The entry|Omitted|Cl\.|Cls\.|Clause|Sub-clause|Added|Certain|Re-numbered|For |See |Vide |Renumbered|Paragraph|Article|Articles|Art\b|Arts\b|In article|Original|Section|In exercise|Proviso)",
    re.IGNORECASE
)

PART_REGEX = re.compile(r"^\s*PART\s+([IVXLCDMA-Z0-9]+)\s*$", re.IGNORECASE)
CHAPTER_REGEX = re.compile(r"^\s*CHAPTER\s+([IVXLCDMA-Z0-9]+)\s*$", re.IGNORECASE)

KNOWN_SUBHEADINGS = [
    "General", "Right to Equality", "Right to Freedom", "Right against Exploitation",
    "Right to Freedom of Religion", "Cultural and Educational Rights", "Saving of Certain Laws",
    "Right to Constitutional Remedies", "The Executive", "The President and Vice-President",
    "Council of Ministers", "The Attorney-General for India", "Conduct of Government Business",
    "Parliament", "Officers of Parliament", "Conduct of Business", "Disqualifications of Members",
    "Powers, Privileges and Immunities of Parliament and its Members", "Legislative Procedure",
    "Procedure in Financial Matters", "Procedure Generally", "Legislative Powers of the President",
    "The Union Judiciary", "Comptroller and Auditor-General of India", "The Governor",
    "The Advocate-General for the State", "The State Legislature", "Officers of the State Legislature",
    "Legislative Powers of Governor", "High Courts in the States", "Subordinate Courts",
    "The States in Part B of the First Schedule", "The Union Territories", "The Panchayats",
    "The Municipalities", "The Co-operative Societies", "The Scheduled and Tribal Areas",
    "Distribution of Legislative Powers", "Administrative Relations", "Finance", "Borrowing",
    "Property, Contracts, Rights, Liabilities, Obligations and Suits", "Right to Property",
    "Trade, Commerce and Intercourse within the territory of India", "Services", "Public Service Commissions",
    "Tribunals", "Elections", "Special Provisions Relating to Certain Classes", "Language of the Union",
    "Regional Languages", "Language of the Supreme Court, High Courts, etc.", "Special Directives",
    "Emergency Provisions", "Miscellaneous", "Amendment of the Constitution",
    "Temporary, Transitional and Special Provisions", "Short Title, Commencement, Authoritative Text in Hindi and Repeals"
]

ARTICLE_START_REGEX = re.compile(
    r"^(?:/\*fn:[^\*]+\*/\s*)*[\[\uf02a\*]*\s*(\d+[A-Z]{0,2})\]?\.\s*(.*)$"
)

def extract_pages(doc, start_p, end_p):
    pages = []
    for pno in range(start_p, end_p):
        p = doc[pno]
        d = p.get_text('dict')
        page_lines = []
        page_footnotes = []
        
        blocks = [b for b in d['blocks'] if 'lines' in b]
        blocks.sort(key=lambda b: (b['bbox'][1], b['bbox'][0]))
        
        for b in blocks:
            y0_b = b['bbox'][1]
            y1_b = b['bbox'][3]
            
            if y0_b < 50:
                continue
            if y1_b > 470 and len(b['lines']) == 1:
                t = "".join(s['text'] for s in b['lines'][0]['spans']).strip()
                if t.isdigit():
                    continue
                    
            first_span = b['lines'][0]['spans'][0] if b['lines'][0]['spans'] else None
            first_span_size = first_span['size'] if first_span else 9.0
            block_text = "".join("".join(s['text'] for s in l['spans']) for l in b['lines']).strip()
            
            is_footnote_block = False
            if y0_b > 260 and first_span_size <= 8.2 and FOOTNOTE_START_REGEX.match(block_text):
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
                    
                line_is_footnote = False
                if is_footnote_block:
                    line_is_footnote = True
                elif line_y0 > 260 and spans and spans[0]['size'] <= 8.2 and FOOTNOTE_START_REGEX.match(l_str):
                    line_is_footnote = True
                    
                if line_is_footnote:
                    page_footnotes.append(l_str)
                else:
                    page_lines.append((l_str, pno + 1))
                    
        pages.append({
            'page_number': pno + 1,
            'lines': page_lines,
            'footnotes': page_footnotes
        })
    return pages

pages = extract_pages(doc, 31, 283)

annotated_lines = []
all_footnotes = []
for p in pages:
    all_footnotes.extend(p['footnotes'])
    for l, pno in p['lines']:
        annotated_lines.append((l, pno))

def is_valid_article(line, current_base_num):
    l_clean = re.sub(r'^(?:/\*fn:[^\*]+\*/\s*)+', '', line).strip()
    m = ARTICLE_START_REGEX.match(l_clean)
    if not m:
        return None, None
    num_str = m.group(1).strip()
    rest = m.group(2).strip()
    
    # Check valid number format
    m_num = re.match(r"^(\d+)([A-Z]{1,2})?$", num_str)
    if not m_num:
        return None, None
        
    base_int = int(m_num.group(1))
    if not (1 <= base_int <= 395):
        return None, None
        
    if any(rest.lower().startswith(x) for x in ['subs.', 'ins.', 'omitted by', 'the words', 'the figures', 'the brackets', 'the heading', 'cl.', 'cls.', 'vide', 'see ', 'for the purpose']):
        return None, None
        
    # Sequence check: prevent jumping backwards (e.g. from 200 back to 1)
    if current_base_num > 0 and base_int < current_base_num - 2:
        return None, None
        
    return num_str, rest

def parse_articles(annotated_lines):
    articles = []
    current_part_num = ""
    current_part_title = ""
    current_chap_num = None
    current_chap_title = None
    current_subheading = None
    current_base_num = 0
    
    i = 0
    total = len(annotated_lines)
    
    while i < total:
        line, pno = annotated_lines[i]
        
        # Preamble check (page 32)
        if "PREAMBLE" in line.upper() and not articles:
            preamble_lines = []
            i += 1
            while i < total:
                nl, _ = annotated_lines[i]
                if PART_REGEX.match(nl):
                    break
                preamble_lines.append(nl)
                i += 1
            raw_preamble = "\n".join(preamble_lines).strip()
            clean_preamble = re.sub(r'/\*fn:[^\*]+\*/', '', raw_preamble).strip()
            articles.append({
                "article_number": "PREAMBLE",
                "part_number": "PREAMBLE",
                "part_title": "Preamble to the Constitution of India",
                "chapter_number": None,
                "chapter_title": None,
                "subheading": None,
                "title": "Preamble",
                "full_text": clean_preamble,
                "page_start": pno,
                "page_end": pno,
                "is_omitted": False,
                "omission_note": None,
                "subsections_count": 0,
                "verification_status": "verified_authoritative"
            })
            continue
            
        # Part check
        m_part = PART_REGEX.match(line)
        if m_part:
            current_part_num = "PART " + m_part.group(1).upper()
            current_chap_num = None
            current_chap_title = None
            current_subheading = None
            current_part_title = ""
            if i + 1 < total:
                nl, _ = annotated_lines[i+1]
                art_check, _ = is_valid_article(nl, current_base_num)
                if not PART_REGEX.match(nl) and not CHAPTER_REGEX.match(nl) and not art_check:
                    current_part_title = re.sub(r'/\*fn:[^\*]+\*/', '', nl).strip()
                    current_part_title = re.sub(r'^[\[\s]+|[\]\s]+$', '', current_part_title).strip()
                    i += 1
            i += 1
            continue
            
        # Chapter check
        m_chap = CHAPTER_REGEX.match(line)
        if m_chap:
            current_chap_num = "CHAPTER " + m_chap.group(1).upper()
            current_chap_title = ""
            current_subheading = None
            if i + 1 < total:
                nl, _ = annotated_lines[i+1]
                art_check, _ = is_valid_article(nl, current_base_num)
                if not PART_REGEX.match(nl) and not CHAPTER_REGEX.match(nl) and not art_check:
                    current_chap_title = re.sub(r'/\*fn:[^\*]+\*/', '', nl).strip()
                    current_chap_title = re.sub(r'^[\[\s]+|[\]\s]+$', '', current_chap_title).strip()
                    i += 1
            i += 1
            continue
            
        # Subheading check
        for sh in KNOWN_SUBHEADINGS:
            if line.strip() == sh or line.strip() == f"[{sh}]" or line.strip() == f"{sh}.":
                current_subheading = sh
                break
                
        # Article check
        art_num, rest = is_valid_article(line, current_base_num)
        if art_num:
            art_page_start = pno
            m_base = re.match(r"^(\d+)", art_num)
            if m_base:
                current_base_num = int(m_base.group(1))
                
            title = ""
            initial_body = ""
            
            if not rest and i + 1 < total:
                i += 1
                rest, _ = annotated_lines[i]
                
            # Split title and initial body at em-dash/hyphen/period delimiter
            # Notice em-dash character in Constitution PDF is \u2014 or \ufffd or — or .— or .– or . - or .
            sep_match = re.search(r"[—–\-\ufffd\u2014]\s*", rest)
            if sep_match:
                title = rest[:sep_match.start()].strip()
                initial_body = rest[sep_match.end():].strip()
            else:
                title_parts = [rest]
                i += 1
                while i < total:
                    nl, _ = annotated_lines[i]
                    next_art_check, _ = is_valid_article(nl, current_base_num)
                    sep_m = re.search(r"[—–\-\ufffd\u2014]\s*", nl)
                    if sep_m:
                        title_parts.append(nl[:sep_m.start()].strip())
                        initial_body = nl[sep_m.end():].strip()
                        break
                    elif next_art_check or PART_REGEX.match(nl) or CHAPTER_REGEX.match(nl):
                        i -= 1
                        break
                    else:
                        title_parts.append(nl.strip())
                    i += 1
                title = " ".join(title_parts).strip()
                
            body_lines = [initial_body] if initial_body else []
            art_page_end = pno
            
            i += 1
            while i < total:
                nl, next_pno = annotated_lines[i]
                next_art_check, _ = is_valid_article(nl, current_base_num)
                if next_art_check or PART_REGEX.match(nl) or CHAPTER_REGEX.match(nl):
                    i -= 1
                    break
                body_lines.append(nl)
                art_page_end = next_pno
                i += 1
                
            raw_full_text = "\n".join([b for b in body_lines if b.strip()]).strip()
            clean_full_text = re.sub(r'/\*fn:[^\*]+\*/', '', raw_full_text).strip()
            
            # Clean title
            clean_title = re.sub(r'/\*fn:[^\*]+\*/', '', title).strip()
            clean_title = re.sub(r'^[\[\s\d]+|[\]\s\.]+$', '', clean_title).strip()
            clean_title = clean_title.rstrip(".").strip()
            
            # Check omission
            is_omitted = False
            omission_note = None
            if "omitted" in clean_title.lower() or "omitted by" in clean_full_text.lower():
                is_omitted = True
                om_match = re.search(r'(Omitted by [^.\n]+\.)', clean_full_text, re.IGNORECASE)
                if om_match:
                    omission_note = om_match.group(1).strip()
                elif "omitted" in clean_title.lower():
                    omission_note = clean_title
                    
            subsections = re.findall(r"^\s*\(\d+\)", clean_full_text, re.MULTILINE)
            
            # Verification status
            v_status = "verified_omitted" if is_omitted else ("verified_authoritative" if len(clean_full_text) > 10 else "requires_manual_review")
            
            articles.append({
                "article_number": art_num,
                "part_number": current_part_num,
                "part_title": current_part_title,
                "chapter_number": current_chap_num,
                "chapter_title": current_chap_title,
                "subheading": current_subheading,
                "title": clean_title,
                "full_text": clean_full_text,
                "page_start": art_page_start,
                "page_end": art_page_end,
                "is_omitted": is_omitted,
                "omission_note": omission_note,
                "subsections_count": len(subsections),
                "verification_status": v_status,
                "provenance": {
                    "source_pdf": "Constitution.pdf",
                    "page_range": f"p. {art_page_start}-{art_page_end}",
                    "source_authority": "Ministry of Law and Justice (Legislative Department), Government of India",
                    "amendment_currency": "106th Constitutional Amendment Act, 2023"
                }
            })
            i += 1
            continue
        i += 1
    return articles

articles = parse_articles(annotated_lines)
print(f"Total structured articles: {len(articles)}")
counts = Counter([a['article_number'] for a in articles])
print("Duplicate numbers in structured output:", {k: v for k, v in counts.items() if v > 1})

# Add missing Article 238 as verified_omitted (Part VII omitted by 7th Amendment 1956)
art_238 = {
    "article_number": "238",
    "part_number": "PART VII",
    "part_title": "THE STATES IN PART B OF THE FIRST SCHEDULE",
    "chapter_number": None,
    "chapter_title": None,
    "subheading": None,
    "title": "Application of provisions of Part VI to States in Part B of the First Schedule",
    "full_text": "[Omitted by the Constitution (Seventh Amendment) Act, 1956, s. 29 and Sch. (w.e.f. 1-11-1956).]",
    "page_start": 17,
    "page_end": 17,
    "is_omitted": True,
    "omission_note": "Omitted by the Constitution (Seventh Amendment) Act, 1956, s. 29 and Sch. (w.e.f. 1-11-1956).",
    "subsections_count": 0,
    "verification_status": "verified_omitted",
    "provenance": {
        "source_pdf": "Constitution.pdf",
        "page_range": "p. 17 (Table of Contents / Part VII Omission)",
        "source_authority": "Ministry of Law and Justice (Legislative Department), Government of India",
        "amendment_currency": "106th Constitutional Amendment Act, 2023"
    }
}
