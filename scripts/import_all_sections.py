import re
import psycopg2
from pathlib import Path
from difflib import SequenceMatcher
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

TEXT_FOLDER = Path(
    r"C:\Users\aditi\Desktop\Capstone\Vidhik\data\Legal_Dataset\extracted_text"
)

DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "database": "vidhik_db",
    "user": "postgres",
    "password": "postgres"
}


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove IndiaCode headers
    text = re.sub(r"(?im)^\s*IndiaCode\s*$", "", text)

    # Remove standalone page numbers
    text = re.sub(r"(?m)^\s*\d+\s*$", "", text)

    return text


# ============================================================
# NORMALIZE ACT NAME FOR MATCHING
# ============================================================

def normalize_name(name):

    name = Path(name).stem

    name = name.lower()

    name = name.replace("_", " ")
    name = name.replace("-", " ")
    name = name.replace("–", " ")
    name = name.replace("—", " ")

    # Remove extra spaces
    name = re.sub(r"\s+", " ", name)

    # Remove punctuation
    name = re.sub(r"[^\w\s]", "", name)

    return name.strip()


# ============================================================
# EXTRACT SECTIONS
# ============================================================

def extract_sections(text):

    text = clean_text(text)

    lines = [
        line.strip()
        for line in text.split("\n")
        if line.strip()
    ]

    # Section numbers:
    # 1.
    # 2.
    # 10.
    # 2A.
    # 43-B.
    section_pattern = re.compile(
    r"^((?:\d+[A-Z]?(?:[-–]\d+)?)|(?:[IVXLCDM]+))[\.\)]\s+(.+)$",
    re.IGNORECASE
)

    # Chapter detection
    chapter_pattern = re.compile(
        r"^CHAPTER\s+([IVXLCDM]+)\s*$",
        re.IGNORECASE
    )

    # Part detection
    part_pattern = re.compile(
        r"^PART\s+([IVXLCDM]+|\d+)\s*$",
        re.IGNORECASE
    )

    sections = []

    current_section = None
    current_text = []

    current_chapter = None
    current_part = None

    i = 0

    while i < len(lines):

        line = lines[i]

        # ----------------------------------------------------
        # CHAPTER
        # ----------------------------------------------------

        chapter_match = chapter_pattern.match(line)

        if chapter_match:

            chapter_number = chapter_match.group(1)

            chapter_title = ""

            if i + 1 < len(lines):
                next_line = lines[i + 1]

                if not section_pattern.match(next_line):
                    chapter_title = next_line

            current_chapter = f"Chapter {chapter_number}"

            if chapter_title:
                current_chapter += f" - {chapter_title}"

            i += 1
            continue

        # ----------------------------------------------------
        # PART
        # ----------------------------------------------------

        part_match = part_pattern.match(line)

        if part_match:

            current_part = f"Part {part_match.group(1)}"

            i += 1
            continue

        # ----------------------------------------------------
        # SECTION
        # ----------------------------------------------------

        section_match = section_pattern.match(line)

        if section_match:

            # Save previous section
            if current_section is not None:

                current_section["full_text"] = "\n".join(
                    current_text
                ).strip()

                sections.append(current_section)

            section_number = section_match.group(1)
            heading = section_match.group(2).strip()

            # Extract title
            title = heading

            for separator in ["—", "–", " - "]:
                if separator in heading:
                    title = heading.split(
                        separator,
                        1
                    )[0].strip()
                    break

            current_section = {
                "section_number": section_number,
                "section_title": title,
                "description": heading,
                "full_text": "",
                "chapter": current_chapter,
                "part": current_part
            }

            current_text = [line]

        else:

            if current_section is not None:
                current_text.append(line)

        i += 1

    # Save final section
    if current_section is not None:

        current_section["full_text"] = "\n".join(
            current_text
        ).strip()

        sections.append(current_section)

    return sections


# ============================================================
# CONNECT DATABASE
# ============================================================

print("=" * 70)
print("VIDHIK - LEGAL SECTIONS IMPORT")
print("=" * 70)

print("\nConnecting to PostgreSQL...")

conn = psycopg2.connect(**DB_CONFIG)

cursor = conn.cursor()

print("Database connected successfully.\n")


# ============================================================
# LOAD ALL LAWS
# ============================================================

cursor.execute("""
    SELECT
        law_id,
        law_name,
        source_url
    FROM laws
""")

laws = cursor.fetchall()

print(f"Laws found in database: {len(laws)}")


# Create normalized lookup
law_lookup = {}

