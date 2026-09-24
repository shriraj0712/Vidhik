import pymupdf as pm

pdf_path = "data/constitution.pdf"
output_path = "data/constitution_raw.txt"

doc = pm.open(pdf_path)

with open(output_path, "w", encoding="utf-8") as file:
    for page in doc:
        text = page.get_text()
        file.write(text)
        file.write("\n")

doc.close()

print("Constitution text extracted successfully!")