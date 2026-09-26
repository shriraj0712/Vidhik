import pymupdf

doc = pymupdf.open('data/Constitution.pdf')

sched_keys = [
    "FIRST SCHEDULE", "SECOND SCHEDULE", "THIRD SCHEDULE", "FOURTH SCHEDULE",
    "FIFTH SCHEDULE", "SIXTH SCHEDULE", "SEVENTH SCHEDULE", "EIGHTH SCHEDULE",
    "NINTH SCHEDULE", "TENTH SCHEDULE", "ELEVENTH SCHEDULE", "TWELFTH SCHEDULE"
]

for sk in sched_keys:
    found = []
    for pno in range(280, 390):
        txt = doc[pno].get_text()
        if sk in txt.upper():
            found.append(pno + 1)
    print(f"{sk:20s}: Pages {found}")
