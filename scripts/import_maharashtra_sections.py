from pathlib import Path
import re
import psycopg2
from difflib import SequenceMatcher
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

TEXT_FOLDER = Path(
    r"C:\Users\aditi\Desktop\Capstone\Vidhik\data\Maharashtra_Laws\extracted_text"
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
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove IndiaCode/page-number artifacts
    text = re.sub(r"IndiaCode\s*\d*", "", text, flags=re.IGNORECASE)

    # Remove lines containing only page numbers
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)

    return text


# ============================================================
# NORMALIZE ACT NAME
# ============================================================

def normalize_name(name):
    name = name.lower()

    name = name.replace(".txt", "")
    name = name.replace("_", " ")

    name = re.sub(r"\bact\b", "act", name)
    name = re.sub(r"[^a-z0-9 ]", " ", name)
    name = re.sub(r"\s+", " ", name)

    return name.strip()


# ============================================================
# FIND ACT TITLE
# ============================================================

def extract_act_title(text):

    patterns = [
        r"THE\s+([A-Z][A-Z\s\(\),&\-\.]+ACT(?:,\s*\d{4})?)",
        r"THE\s+([A-Za-z][A-Za-z\s\(\),&\-\.]+ACT(?:,\s*\d{4})?)"
    ]

    for pattern in patterns:

        match = re.search(pattern, text)

        if match:
            title = match.group(1).strip()

            title = re.sub(r"\s+", " ", title)

            return "The " + title

    return None


# ============================================================
# EXTRACT SECTIONS
# ============================================================

def extract_sections(text):

    lines = text.splitlines()

    sections = []

    current_section = None
    current_text = []

    # Supports:
    # 1.
    # 2.
    # 23A.
    # 27AA.
    # 40A.
    #
    section_pattern = re.compile(
        r"^\s*(\d+[A-Z]{0,3})[\.\)]\s+(.+?)\s*$",
        re.IGNORECASE
    )

    # We start parsing after the CONTENTS area.
    contents_finished = False

    for line in lines:

        stripped = line.strip()

        if not stripped:
            if current_section:
                current_text.append("")
            continue

        # Detect beginning of actual law text
        if not contents_finished:

            upper = stripped.upper()

            if (
                "PRELIMINARY" in upper
                or "PART I" in upper
                or "CHAPTER I" in upper
            ):
                contents_finished = True

            # Still allow parsing if actual section begins
            section_match = section_pattern.match(stripped)

            if not section_match:
                continue

        match = section_pattern.match(stripped)

        if match:

            section_number = match.group(1).upper()
            section_title = match.group(2).strip()

            # Ignore obvious contents headings
            if section_number in {"1"} and not contents_finished:
                continue

            # Save previous section
            if current_section:

                full_text = "\n".join(current_text).strip()

                if full_text:
                    current_section["full_text"] = full_text
                    sections.append(current_section)

            current_section = {
                "section_number": section_number,
                "section_title": section_title,
                "full_text": ""
            }

            current_text = [stripped]

        else:

            if current_section:
                current_text.append(stripped)

    # Save final section
    if current_section:

        full_text = "\n".join(current_text).strip()

        if full_text:
            current_section["full_text"] = full_text
            sections.append(current_section)

    return sections


# ============================================================
# DATABASE
# ============================================================

def get_db_connection():

    return psycopg2.connect(**DB_CONFIG)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("MAHARASHTRA LAW SECTION IMPORT")
    print("=" * 60)

    files = list(TEXT_FOLDER.glob("*.txt"))

    print(f"\nFound {len(files)} text files.")

    if not files:
        print("No TXT files found.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    total_sections = 0
    total_laws = 0

    for txt_file in files:

        print("\n" + "-" * 60)
        print("Processing:", txt_file.name)

        try:

            raw_text = txt_file.read_text(
                encoding="utf-8",
                errors="replace"
            )

            text = clean_text(raw_text)

            # ------------------------------------------------
            # Extract Act title
            # ------------------------------------------------

            act_title = extract_act_title(text)

            if not act_title:

                print("❌ Could not identify Act title")
                continue

            print("Act:", act_title)

            # ------------------------------------------------
            # Check if law already exists
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT law_id, law_name
                FROM laws
                WHERE LOWER(law_name) = LOWER(%s)
                """,
                (act_title,)
            )

            law = cursor.fetchone()

            # ------------------------------------------------
            # Create Maharashtra law if needed
            # ------------------------------------------------

            if law:

                law_id = law[0]

                print("Existing law_id:", law_id)

            else:

                cursor.execute(
                    """
                    INSERT INTO laws
                    (
                        law_name,
                        short_name,
                        law_type,
                        description,
                        jurisdiction,
                        created_at,
                        updated_at
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        'State Act',
                        %s,
                        'Maharashtra',
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    )
                    RETURNING law_id
                    """,
                    (
                        act_title,
                        act_title,
                        f"Maharashtra State Act: {act_title}"
                    )
                )

                law_id = cursor.fetchone()[0]

                total_laws += 1

                print("✅ Created law_id:", law_id)

            # ------------------------------------------------
            # Extract sections
            # ------------------------------------------------

            sections = extract_sections(text)

            print("Sections detected:", len(sections))

            if not sections:

                print("⚠️ No sections detected")
                continue

            inserted = 0
            skipped = 0

            # ------------------------------------------------
            # Insert sections
            # ------------------------------------------------

            for section in sections:

                section_number = section["section_number"]
                section_title = section["section_title"]
                full_text = section["full_text"]

                # Check duplicate
                cursor.execute(
                    """
                    SELECT section_id
                    FROM sections
                    WHERE law_id = %s
                    AND section_number = %s
                    """,
                    (
                        law_id,
                        section_number
                    )
                )

                existing = cursor.fetchone()

                if existing:

                    skipped += 1
                    continue

                cursor.execute(
                    """
                    INSERT INTO sections
                    (
                        law_id,
                        section_number,
                        section_title,
                        full_text,
                        created_at,
                        updated_at
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    )
                    """,
                    (
                        law_id,
                        section_number,
                        section_title,
                        full_text
                    )
                )

                inserted += 1

            conn.commit()

            total_sections += inserted

            print("✅ Inserted:", inserted)
            print("⏭️ Skipped:", skipped)

        except Exception as e:

            conn.rollback()

            print("❌ ERROR:", e)

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("IMPORT COMPLETE")
    print("=" * 60)

    print("New laws created:", total_laws)
    print("New sections inserted:", total_sections)


if __name__ == "__main__":
    main()