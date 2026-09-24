import pymupdf
import re

doc = pymupdf.open('data/Constitution.pdf')

def extract_schedules(doc, start_p, end_p):
    schedule_names = [
        ("FIRST SCHEDULE", "[Articles 1 and 4]"),
        ("SECOND SCHEDULE", "[Articles 59(3), 65(3), 75(6), 97, 125, 148(3), 158(3), 164(5), 186 and 221]"),
        ("THIRD SCHEDULE", "[Articles 75(4), 99, 124(6), 148(2), 164(3), 188 and 219]"),
        ("FOURTH SCHEDULE", "[Articles 4(1) and 80(2)]"),
        ("FIFTH SCHEDULE", "[Article 244(1)]"),
        ("SIXTH SCHEDULE", "[Articles 244(2) and 275(1)]"),
        ("SEVENTH SCHEDULE", "[Article 246]"),
        ("EIGHTH SCHEDULE", "[Articles 344(1) and 351]"),
        ("NINTH SCHEDULE", "[Article 31B]"),
        ("TENTH SCHEDULE", "[Articles 102(2) and 191(2)]"),
        ("ELEVENTH SCHEDULE", "[Article 243G]"),
        ("TWELFTH SCHEDULE", "[Article 243W]")
    ]
    
    # Collect all body lines for schedule pages
    raw_lines = []
    for pno in range(start_p, end_p):
        p = doc[pno]
        d = p.get_text('dict')
        for b in d['blocks']:
            if 'lines' not in b:
                continue
            y0, y1 = b['bbox'][1], b['bbox'][3]
            if y0 < 50:
                continue
            if y1 > 470 and len(b['lines']) == 1:
                t = "".join(s['text'] for s in b['lines'][0]['spans']).strip()
                if t.isdigit():
                    continue
            for l in b['lines']:
                spans = l['spans']
                if spans and spans[0]['size'] <= 8.2 and l['bbox'][1] > 350:
                    # footnote line
                    continue
                line_str = "".join(s['text'] for s in spans).strip()
                if line_str:
                    raw_lines.append((line_str, pno + 1))
                    
    # State machine to segment schedules
    schedules = []
    current_sched = None
    current_text = []
    
    for line, pno in raw_lines:
        matched_name = None
        for sname, sref in schedule_names:
            if line.upper() == sname or line.upper() == f"[{sname}]" or line.upper().startswith(sname):
                matched_name = sname
                break
                
        if matched_name and len(line) < 60:
            if current_sched:
                current_sched["full_text"] = "\n".join(current_text).strip()
                current_sched["page_end"] = pno - 1 if pno > current_sched["page_start"] else pno
                schedules.append(current_sched)
            ref_match = next((ref for name, ref in schedule_names if name == matched_name), None)
            current_sched = {
                "schedule_number": matched_name.split()[0],
                "schedule_name": matched_name,
                "articles_referred": ref_match,
                "page_start": pno,
                "page_end": pno,
                "full_text": ""
            }
            current_text = [line]
        else:
            if current_sched:
                current_text.append(line)
                current_sched["page_end"] = pno
                
    if current_sched:
        current_sched["full_text"] = "\n".join(current_text).strip()
        schedules.append(current_sched)
        
    return schedules

schedules = extract_schedules(doc, 283, 381)
print(f"Extracted Schedules: {len(schedules)}")
for s in schedules:
    print(f"  [{s['schedule_name']}] -> Pages {s['page_start']}-{s['page_end']} | Text Len: {len(s['full_text'])}")