for law_id, law_name, source_url in laws:

    normalized = normalize_name(law_name)

    law_lookup[normalized] = (
        law_id,
        law_name,
        source_url
    )


# ============================================================
# PROCESS FILES
# ============================================================

files = sorted(TEXT_FOLDER.glob("*.txt"))

print(f"Text files found: {len(files)}")

print("\nStarting import...\n")


total_sections = 0
processed_files = 0
unmatched_files = 0
failed_files = 0
duplicate_sections = 0


unmatched_log = []
failed_log = []


for index, file_path in enumerate(files, start=1):

    print(
        f"[{index}/{len(files)}] "
        f"{file_path.name}"
    )

    try:

        # ----------------------------------------------------
        # MATCH FILE TO LAW
        # ----------------------------------------------------

        normalized_filename = normalize_name(
            file_path.name
        )

        law_data = law_lookup.get(
            normalized_filename
        )

        # ----------------------------------------------------
        # Fallback matching
        # ----------------------------------------------------

        if law_data is None:

            possible_matches = []

            for law_name_normalized, data in law_lookup.items():

                similarity = SequenceMatcher(
                    None,
                    normalized_filename,
                    law_name_normalized
                ).ratio()

                if similarity >= 0.92:
                    possible_matches.append(
                        (similarity, data)
                    )

            if len(possible_matches) == 1:

                law_data = possible_matches[0][1]

        # ----------------------------------------------------
        # NO MATCH
        # ----------------------------------------------------

        if law_data is None:

            print("   WARNING: No matching law found")

            unmatched_files += 1

            unmatched_log.append(
                file_path.name
            )

            continue

        law_id, law_name, source_url = law_data

        print(
            f"   Matched: {law_name}"
        )

        # ----------------------------------------------------
        # READ FILE
        # ----------------------------------------------------

        text = file_path.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        # ----------------------------------------------------
        # EXTRACT SECTIONS
        # ----------------------------------------------------

        sections = extract_sections(text)

        print(
            f"   Sections detected: {len(sections)}"
        )

        if not sections:
            print("   WARNING: No sections detected")

            failed_files += 1

            failed_log.append(
                f"{file_path.name} - No sections detected"
            )

            continue

        # ----------------------------------------------------
        # INSERT SECTIONS
        # ----------------------------------------------------

        file_inserted = 0

        for section in sections:

            section_number = section[
                "section_number"
            ]

            # Check duplicate
            cursor.execute("""
                SELECT section_id
                FROM sections
                WHERE law_id = %s
                AND section_number = %s
            """, (
                law_id,
                section_number
            ))

            existing = cursor.fetchone()

            if existing:

                duplicate_sections += 1
                continue

            cursor.execute("""
                INSERT INTO sections (
                    law_id,
                    section_number,
                    section_title,
                    description,
                    full_text,
                    chapter,
                    part,
                    source_url,
                    created_at,
                    updated_at
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
            """, (
                law_id,
                section_number,
                section["section_title"],
                section["description"],
                section["full_text"],
                section["chapter"],
                section["part"],
                source_url,
                datetime.now(),
                datetime.now()
            ))

            file_inserted += 1
            total_sections += 1

        conn.commit()

        processed_files += 1

        print(
            f"   Inserted: {file_inserted}"
        )

    except Exception as e:

        conn.rollback()

        failed_files += 1

        error_message = (
            f"{file_path.name} - {str(e)}"
        )

        failed_log.append(
            error_message
        )

        print(
            f"   ERROR: {e}"
        )


# ============================================================
# SAVE LOGS
# ============================================================

if unmatched_log:

    Path(
        "unmatched_law_files.txt"
    ).write_text(
        "\n".join(unmatched_log),
        encoding="utf-8"
    )


if failed_log:

    Path(
        "section_import_errors.txt"
    ).write_text(
        "\n".join(failed_log),
        encoding="utf-8"
    )


# ============================================================
# CLOSE DATABASE
# ============================================================

cursor.close()
conn.close()


# ============================================================
# FINAL REPORT
# ============================================================

print("\n")
print("=" * 70)
print("IMPORT COMPLETED")
print("=" * 70)

print(
    f"Total text files       : {len(files)}"
)

print(
    f"Successfully processed : {processed_files}"
)

print(
    f"Unmatched files        : {unmatched_files}"
)

print(
    f"Failed files           : {failed_files}"
)

print(
    f"Sections inserted      : {total_sections}"
)

print(
    f"Duplicate sections     : {duplicate_sections}"
)

print("=" * 70)