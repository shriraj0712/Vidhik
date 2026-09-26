"""
VIDHIK - Maharashtra MVP & Central Laws Extraction & Multi-Pass Section Parser
=============================================================================
Authoritative Sources:
  - data/Legal_Dataset/Maharashtra_MVP/*.pdf (128 MVP Legal Documents)
  - data/Legal_Dataset/Maharashtra_MVP/extracted_text/*.txt (Reference raw text)
  - data/Legal_Dataset/PDFs/*.pdf (Central Acts Archive)
  - data/Maharashtra_Laws/ (State Laws Archive)

Multi-Pass Pipeline Architecture:
  Pass 1: Text Sanitization & Bounding Box Aware Page Processing (Headers/Footers, Page Metadata)
  Pass 2: Section Boundary Detection (Numbered, Alphanumeric, Multi-line, Hindi/Diglot, Inline, Roman)
  Pass 3: Section Metadata & Provenance Extraction (Chapter, Part, Page Range, Jurisdiction)
  Pass 4: Internal Structure Preservation (Subsections, Clauses, Sub-clauses, Provisos, Explanations)

Outputs:
  - data/Legal_Dataset/Maharashtra_MVP/staging/laws_staging.json
  - data/Legal_Dataset/Maharashtra_MVP/staging/sections_staging.json
  - data/Legal_Dataset/Maharashtra_MVP/validation_reports/section_parser_report.json
  - data/Legal_Dataset/Maharashtra_MVP/validation_reports/manual_review_required.csv
  - data/Legal_Dataset/Maharashtra_MVP/validation_reports/filename_anomalies.csv
"""

import os
import re
import csv
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter
import pymupdf

# Set UTF-8 encoding for standard output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
MVP_PDF_DIR = BASE_DIR / "data" / "Legal_Dataset" / "Maharashtra_MVP"
MVP_EXT_TXT_DIR = MVP_PDF_DIR / "extracted_text"
GEN_PDF_DIR = BASE_DIR / "data" / "Legal_Dataset" / "PDFs"
GEN_EXT_TXT_DIR = BASE_DIR / "data" / "Legal_Dataset" / "extracted_text"
MAH_LAWS_PDF_DIR = BASE_DIR / "data" / "Maharashtra_Laws" / "PDFs"

STAGING_DIR = MVP_PDF_DIR / "staging"
REPORTS_DIR = MVP_PDF_DIR / "validation_reports"

STAGING_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Output Paths
LAWS_STAGING_PATH = STAGING_DIR / "laws_staging.json"
SECTIONS_STAGING_PATH = STAGING_DIR / "sections_staging.json"
PARSER_REPORT_PATH = REPORTS_DIR / "section_parser_report.json"
MANUAL_REVIEW_CSV_PATH = REPORTS_DIR / "manual_review_required.csv"
FILENAME_ANOMALIES_CSV_PATH = REPORTS_DIR / "filename_anomalies.csv"

# Known Maharashtra / Bombay Identifiers
MAHARASHTRA_BOMBAY_KEYWORDS = (
    "maharashtra", "bombay", "dekkhan", "hyderabad", "atiyat", "revenue_patels",
    "shore nuisances", "tobacco duty"
)

# Known Problematic Acts for Deep Validation Audit
KNOWN_PROBLEMATIC_ACTS = [
    "The Bilateral Netting of Qualified Financial Contracts Act, 2020",
    "The Delivery of Books and Newspapers (Public Libraries) Act, 1954",
    "The Human Immunodeficiency Virus and Acquired Immune Deficiency Syndrome (Prevention and Control) Act, 2017",
    "The India International Arbitration Centre Act, 2019",
    "The Jammu and Kashmir Official Languages Act, 2020.",
    "The Jammu and Kashmir Official Languages Act, 2020",
    "The National Commission for Backward Classes (Repeal) Act, 2018",
    "The Rashtriya Raksha University Act, 2020.",
    "The Rashtriya Raksha University Act, 2020",
    "The Repealing and Amending (Second) Act, 2015"
]

