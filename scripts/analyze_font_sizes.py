import pymupdf

doc = pymupdf.open('data/Constitution.pdf')

sizes = {}
for pno in range(31, 283):
    d = doc[pno].get_text('dict')
    for b in d['blocks']:
        if 'lines' in b:
            for l in b['lines']:
                for s in l['spans']:
                    sz = round(s['size'], 1)
                    txt = s['text'].strip()
                    if txt:
                        if sz not in sizes:
                            sizes[sz] = []
                        if len(sizes[sz]) < 3:
                            sizes[sz].append(f"P{pno+1}: {repr(txt[:40])}")

print("Font sizes found in Constitution pages 32-283:")
for sz in sorted(sizes.keys()):
    print(f"Size {sz:4.1f} pt ({len(sizes[sz])} samples):")
    for samp in sizes[sz]:
        print(f"   {samp}")
