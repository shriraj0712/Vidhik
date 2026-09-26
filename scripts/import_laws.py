import os
import re
from datetime import datetime

import psycopg2


# ==============================
# DATABASE
# ==============================

conn = psycopg2.connect(
    host="localhost",
    port="5432",
    database="vidhik_db",
    user="postgres",
    password="postgres"
)

cursor = conn.cursor()


# ==============================
# FOLDERS
# ==============================

BASE_DIR = os.path.dirname(
    os.path.dirname(__file__)
)

TEXT_FOLDER = os.path.join(
    BASE_DIR,
    "data",
    "Legal_Dataset",
    "extracted_text"
)


# ==============================
# PROCESS FILES
# ==============================

files = [
    f for f in os.listdir(TEXT_FOLDER)
    if f.lower().endswith(".txt")
]

print("======================================")
print("        LAW DATA IMPORT")
print("======================================")
print("Text files found:", len(files))
print()


inserted = 0
skipped = 0
failed = 0


for index, filename in enumerate(files, start=1):

    filepath = os.path.join(
        TEXT_FOLDER,
        filename
    )

    try:

        # --------------------------------
        # Read text
        # --------------------------------

        with open(
            filepath,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as f:

            text = f.read()


        # --------------------------------
        # Law name from filename
        # --------------------------------

        law_name = os.path.splitext(
            filename
        )[0].strip()


        # --------------------------------
        # Extract Act number and year
        # --------------------------------

        act_match = re.search(
            r"ACT\s*No\.?\s*([A-Z0-9IVXLC]+)"
            r"\.?\s*OF\s*(\d{4})",
            text,
            re.IGNORECASE
        )

        act_number = None
        year = None

        if act_match:

            act_number = act_match.group(1).strip()
            year = act_match.group(2).strip()


        # --------------------------------
        # Extract passed/enactment date
        # --------------------------------

        date_match = re.search(
            r"\[\s*Passed\s+on\s+the\s+"
            r"(\d{1,2})\s+([A-Za-z]+),\s*(\d{4})\s*\]",
            text,
            re.IGNORECASE
        )

        enactment_date = None

        if date_match:

            day = date_match.group(1)
            month = date_match.group(2)
            year_date = date_match.group(3)

            try:

                enactment_date = datetime.strptime(
                    f"{day} {month} {year_date}",
                    "%d %B %Y"
                ).date()

            except ValueError:

                enactment_date = None


        # --------------------------------
        # Short name
        # --------------------------------

        if act_number and year:

            short_name = (
                f"Act No. {act_number} of {year}"
            )

        elif year:

            short_name = f"{law_name} Act, {year}"

        else:

            short_name = law_name


        # --------------------------------
        # Description
        # --------------------------------

        # Take a small portion after the
        # Act heading as description.

        description = text[:1000].strip()

        # --------------------------------
        # Check duplicate
        # --------------------------------

        cursor.execute(
            """
            SELECT law_id
            FROM laws
            WHERE law_name = %s
            """,
            (law_name,)
        )

        existing = cursor.fetchone()


        if existing:

            print(
                f"[{index}/{len(files)}] "
                f"Already exists: {law_name}"
            )

            skipped += 1
            continue


        # --------------------------------
        # Insert
        # --------------------------------

        cursor.execute(
            """
            INSERT INTO laws
            (
                law_name,
                short_name,
                law_type,
                description,
                jurisdiction,
                enactment_date,
                effective_date,
                source_url
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                law_name,
                short_name,
                "Central Act",
                description,
                "India",
                enactment_date,
                None,
                None
            )
        )


        inserted += 1

        print(
            f"[{index}/{len(files)}] "
            f"Inserted: {law_name}"
        )


    except Exception as e:

        print(
            f"[{index}/{len(files)}] "
            f"ERROR: {filename}"
        )

        print(" ", e)

        conn.rollback()

        failed += 1


# ==============================
# COMMIT
# ==============================

conn.commit()

cursor.close()
conn.close()


# ==============================
# RESULT
# ==============================

print()
print("======================================")
print("       LAW IMPORT COMPLETED")
print("======================================")
print("Total files:", len(files))
print("Inserted:", inserted)
print("Already existed:", skipped)
print("Failed:", failed)
print("======================================")