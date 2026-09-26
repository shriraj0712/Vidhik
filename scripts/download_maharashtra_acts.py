import re
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urljoin

BASE = "https://lj.maharashtra.gov.in"
ACT_LIST = BASE + "/en/document-category/act-list/"

OUTPUT = Path(
    r"C:\Users\aditi\Desktop\Capstone\Vidhik\data\Legal_Dataset\Maharashtra_MVP"
)

OUTPUT.mkdir(parents=True, exist_ok=True)

TARGETS = {
    "maharashtra land revenue code": "Maharashtra Land Revenue Code, 1966.pdf",
    "maharashtra rent control act": "Maharashtra Rent Control Act, 1999.pdf",
    "maharashtra stamp act": "Maharashtra Stamp Act.pdf",
    "maharashtra tenancy and agricultural lands act": "Maharashtra Tenancy and Agricultural Lands Act.pdf",
    "maharashtra co-operative societies act": "Maharashtra Co-operative Societies Act, 1960.pdf",
    "maharashtra regional and town planning act": "Maharashtra Regional and Town Planning Act, 1966.pdf",
    "maharashtra ownership flats": "Maharashtra Ownership Flats Act, 1963.pdf",
    "maharashtra prohibition act": "Maharashtra Prohibition Act.pdf",
    "maharashtra village panchayats act": "Maharashtra Village Panchayats Act.pdf",
    "maharashtra land requisition act": "Maharashtra Land Requisition Act.pdf",
}

session = requests.Session()

session.headers.update({
    "User-Agent": "Mozilla/5.0"
})

def clean(text):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()

found = {}

print("=" * 70)
print("VIDHIK - MAHARASHTRA ACT DOWNLOADER")
print("=" * 70)

# Search pages
for page in range(1, 30):

    if page == 1:
        url = ACT_LIST
    else:
        url = f"{ACT_LIST}page/{page}/"

    print(f"Checking page {page}...")

    try:
        response = session.get(url, timeout=30)

        if response.status_code != 200:
            continue

    except Exception as e:
        print("Error:", e)
        continue

    soup = BeautifulSoup(response.text, "html.parser")

    # Find every table row
    for row in soup.find_all("tr"):

        row_text = clean(row.get_text(" ", strip=True))

        if not row_text:
            continue

        # Look for target Act
        matched_target = None

        for target in TARGETS:

            if target in row_text:
                matched_target = target
                break

        if not matched_target:
            continue

        # Find PDF link inside same row
        pdf_link = None

        for a in row.find_all("a", href=True):

            href = a["href"]

            if ".pdf" in href.lower():
                pdf_link = urljoin(BASE, href)
                break

        if pdf_link:

            found[matched_target] = pdf_link

            print()
            print("FOUND:")
            print(matched_target)
            print(pdf_link)


print()
print("=" * 70)
print("DOWNLOAD PHASE")
print("=" * 70)

downloaded = 0

for target, filename in TARGETS.items():

    if target not in found:

        print("MISSING:", target)
        continue

    url = found[target]

    output = OUTPUT / filename

    print()
    print("Downloading:", filename)
    print("URL:", url)

    try:

        r = session.get(url, timeout=90)
        r.raise_for_status()

        if not r.content.startswith(b"%PDF"):

            print("ERROR: Not a PDF")
            continue

        output.write_bytes(r.content)

        size_mb = len(r.content) / (1024 * 1024)

        print(f"SAVED: {output}")
        print(f"SIZE : {size_mb:.2f} MB")

        downloaded += 1

    except Exception as e:

        print("ERROR:", e)


print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)

print("Found:", len(found), "/", len(TARGETS))
print("Downloaded:", downloaded)

print()
print("Output:")
print(OUTPUT)

print("=" * 70)