import re
from pathlib import Path

FILE_PATH = Path(
    r"C:\Users\aditi\Desktop\Capstone\Vidhik\data\Legal_Dataset\extracted_text\Extending certain Acts to Straits Settlement , 1852.txt"
)

text = FILE_PATH.read_text(encoding="utf-8", errors="ignore")

text = text.replace("\r\n", "\n").replace("\r", "\n")

# Remove IndiaCode headers
text = re.sub(r"(?im)^\s*IndiaCode\s*$", "", text)

# Remove standalone page numbers
text = re.sub(r"(?m)^\s*\d+\s*$", "", text)

lines = [line.strip() for line in text.split("\n") if line.strip()]


# --------------------------------------------------
# SECTION PATTERN
# --------------------------------------------------

section_pattern = re.compile(
    r"^(\d+[A-Z]?(?:[-–]\d+)?)[\.\)]\s+(.+)$"
)

sections = []

current_section = None
current_text = []


for line in lines:

    match = section_pattern.match(line)

    if match:

        # Save previous section
        if current_section:
            current_section["full_text"] = "\n".join(current_text).strip()
            sections.append(current_section)

        section_number = match.group(1)
        heading = match.group(2).strip()

        # ------------------------------------------
        # Extract title
        # ------------------------------------------

        if "—" in heading:
            title = heading.split("—", 1)[0].strip()

        elif "–" in heading:
            title = heading.split("–", 1)[0].strip()

        elif " - " in heading:
            title = heading.split(" - ", 1)[0].strip()

        else:
            title = heading.strip()

        current_section = {
            "section_number": section_number,
            "section_title": title,
            "chapter": None,
            "part": None,
            "full_text": ""
        }

        current_text = [line]

    else:

        if current_section:
            current_text.append(line)


# Save last section
if current_section:
    current_section["full_text"] = "\n".join(current_text).strip()
    sections.append(current_section)


# --------------------------------------------------
# DISPLAY
# --------------------------------------------------

print("=" * 70)
print("SECTION EXTRACTION TEST")
print("=" * 70)

print(f"File: {FILE_PATH.name}")
print(f"Sections found: {len(sections)}")
print()

for section in sections:

    print("-" * 70)
    print("Section Number :", section["section_number"])
    print("Section Title  :", section["section_title"])
    print("Full Text      :")
    print(section["full_text"][:500])
    print()

print("=" * 70)
print("TEST COMPLETED")
print("=" * 70)