# Regex Patterns for Structural Elements
CHAPTER_REGEX = re.compile(
    r"^\s*(?:CHAPTER|अध्याय|अध्\s*याय)\s+([IVXLCDMA-Z0-9\-]+)(?:\s*[\.:—–\-]\s*(.*))?$",
    re.IGNORECASE
)

PART_REGEX = re.compile(
    r"^\s*(?:PART|भाग)\s+([IVXLCDMA-Z0-9\-]+)(?:\s*[\.:—–\-]\s*(.*))?$",
    re.IGNORECASE
)

SCHEDULE_HEADING_REGEX = re.compile(
    r"^\s*(?:\[?\d*\[?)*(?:THE\s+)?(?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH|ELEVENTH|TWELFTH|[IVXLCDM]+|\d+)?\s*SCHEDULE(?:\s+[IVXLCDM]+|\s+\d+)?(?:\s*\[.*?\])?\s*$",
    re.IGNORECASE
)

FOOTNOTE_START_REGEX = re.compile(
    r"^\s*(?:\d+[\.\)]|\*+|\uf02a+|\†|\‡)\s*(?:Subs\.|Ins\.|These |The |This |Omitted|Repealed|Deleted|Added|Substituted|Inserted|Re-numbered|Renumbered|For |Vide |See |Mah\.|Bom\.|Act\s+\d+|w\.e\.f\.|Published|Corrigendum|G\.N\.|G\.R\.|Notfn\.|Notification|Section|Sec\.|Cl\.|Cls\.|Paragraph|Article|Original)|"
    r"^\s*\d+[\.\)]\s*.*?\b(?:was|were|has been|is|shall be|stand|stands)\s+(?:inserted|substituted|deleted|omitted|repealed|re-numbered|added|amended|modified)\b|"
    r"^\s*\d+[\.\)]\s*.*?\b(?:Mah\.|Bom\.|w\.e\.f\.|w\.\s*e\.\s*f\.|Gazette|G\.N\.|G\.R\.)|"
    r"^\s*\d+[\.\)]\s*(?:18\d{2}|19\d{2}|20\d{2})\s*:",
    re.IGNORECASE
)

# Top-level Section Matching Pattern (English + Devanagari + Alphanumeric + Roman)
SECTION_START_REGEX = re.compile(
    r"^\s*(?:Section\s+|Sec\.\s*|धारा\s+|िारा\s+|िाराएं\s*)?((?:\d+[A-Za-z0-9\-]*|\d+[क-ह]?)|(?:[IVXLCDM]+))(?:\.|\)|—|–|-)\s*(.*)$"
)

ROMAN_SUBCLAUSE_PREFIXES = (
    "(i)", "(ii)", "(iii)", "(iv)", "(v)", "(vi)", "(vii)", "(viii)", "(ix)", "(x)",
    "(xi)", "(xii)", "(xiii)", "(xiv)", "(xv)", "(xvi)", "(xvii)", "(xviii)", "(xix)", "(xx)"
)


def slugify(text):
    """Generate URL-safe unique slug for laws and sections."""
    text = str(text).lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def detect_jurisdiction(law_name):
    """Classifies whether an Act is a Maharashtra State Act or Central Act."""
    lower_name = law_name.lower()
    for kw in MAHARASHTRA_BOMBAY_KEYWORDS:
        if kw in lower_name:
            return "Maharashtra", "State Act"
    if "code" in lower_name:
        return "Central", "Code"
    if "constitution" in lower_name:
        return "India", "Constitution"
    return "Central", "Central Act"


def sanitize_text(text):
    """Pass 1: Text Sanitization & Normalization."""
    if not text:
        return ""
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Normalize zero-width and invisible unicode characters
    text = re.sub(r"[\u200b\u200c\u200d\ufeff\xa0]", " ", text)
    # Remove IndiaCode running headers
    text = re.sub(r"(?im)^\s*IndiaCode\s*$", "", text)
    # Normalize unicode quotes and dashes
    text = text.replace("“", "\"").replace("”", "\"").replace("’", "'").replace("‘", "'")
    return text


