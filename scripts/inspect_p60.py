import pymupdf

doc = pymupdf.open('data/Constitution.pdf')
p = doc[59] # page 60
d = p.get_text('dict')
print("Page 60 rect:", p.rect)
print("Blocks on P60:", len(d['blocks']))
for i, b in enumerate(d['blocks']):
    bbox = b.get('bbox')
    btype = b.get('type')
    print(f"Block {i}: bbox={bbox}, type={btype}")
    if 'lines' in b:
        txt = "".join("".join(s['text'] for s in l['spans']) for l in b['lines'])
        print(f"  Lines: {len(b['lines'])}, Text snippet: {repr(txt[:120])}")
