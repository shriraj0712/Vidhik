from pathlib import Path
from pypdf import PdfReader
import re

PDF_FOLDER = Path(
    r"C:\Users\aditi\Desktop\Capstone\Vidhik\data\Maharashtra_Laws\PDFs"
)

ACT_NAMES = {
    "maharashtra industrial relations act":
        "Maharashtra_Industrial_Relations_Act.pdf",

    "maharashtra lokayukta act":
        "Maharashtra_Lokayukta_Act_2023.pdf",

    "maharashtra land revenue code":
        "Maharashtra_Land_Revenue_Code_1966.pdf",

    "hyderabad atiayat inquiries act":
        "Hyderabad_Atiyat_Inquiries_Act_1952.pdf",

    "hyderabad atiyat inquiries act":
        "Hyderabad_Atiyat_Inquiries_Act_1952.pdf",
}

for pdf_file in PDF_FOLDER.glob("*.pdf"):

    print("\nReading:", pdf_file.name)

    try:
        reader = PdfReader(str(pdf_file))

        text = ""

        for page in reader.pages[:3]:
            text += " " + (page.extract_text() or "")

        text_lower = re.sub(r"\s+", " ", text.lower())

        matched_name = None

        for keyword, new_name in ACT_NAMES.items():

            if keyword in text_lower:
                matched_name = new_name
                break

        if matched_name:

            new_path = PDF_FOLDER / matched_name

            if new_path.exists() and new_path != pdf_file:

                print("⚠️ Duplicate detected:")
                print("   Existing:", new_path.name)
                print("   Current :", pdf_file.name)

            else:

                pdf_file.rename(new_path)

                print("✅ RENAMED →", matched_name)

        else:

            print("❌ Could not identify this PDF")
            print("First text found:")
            print(text[:500])

    except Exception as e:

        print("❌ Error:", e)

print("\nDone.")