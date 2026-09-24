import json
import csv

input_file = "constitution_structured.json"
output_file = "constitution_structured.csv"

with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# If JSON is a list of objects
if isinstance(data, list):
    rows = data

# If JSON has the records inside a key
elif isinstance(data, dict):
    # Change this if your records are under a specific key
    rows = list(data.values())

else:
    raise ValueError("Unsupported JSON format")

if not rows:
    raise ValueError("No data found")

# Get all column names
columns = set()

for row in rows:
    if isinstance(row, dict):
        columns.update(row.keys())

columns = list(columns)

with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()

    for row in rows:
        writer.writerow(row)

print("Conversion completed!")
print("Created:", output_file)