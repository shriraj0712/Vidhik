from pathlib import Path
import fitz

BASE_DIR = Path(r"C:\Users\aditi\Desktop\Capstone\Vidhik")

PDF_FOLDER = BASE_DIR / "data" / "Legal_Dataset" / "Maharashtra_MVP"
OUTPUT_FOLDER = PDF_FOLDER / "extracted_text"

OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

pdf_files = list(PDF_FOLDER.glob("*.pdf"))

print(f"Found {len(pdf_files)} PDF files.")

for pdf_path in pdf_files:
    output_path = OUTPUT_FOLDER / f"{pdf_path.stem}.txt"

    print(f"\nProcessing: {pdf_path.name}")

    try:
        doc = fitz.open(pdf_path)

        text_parts = []

        for page_number, page in enumerate(doc, start=1):
            text = page.get_text()

            if text.strip():
                text_parts.append(text)

        full_text = "\n\n".join(text_parts)

        output_path.write_text(
            full_text,
            encoding="utf-8"
        )

        print(f"Pages: {len(doc)}")
        print(f"Characters extracted: {len(full_text)}")
        print(f"Saved: {output_path.name}")

        doc.close()

    except Exception as e:
        print(f"ERROR: {e}")

print("\n===================================")
print("PDF TEXT EXTRACTION COMPLETED")
print("===================================")