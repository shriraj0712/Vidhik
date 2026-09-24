from pathlib import Path
import shutil

SOURCE = Path(r"C:\Users\aditi\Desktop\Capstone\Vidhik\data\Legal_Dataset\PDFs")
DEST = Path(r"C:\Users\aditi\Desktop\Capstone\Vidhik\data\Legal_Dataset\Maharashtra_MVP")

DEST.mkdir(parents=True, exist_ok=True)

# ============================================================
# IMPORTANT CENTRAL ACTS
# ============================================================

CENTRAL_ACTS = [
    "Constitution.pdf",

    # Criminal law
    "Bharatiya Nyaya Sanhita",
    "Bharatiya Nagarik Suraksha Sanhita",
    "Bharatiya Sakshya Adhiniyam",
    "Juvenile Justice",
    "Protection of Children from Sexual Offences",
    "Dowry Prohibition Act",
    "Protection of Women from Domestic Violence",
    "Prohibition of Child Marriage",
    "Scheduled Castes and the Scheduled Tribes",
    "Protection of Civil Rights Act",
    "Protection of Human Rights Act",
    "Prevention of Corruption Act",
    "Prevention of Money-Laundering Act",
    "Narcotic Drugs and Psychotropic Substances",
    "Unlawful Activities (Prevention) Act",
    "Arms Act",
    "Probation of Offenders Act",
    "Police Act, 1861",
    "Prisons Act",

    # Civil / property
    "Code of Civil Procedure",
    "Indian Contract Act",
    "Indian Partnership Act",
    "Sale of Goods Act",
    "Transfer of Property Act",
    "Indian Easements Act",
    "Specific Relief Act",
    "Limitation Act",
    "Partition Act",
    "Registration Act",
    "Indian Stamp Act",
    "Powers-of-Attorney Act",
    "Indian Trusts Act",
    "Indian Succession Act",
    "Majority Act",
    "Guardians and Wards Act",
    "Married Women's Property Act",
    "Fatal Accidents Act",
    "Usurious Loans Act",
    "Court-Fees Act",
    "Suits Valuation Act",
    "Provincial Small Cause Courts Act",

    # Family law
    "Hindu Marriage Act",
    "Hindu Succession Act",
    "Hindu Adoptions and Maintenance Act",
    "Hindu Minority and Guardianship Act",
    "Special Marriage Act",
    "Indian Christian Marriage Act",
    "Dissolution of Muslim Marriages Act",
    "Muslim Personal Law",
    "Muslim Women",

    # Consumer / business
    "Consumer Protection Act",
    "Commercial Courts Act",
    "Arbitration and Conciliation Act",
    "Mediation Act",
    "Negotiable Instruments Act",
    "Companies Act",
    "Limited Liability Partnership Act",
    "Insolvency and Bankruptcy Code",
    "Micro, Small and Medium Enterprises Development Act",
    "Recovery Of Debts And Bankruptcy Act",
    "Securitisation and Reconstruction",

    # Technology / intellectual property
    "Information Technology Act",
    "Digital Personal Data Protection Act",
    "Copyright Act",
    "Trade Marks Act",
    "Patents Act",
    "Geographical Indications",
    "Legal Metrology Act",
    "Telecommunications Act",

    # Land / housing
    "Real Estate (Regulation and Development) Act",
    "Right to Fair Compensation and Transparency in Land Acquisition",
    "Land Acquisition",

    # Rights / welfare
    "Right to Information Act",
    "Legal Services Authorities Act",
    "Right of Children to Free and Compulsory Education",
    "Rights of Persons with Disabilities",
    "Maintenance and Welfare of Parents and Senior Citizens",
    "Sexual Harassment of Women at Workplace",
    "Child and Adolescent Labour",
    "Street Vendors",
    "National Food Security Act",
    "Scheduled Tribes and Other Traditional Forest Dwellers",

    # Health
    "Drugs and Cosmetics Act",
    "Food Safety and Standards Act",
    "Medical Termination of Pregnancy Act",
    "Mental Healthcare Act",
    "Transplantation of Human Organs",
    "Surrogacy (Regulation) Act",
    "Pre-conception and Pre-natal",
    "Immoral Traffic",

    # Environment
    "Environment (Protection) Act",
    "Water (Prevention and Control of Pollution)",
    "Air (Prevention and Control of Pollution)",
    "Wild Life (Protection) Act",
    "Indian Forest Act",
    "Biological Diversity Act",

    # Transport / infrastructure
    "Motor Vehicles Act",
    "Electricity Act",

    # Other important laws
    "Disaster Management Act",
    "Passports Act",
    "Citizenship Act",
    "Official Secrets Act",
    "Notaries Act",
]


# ============================================================
# BOMBAY / MAHARASHTRA-RELATED ACTS FROM CURRENT COLLECTION
# ============================================================

MAHARASHTRA_ACTS = [
    "Bombay Civil Court's Act",
    "Bombay Rent-free Estates Act",
    "Bombay Revenue Jurisdiction Act",
    "Boundary-Marks, Bombay",
    "Bombay Reorganisation Act",
    "City of Bombay Municipal",
    "Tobacco Duty (Town of Bombay)",
    "Dekkhan Agriculturists' Relief Act",
    "Shore Nuisances (Bombay and Kotaba)",
    "Revenue Commissioners, Bombay",
    "Revenue, Bombay",
]


# ============================================================
# FILES TO EXPLICITLY EXCLUDE
# ============================================================

EXCLUDE = [
    "Bihar Land Reforms Laws",
    "Goa, Daman and Diu (Extension of the Code of Civil Procedure",
    "Indian Institutes of Information Technology Act, 2014",
]


def should_keep(filename):
    name = filename.lower()

    # Explicit exclusions first
    for item in EXCLUDE:
        if item.lower() in name:
            return False

    # Constitution
    if filename.lower() == "constitution.pdf".lower():
        return True

    # Central Acts
    for item in CENTRAL_ACTS:
        if item.lower() in name:
            return True

    # Maharashtra/Bombay Acts
    for item in MAHARASHTRA_ACTS:
        if item.lower() in name:
            return True

    return False


# ============================================================
# CREATE DATASET
# ============================================================

source_files = list(SOURCE.glob("*.pdf"))

# Clear previous MVP copy only
for old_file in DEST.glob("*.pdf"):
    old_file.unlink()

copied = []

for pdf in source_files:
    if should_keep(pdf.name):
        shutil.copy2(pdf, DEST / pdf.name)
        copied.append(pdf.name)


print("=" * 65)
print("VIDHIK - MAHARASHTRA MVP DATASET")
print("=" * 65)
print(f"Original PDFs : {len(source_files)}")
print(f"MVP PDFs      : {len(copied)}")
print(f"Destination   : {DEST}")
print("=" * 65)

print("\nSELECTED FILES:\n")

for name in sorted(copied):
    print(name)

print("\n" + "=" * 65)
print("Original 847 PDFs were NOT deleted.")
print("=" * 65)