def extract_pages_from_pdf(pdf_path):
    """Extract page-by-page text with header/footer rejection."""
    doc = pymupdf.open(str(pdf_path))
    pages_data = []
    
    for pno in range(len(doc)):
        p = doc[pno]
        d = p.get_text("dict")
        page_height = p.rect.height
        
        body_lines = []
        for b in d.get("blocks", []):
            if "lines" not in b:
                continue
            y0_b, y1_b = b["bbox"][1], b["bbox"][3]
            
            # Header filtration (top margin)
            if y0_b < 45 and len(b["lines"]) <= 2:
                header_text = "".join("".join(s["text"] for s in l["spans"]) for l in b["lines"]).strip()
                if "IndiaCode" in header_text or header_text.isdigit() or len(header_text) < 30:
                    continue
                    
            # Footer filtration (bottom standalone page number)
            if y1_b > (page_height - 35) and len(b["lines"]) == 1:
                footer_text = "".join(s["text"] for s in b["lines"][0]["spans"]).strip()
                if footer_text.isdigit():
                    continue
                    
            for l in b["lines"]:
                line_str = "".join(s["text"] for s in l["spans"]).strip()
                if line_str:
                    body_lines.append((line_str, y0_b, page_height))
                    
        pages_data.append({
            "page_number": pno + 1,
            "lines": body_lines
        })
        
    return doc, pages_data


def detect_enactment_start_page(doc, pages_data):
    """
    Detects the 1-indexed page where the substantive Enactment begins,
    distinguishing Table of Contents / Arrangement of Sections / List of Amendment Acts from statutory body.
    """
    for pno in range(len(doc)):
        raw_text = doc[pno].get_text()
        # Look for enacting formula
        if any(k in raw_text for k in [
            "An Act to", "AN ACT TO", "BE it enacted", "BE IT ENACTED", 
            "WHEREAS with a view", "WHEREAS it is expedient", "MAHARASHTRA ACT NO", "BOMBAY ACT NO"
        ]):
            if pno > 0:
                return pno + 1
        lines = [l[0] for l in pages_data[pno]["lines"]]
        for idx, l in enumerate(lines):
            # Check Section 1 with substantive enacting formula
            if re.match(r"^\s*(?:1[\.\)]|Section\s+1[\.\:\s—–\-]|\d+\s*1[\.\)])\s*(?:Short\s+title|Short\s+Title|संक्षिप्त|संगिप्|संधिप्त)", l, re.IGNORECASE):
                combined = " ".join(lines[idx:idx+8]).lower()
                if any(k in combined for k in [
                    "this act may be called", "this act may be cited", "it extends to", 
                    "shall come into force", "कहा जा सकता", "कहलाएगा", "लागू होगा", "विस्तार"
                ]):
                    return pno + 1
                    
    return 1


def parse_internal_structure(full_text):
    """
    Pass 4: Internal structure preservation and feature tagging.
    Identifies subsections, clauses, provisos, explanations, illustrations, and definitions.
    """
    subsections = re.findall(r"^\s*\(\d+[A-Za-z]?\)", full_text, re.MULTILINE)
    clauses = re.findall(r"^\s*\([a-z]\)", full_text, re.MULTILINE)
    subclauses = re.findall(r"^\s*\([ivxldcm]+\)", full_text, re.MULTILINE)
    
    has_proviso = bool(re.search(r"\bProvided\s+(?:that|further\s+that)\b", full_text, re.IGNORECASE))
    has_explanation = bool(re.search(r"\bExplanation(?:\s*\d*|\s*[\.—–\-])", full_text, re.IGNORECASE))
    has_illustration = bool(re.search(r"\bIllustration(?:\s*\d*|\s*[\.—–\-])", full_text, re.IGNORECASE))
    has_schedule_ref = bool(re.search(r"\b(?:Schedule|First Schedule|Second Schedule)\b", full_text, re.IGNORECASE))
    
    return {
        "subsections_count": len(subsections),
        "clauses_count": len(clauses),
        "subclauses_count": len(subclauses),
        "has_proviso": has_proviso,
        "has_explanation": has_explanation,
        "has_illustration": has_illustration,
        "has_schedule_ref": has_schedule_ref
    }


