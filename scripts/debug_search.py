import pymupdf
import re

doc = pymupdf.open('data/Constitution.pdf')

print("--- Checking P60 (Art 63, 64) ---")
print(doc[59].get_text())

print("--- Checking P72 (Art 92) ---")
print(doc[71].get_text())

print("--- Checking P262 (Art 370) ---")
print(repr(doc[261].get_text()))

print("--- Searching for 238 in all pages ---")
for pno in range(len(doc)):
    txt = doc[pno].get_text()
    if "238" in txt:
        print(f"P{pno+1} contains 238:")
        for l in txt.split("\n"):
            if "238" in l:
                print("  ", repr(l))
