import os
import re
from pypdf import PdfReader

PDF_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "Legal_Dataset",
    "PDFs"
)

OUTPUT_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "Legal_Dataset",
    "extracted_text"
)

os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def clean_filename(filename):
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'\s+', ' ', filename)
    return filename.strip()


def extract_pdf(pdf_path):
    reader = PdfReader(pdf_path)

    text = ""

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text


def main():

    print("======================================")
    print("   CENTRAL ACT PDF TEXT EXTRACTION")
    print("======================================")

    pdf_files = [
        file for file in os.listdir(PDF_FOLDER)
        if file.lower().endswith(".pdf")
    ]

    print("PDFs found:", len(pdf_files))
    print()

    successful = 0
    failed = 0

    for index, filename in enumerate(pdf_files, start=1):

        pdf_path = os.path.join(
            PDF_FOLDER,
            filename
        )

        law_name = os.path.splitext(filename)[0]

        output_filename = (
            clean_filename(law_name)
            + ".txt"
        )

        output_path = os.path.join(
            OUTPUT_FOLDER,
            output_filename
        )

        print(
            f"[{index}/{len(pdf_files)}] {law_name}"
        )

        try:

            text = extract_pdf(pdf_path)

            with open(
                output_path,
                "w",
                encoding="utf-8"
            ) as file:

                file.write(text)

            print(
                "  Extracted:",
                len(text),
                "characters"
            )

            successful += 1

        except Exception as e:

            print(
                "  ERROR:",
                e
            )

            failed += 1

    print()
    print("======================================")
    print("EXTRACTION COMPLETED")
    print("======================================")
    print("Total PDFs:", len(pdf_files))
    print("Successful:", successful)
    print("Failed:", failed)
    print("Output folder:", OUTPUT_FOLDER)
    print("======================================")


if __name__ == "__main__":
    main()