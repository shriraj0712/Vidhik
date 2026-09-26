import pymupdf

doc = pymupdf.open('data/Constitution.pdf')

sched_pages = [284, 290, 300, 304, 307, 311, 341, 356, 358, 376, 380, 381]

for pno in sched_pages:
    txt = doc[pno - 1].get_text()
    lines = [l.strip() for l in txt.split('\n') if l.strip()]
    print(f"=== Page {pno} Top 5 lines ===")
    for l in lines[:6]:
        print("  ", repr(l))