def parse_act_sections(doc, pages_data, enact_start_page, law_metadata):
    """
    Pass 2 & Pass 3: Section boundary detection and metadata extraction.
    """
    sections = []
    current_chapter_num = None
    current_chapter_title = None
    current_part_num = None
    current_part_title = None
    
    annotated_lines = []
    in_schedule = False
    
    for p in pages_data:
        pno = p["page_number"]
        if pno < enact_start_page:
            # Skip preliminary Table of Contents pages
            continue
        for l_str, y0, page_height in p["lines"]:
            # Footnote filter at bottom of page
            if y0 > (page_height - 120) and FOOTNOTE_START_REGEX.match(l_str):
                continue
            # Detect schedule boundary strictly after enactment start
            clean_l = l_str.strip().rstrip("]")
            if SCHEDULE_HEADING_REGEX.match(clean_l) and len(clean_l) < 60 and pno > (enact_start_page + 1):
                in_schedule = True
            annotated_lines.append((l_str, pno, in_schedule))
            
    total_lines = len(annotated_lines)
    i = 0
    current_section = None
    current_body_lines = []
    
    while i < total_lines:
        line, pno, sched_flag = annotated_lines[i]
        line_clean = sanitize_text(line).strip()

        if not line_clean:
            i += 1
            continue
                
        if sched_flag:
            # Reached schedule at end of act; preserve text in schedule rather than false sections
            i += 1
            continue
            
        # 1. Check Part Heading
        m_part = PART_REGEX.match(line_clean)
        if m_part:
            current_part_num = "PART " + m_part.group(1).upper()
            current_part_title = m_part.group(2).strip() if m_part.group(2) else ""
            if not current_part_title and i + 1 < total_lines:
                next_l, _, _ = annotated_lines[i+1]
                if not CHAPTER_REGEX.match(next_l) and not SECTION_START_REGEX.match(next_l):
                    current_part_title = next_l.strip()
                    i += 1
            i += 1
            continue
            
        # 2. Check Chapter Heading
        m_chap = CHAPTER_REGEX.match(line_clean)
        if m_chap:
            current_chapter_num = "CHAPTER " + m_chap.group(1).upper()
            current_chapter_title = m_chap.group(2).strip() if m_chap.group(2) else ""
            if not current_chapter_title and i + 1 < total_lines:
                next_l, _, _ = annotated_lines[i+1]
                if not PART_REGEX.match(next_l) and not SECTION_START_REGEX.match(next_l):
                    current_chapter_title = next_l.strip()
                    i += 1
            i += 1
            continue
            
        # 3. Check Section Boundary
        # Filter out Roman numeral sub-clauses e.g. (i), (ii) and lower-case clauses e.g. (a)
        is_subclause = any(line_clean.lower().startswith(pfx) for pfx in ROMAN_SUBCLAUSE_PREFIXES)
        is_alpha_clause = bool(re.match(r"^\([a-z]\)", line_clean))
        
        m_sec = None
        if not is_subclause and not is_alpha_clause and not FOOTNOTE_START_REGEX.match(line_clean):
            m_sec = SECTION_START_REGEX.match(line_clean)
            if m_sec:
                sec_num = m_sec.group(1).strip()
                # Exclude 4-digit years like 1956, 2020 at line start acting as sections
                if sec_num.isdigit() and len(sec_num) == 4 and int(sec_num) > 1800:
                    m_sec = None
                    
        if m_sec:
            sec_num = m_sec.group(1).strip()
            rest = m_sec.group(2).strip()
            
            # Check if rest looks like a footnote sentence
            if re.search(r"\b(?:was|were|has been|is)\s+(?:inserted|substituted|deleted|omitted|repealed|re-numbered|added)\b", rest, re.IGNORECASE) or \
               re.search(r"\b(?:Mah\.|Bom\.|w\.e\.f\.|w\.\s*e\.\s*f\.|Vide G\.N\.|Vide Notfn\.)\b", rest, re.IGNORECASE):
                # This is a footnote, not a statutory section heading
                if current_section:
                    current_body_lines.append(line_clean)
                i += 1
                continue
                
            # Commit previous section
            if current_section:
                full_text = "\n".join(current_body_lines).strip()
                struct = parse_internal_structure(full_text)
                current_section["full_text"] = full_text
                current_section["source_page_end"] = pno
                current_section.update(struct)
                title_lower = current_section["section_title"].lower()
                current_section["is_definition_section"] = bool(
                    "definition" in title_lower or "interpretation" in title_lower or "पररिाषा" in title_lower or "परिभाषा" in title_lower
                )
                if re.search(r"(\[\s*\*\s*\*\s*\*\s*\]|\[Deleted\]|\[Repealed\]|Omitted by\b)", current_section["section_title"] + " " + full_text, re.IGNORECASE):
                    current_section["is_omitted"] = True
                    current_section["omission_note"] = "Deleted / Repealed / Omitted provision"
                sections.append(current_section)
            
            # Start new section
            sec_title = ""
            body_start = ""
            
            if rest:
                # Check if rest has title and inline body split by em-dash, en-dash, colon, or period
                dash_split = re.split(r"\s*[—–\-]\s*", rest, maxsplit=1)
                if len(dash_split) == 2 and len(dash_split[0]) < 80:
                    sec_title = dash_split[0].strip()
                    body_start = dash_split[1].strip()
                elif "." in rest and len(rest.split(".", 1)[0]) < 80 and not rest.startswith("("):
                    dot_split = rest.split(".", 1)
                    sec_title = dot_split[0].strip()
                    body_start = dot_split[1].strip()
                elif len(rest) < 80 and not rest.startswith("(") and not rest.startswith("Be it enacted") and not rest.startswith("Where"):
                    sec_title = rest
                else:
                    body_start = rest
            else:
                # Multi-line heading: next line might be the title
                if i + 1 < total_lines:
                    next_l, _, _ = annotated_lines[i+1]
                    if len(next_l) < 80 and not SECTION_START_REGEX.match(next_l) and not next_l.startswith("("):
                        sec_title = next_l.strip()
                        i += 1
                        
            current_section = {
                "section_id": f"{law_metadata['law_id']}-sec-{slugify(sec_num)}",
                "law_id": law_metadata["law_id"],
                "law_name": law_metadata["law_name"],
                "section_number": sec_num,
                "section_title": sec_title,
                "full_text": "",
                "chapter_number": current_chapter_num,
                "chapter_title": current_chapter_title,
                "part_number": current_part_num,
                "part_title": current_part_title,
                "source_pdf": law_metadata["source_pdf"],
                "source_page_start": pno,
                "source_page_end": pno,
                "jurisdiction": law_metadata["jurisdiction"],
                "extraction_status": "extracted_from_pdf",
                "is_omitted": False,
                "omission_note": None,
                "manual_review_required": False,
                "parser_notes": []
            }
            current_body_lines = [body_start] if body_start else []
            i += 1
            continue
            
        # Regular body line
        if current_section:
            current_body_lines.append(line_clean)
            
        i += 1
            
    # Commit final section
    if current_section:
        full_text = "\n".join(current_body_lines).strip()
        struct = parse_internal_structure(full_text)
        current_section["full_text"] = full_text
        current_section["source_page_end"] = annotated_lines[-1][1] if annotated_lines else enact_start_page
        current_section.update(struct)
        title_lower = current_section["section_title"].lower()
        current_section["is_definition_section"] = bool(
            "definition" in title_lower or "interpretation" in title_lower or "पररिाषा" in title_lower or "परिभाषा" in title_lower
        )
        if re.search(r"(\[\s*\*\s*\*\s*\*\s*\]|\[Deleted\]|\[Repealed\]|Omitted by\b)", current_section["section_title"] + " " + full_text, re.IGNORECASE):
            current_section["is_omitted"] = True
            current_section["omission_note"] = "Deleted / Repealed / Omitted provision"
        sections.append(current_section)
        
    return sections


