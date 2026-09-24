import pymupdf

doc = pymupdf.open('data/Constitution.pdf')

for pno in [130, 148, 158, 229]:
    p = doc[pno - 1]
    d = p.get_text('dict')
    print(f"=== Page {pno} (rect={p.rect}) ===")
    for b in d['blocks']:
        if 'lines' in b:
            for l in b['lines']:
                spans = l['spans']
                txt = "".join(s['text'] for s in spans).strip()
                if txt and (txt.startswith("1.") or txt.startswith("2.") or txt.startswith("3.") or "omitted" in txt.lower() or "ins. by" in txt.lower()):
                    sz = spans[0]['size'] if spans else 0
                    y0 = l['bbox'][1]
                    print(f"  y0={y0:.1f}, sz={sz:.1f}, txt={repr(txt[:80])}")
