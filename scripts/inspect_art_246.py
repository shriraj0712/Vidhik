import pymupdf
import re

doc = pymupdf.open('data/Constitution.pdf')

# Let's inspect Article 246 on page 174
p174 = doc[173] # page 174 (0-index 173)
d = p174.get_text('dict')
for b in d['blocks']:
    if 'lines' in b:
        for l in b['lines']:
            spans_info = [(s['size'], s['flags'], repr(s['text'])) for s in l['spans']]
            txt = "".join(s['text'] for s in l['spans'])
            if "246" in txt:
                print("Line with 246:")
                print("  Text:", repr(txt))
                print("  Spans:", spans_info)