def run_mvp_pipeline():
    print("=" * 75)
    print("VIDHIK - MAHARASHTRA MVP & CENTRAL LAWS EXTRACTION & VALIDATION (v2.2)")
    print("=" * 75)
    
    # Collect all MVP PDFs
    pdf_files = sorted(list(MVP_PDF_DIR.glob("*.pdf")))
    print(f"Total MVP PDFs Located: {len(pdf_files)}")
    
    # Collect extracted text files
    txt_files = sorted(list(MVP_EXT_TXT_DIR.glob("*.txt"))) if MVP_EXT_TXT_DIR.exists() else []
    print(f"Total Raw Extracted TXT Files: {len(txt_files)}")
    
    # 1. Audit Filename Anomalies
    filename_anomalies = []
    for p in pdf_files:
        name = p.name
        anomalies = []
        if name.endswith("..pdf"):
            anomalies.append("Double dot in extension (..pdf)")
        if ".pdf.pdf" in name:
            anomalies.append("Duplicate extension (.pdf.pdf)")
        if re.search(r"\s{2,}", name):
            anomalies.append("Multiple consecutive spaces in filename")
        if anomalies:
            filename_anomalies.append({
                "filename": name,
                "file_type": "PDF",
                "anomalies": "; ".join(anomalies)
            })
            
    for t in txt_files:
        name = t.name
        anomalies = []
        if name.endswith("..txt"):
            anomalies.append("Double dot in extension (..txt)")
        if ".pdf.txt" in name:
            anomalies.append("Double extension (.pdf.txt)")
        if anomalies:
            filename_anomalies.append({
                "filename": name,
                "file_type": "TXT",
                "anomalies": "; ".join(anomalies)
            })
            
    # Write filename anomalies report
    with open(FILENAME_ANOMALIES_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "file_type", "anomalies"])
        writer.writeheader()
        writer.writerows(filename_anomalies)
    print(f"  -> Filename anomalies report written: {FILENAME_ANOMALIES_CSV_PATH} ({len(filename_anomalies)} anomalies)")

    # 2. Process all 128 MVP Acts
    all_laws = []
    all_sections = []
    manual_review_records = []
    
    for idx, pdf_path in enumerate(pdf_files, 1):
        raw_name = pdf_path.name
        clean_name = raw_name.replace("..pdf", "").replace(".pdf", "").strip()
        law_slug = slugify(clean_name)
        jurisdiction, law_type = detect_jurisdiction(clean_name)
        
        year_match = re.search(r"\b(18\d{2}|19\d{2}|20\d{2})\b", clean_name)
        year = int(year_match.group(1)) if year_match else None
        
        law_meta = {
            "law_id": law_slug,
            "law_name": clean_name,
            "short_name": clean_name,
            "year": year,
            "law_type": law_type,
            "jurisdiction": jurisdiction,
            "source_pdf": raw_name,
            "total_pages": 0,
            "enactment_start_page": 1,
            "total_sections_extracted": 0,
            "is_diglot": False,
            "extraction_status": "extracted_from_source_pdf",
            "manual_review_required": False,
            "parser_notes": []
        }
        
        try:
            doc, pages_data = extract_pages_from_pdf(pdf_path)
            law_meta["total_pages"] = len(doc)
            
            total_chars = sum(len(" ".join(l[0] for l in p["lines"])) for p in pages_data)
            
            # Detect diglot / Hindi
            has_hindi = any(any("\u0900" <= ch <= "\u097F" for ch in " ".join(l[0] for l in p["lines"])) for p in pages_data)
            if has_hindi or "Hkkjr dk jkti=" in " ".join(" ".join(l[0] for l in p["lines"]) for p in pages_data[:3]):
                law_meta["is_diglot"] = True
                law_meta["parser_notes"].append("Contains Hindi / Diglot official text in source document")
                
            # Detect TOC vs Enactment start
            enact_start = detect_enactment_start_page(doc, pages_data)
            law_meta["enactment_start_page"] = enact_start
            
            # Extract Sections
            sections = parse_act_sections(doc, pages_data, enact_start, law_meta)
            law_meta["total_sections_extracted"] = len(sections)
            
            # Quality Checks & Anomaly Flagging
            if len(sections) == 0:
                law_meta["extraction_status"] = "incomplete_source_text"
                law_meta["manual_review_required"] = True
                law_meta["parser_notes"].append("No sections detected from source text")
                manual_review_records.append({
                    "law_id": law_slug,
                    "law_name": clean_name,
                    "section_number": "ALL",
                    "reason": "Zero sections detected from source text",
                    "source_pdf": raw_name
                })
            elif total_chars < 500 and len(doc) > 1:
                law_meta["extraction_status"] = "incomplete_source_text"
                law_meta["manual_review_required"] = True
                law_meta["parser_notes"].append("Source text appears truncated / OCR incomplete in PDF")
                manual_review_records.append({
                    "law_id": law_slug,
                    "law_name": clean_name,
                    "section_number": "ALL",
                    "reason": f"Truncated text from source PDF ({total_chars} characters extracted across {len(doc)} pages)",
                    "source_pdf": raw_name
                })
                
            all_laws.append(law_meta)
            all_sections.extend(sections)
            
            if idx % 20 == 0 or idx == len(pdf_files):
                print(f"  [{idx:3d}/{len(pdf_files)}] Processed: {clean_name[:45]:45s} | Pages: {len(doc):3d} | Sections: {len(sections):3d}")
                
        except Exception as e:
            law_meta["extraction_status"] = "parser_error"
            law_meta["manual_review_required"] = True
            law_meta["parser_notes"].append(f"Parser error: {str(e)}")
            all_laws.append(law_meta)
            manual_review_records.append({
                "law_id": law_slug,
                "law_name": clean_name,
                "section_number": "ERROR",
                "reason": f"Exception encountered: {str(e)}",
                "source_pdf": raw_name
            })
            print(f"  [{idx:3d}/{len(pdf_files)}] ERROR on {clean_name}: {e}")

    # 3. Test & Audit 8 Problematic Acts from wider collection
    problematic_audit = []
    for pname in KNOWN_PROBLEMATIC_ACTS:
        target_pdf = None
        for cand_dir in [MVP_PDF_DIR, GEN_PDF_DIR, MAH_LAWS_PDF_DIR]:
            cand = cand_dir / (pname + ".pdf")
            if cand.exists():
                target_pdf = cand
                break
            cand_no_dot = cand_dir / (pname.rstrip(".") + ".pdf")
            if cand_no_dot.exists():
                target_pdf = cand_no_dot
                break
                
        if target_pdf:
            doc, p_data = extract_pages_from_pdf(target_pdf)
            t_chars = sum(len(" ".join(l[0] for l in p["lines"])) for p in p_data)
            has_hindi = any(any("\u0900" <= ch <= "\u097F" for ch in " ".join(l[0] for l in p["lines"])) for p in p_data) or "Hkkjr dk jkti=" in " ".join(" ".join(l[0] for l in p["lines"]) for p in p_data[:3])
            
            enact_p = detect_enactment_start_page(doc, p_data)
            p_meta = {
                "law_id": slugify(pname),
                "law_name": pname,
                "source_pdf": target_pdf.name,
                "jurisdiction": "Central"
            }
            p_secs = parse_act_sections(doc, p_data, enact_p, p_meta)
            
            if t_chars < 500:
                status = "Incomplete / Truncated Source PDF (Requires Manual Review / Scan)"
            elif has_hindi and len(p_secs) == 0:
                status = "Hindi Gazette (Part II Section 1) - Requires Transliteration / Hindi Parser"
            elif len(p_secs) > 0:
                status = f"Successfully Parsed ({len(p_secs)} sections extracted)"
            else:
                status = "Requires Manual Review"
                
            problematic_audit.append({
                "act_name": pname,
                "source_pdf": target_pdf.name,
                "pages": len(doc),
                "chars_extracted": t_chars,
                "is_hindi_diglot": has_hindi,
                "sections_extracted": len(p_secs),
                "audit_verdict": status
            })

    # 4. Save Staging Outputs
    with open(LAWS_STAGING_PATH, "w", encoding="utf-8") as f:
        json.dump(all_laws, f, ensure_ascii=False, indent=2)
    print(f"\n  -> Staging laws written to: {LAWS_STAGING_PATH} ({len(all_laws)} laws)")
    
    with open(SECTIONS_STAGING_PATH, "w", encoding="utf-8") as f:
        json.dump(all_sections, f, ensure_ascii=False, indent=2)
    print(f"  -> Staging sections written to: {SECTIONS_STAGING_PATH} ({len(all_sections)} sections)")

    # 5. Save Manual Review CSV
    with open(MANUAL_REVIEW_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["law_id", "law_name", "section_number", "reason", "source_pdf"])
        writer.writeheader()
        writer.writerows(manual_review_records)
    print(f"  -> Manual review report written to: {MANUAL_REVIEW_CSV_PATH} ({len(manual_review_records)} items)")

    # 6. Generate Complete Validation Telemetry Report
    active_laws = [l for l in all_laws if not l["manual_review_required"]]
    review_laws = [l for l in all_laws if l["manual_review_required"]]
    maharashtra_laws = [l for l in all_laws if l["jurisdiction"] == "Maharashtra"]
    central_laws = [l for l in all_laws if l["jurisdiction"] == "Central"]
    
    empty_sections = [s for s in all_sections if not s["full_text"].strip() and not s.get("is_omitted")]
    short_sections = [s for s in all_sections if len(s["full_text"]) < 20 and not s.get("is_omitted")]
    
    validation_report = {
        "report_metadata": {
            "timestamp": datetime.now().isoformat(),
            "target_dataset": "Maharashtra_MVP",
            "pipeline_version": "vidhik_maharashtra_parser_v2.2",
            "legal_verification_note": "Extracted from official PDF sources. Staged for domain legal sign-off; not marked as verified."
        },
        "summary_statistics": {
            "total_pdfs_found": len(pdf_files),
            "total_extracted_text_files_found": len(txt_files),
            "total_laws_parsed": len(all_laws),
            "total_sections_extracted": len(all_sections),
            "maharashtra_jurisdiction_laws": len(maharashtra_laws),
            "central_jurisdiction_laws": len(central_laws),
            "laws_requiring_manual_review": len(review_laws),
            "sections_requiring_manual_review": len(manual_review_records),
            "empty_section_text_count": len(empty_sections),
            "truncated_sections_count": len(short_sections),
            "filename_anomalies_count": len(filename_anomalies)
        },
        "jurisdiction_breakdown": {
            "maharashtra_laws": [l["law_name"] for l in maharashtra_laws],
            "central_laws_count": len(central_laws)
        },
        "problematic_acts_benchmark_audit": problematic_audit,
        "filename_anomalies_summary": filename_anomalies,
        "sample_law_record": all_laws[0] if all_laws else None,
        "sample_section_record": all_sections[0] if all_sections else None
    }
    
    with open(PARSER_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(validation_report, f, ensure_ascii=False, indent=2)
    print(f"  -> Validation report written to: {PARSER_REPORT_PATH}")

    # Summary Display
    print("\n" + "=" * 75)
    print("MAHARASHTRA MVP PIPELINE EXECUTION SUMMARY")
    print("=" * 75)
    print(f"Total PDFs Evaluated             : {len(pdf_files)}")
    print(f"Total Laws Parsed                : {len(all_laws)}")
    print(f"Total Sections Extracted         : {len(all_sections)}")
    print(f"Maharashtra State / Bombay Acts  : {len(maharashtra_laws)}")
    print(f"Central / India Acts in MVP      : {len(central_laws)}")
    print(f"Laws Requiring Manual Review     : {len(review_laws)}")
    print(f"Empty Sections Detected (un-noted): {len(empty_sections)}")
    print(f"Filename Anomalies Detected      : {len(filename_anomalies)}")
    print("=" * 75)

    return validation_report


if __name__ == "__main__":
    run_mvp_pipeline()
