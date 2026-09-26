import pymupdf

doc = pymupdf.open('data/Constitution.pdf')
p = doc[49] # page 50
d = p.get_text('dict')
for b in d['blocks']:
    if 'lines' in b:
        for l in b['lines']:
            spans_desc = []
            for s in l['spans']:
                t = s['text']
                sz = s['size']
                fl = s['flags']
                spans_desc.append(f"({sz:.1f}pt|{fl}|{repr(t)})")
            print(" ".join(spans_desc))
