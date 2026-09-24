import re

input_file = "data/constitution_raw.txt"
output_file = "data/constitution_clean.txt"

with open(input_file, "r", encoding="utf-8") as file:
    text = file.read()

text = re.sub(r'\n+', '\n', text)
text = re.sub(r'[ \t]+', ' ', text)
text = re.sub(r' +\n', '\n', text)
text = re.sub(r'\n ', '\n', text)

with open(output_file, "w", encoding="utf-8") as file:
    file.write(text.strip())

print("Text cleaned successfully!")