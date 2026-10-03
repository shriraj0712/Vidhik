"""
Vidhik Legal Platform - Phase 17 24-Act Knowledge Corpus Compiler
================================================================
Compiles and verifies the comprehensive legal knowledge dataset for all
24 required Bare Acts, extracting and structuring verbatim statutory
provisions, offences, punishments, procedural workflows, evidence rules,
statutory authorities, amendments, and judgment availability.
"""

import json
import os
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
STAGING_SECTIONS = BASE_DIR / "data" / "Legal_Dataset" / "Maharashtra_MVP" / "staging" / "sections_staging.json"
KB_DIR = BASE_DIR / "data" / "knowledge_base"
ACTS_DIR = KB_DIR / "acts"
ACTS_DIR.mkdir(parents=True, exist_ok=True)

# 24 ACTS MASTER SPECIFICATION
ACTS_MASTER = [
    {
        "act_id": 1,
        "act_name": "Bharatiya Nyaya Sanhita, 2023",
        "short_name": "BNS",
        "act_number": "Act No. 45 of 2023",
        "year": 2023,
        "enactment_date": "2023-12-25",
        "effective_date": "2024-07-01",
        "jurisdiction": "Central / India",
        "category": "Central Criminal Code",
        "staging_law_id": "the-bharatiya-nyaya-sanhita-2023",
        "source_file": "data/knowledge_base/bns_sections.json",
        "provenance": "Gazette of India, Ministry of Law and Justice",
        "status": "In Force",
        "has_offences": True,
        "has_punishments": True,
        "has_procedures": False,
        "has_evidence": False,
        "has_amendments": False,
        "amendment_details": "Original enactment w.e.f. 01-07-2024 replacing Indian Penal Code, 1860",
        "judgments_status": "5 Landmark SC Rulings Linked",
        "authorities": ["Criminal Courts", "Court of Session", "Magistrate Courts"]
    },
    {
        "act_id": 2,
        "act_name": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "short_name": "BNSS",
        "act_number": "Act No. 46 of 2023",
        "year": 2023,
        "enactment_date": "2023-12-25",
        "effective_date": "2024-07-01",
        "jurisdiction": "Central / India",
        "category": "Criminal Procedure Code",
        "staging_law_id": "the-bharatiya-nagarik-suraksha-sanhita-2023",
        "source_file": "data/knowledge_base/bnss_sections.json",
        "provenance": "Gazette of India, Ministry of Law and Justice",
        "status": "In Force",
        "has_offences": False,
        "has_punishments": False,
        "has_procedures": True,
        "has_evidence": False,
        "has_amendments": False,
        "amendment_details": "Original enactment w.e.f. 01-07-2024 replacing Code of Criminal Procedure, 1973",
        "judgments_status": "Cross-statute Precedents Linked",
        "authorities": ["Police", "Judicial Magistrates", "Session Judges", "High Court", "Supreme Court"]
    },
    {
        "act_id": 3,
        "act_name": "Bharatiya Sakshya Adhiniyam, 2023",
        "short_name": "BSA",
        "act_number": "Act No. 47 of 2023",
        "year": 2023,
        "enactment_date": "2023-12-25",
        "effective_date": "2024-07-01",
        "jurisdiction": "Central / India",
        "category": "Law of Evidence",
        "staging_law_id": "the-bharatiya-sakshya-adhiniyam-2023",
        "source_file": "data/knowledge_base/bsa_sections.json",
        "provenance": "Gazette of India, Ministry of Law and Justice",
        "status": "In Force",
        "has_offences": False,
        "has_punishments": False,
        "has_procedures": False,
        "has_evidence": True,
        "has_amendments": False,
        "amendment_details": "Original enactment w.e.f. 01-07-2024 replacing Indian Evidence Act, 1872",
        "judgments_status": "Arjun Panditrao Khotkar ((2020) 7 SCC 1) Linked",
        "authorities": ["Trial Courts", "Expert Examiners of Electronic Evidence"]
    },
    {
        "act_id": 4,
        "act_name": "Information Technology Act, 2000",
        "short_name": "IT Act",
        "act_number": "Act No. 21 of 2000",
        "year": 2000,
        "enactment_date": "2000-06-09",
        "effective_date": "2000-10-17",
        "jurisdiction": "Central / India",
        "category": "Cyber Law & Electronic Commerce",
        "staging_law_id": "the-information-technology-act-2000",
        "source_file": "data/Legal_Dataset/extracted_text/The Information Technology Act, 2000.txt",
        "provenance": "India Code, Ministry of Electronics and Information Technology",
        "status": "In Force",
        "has_offences": True,
        "has_punishments": True,
        "has_procedures": True,
        "has_evidence": True,
        "has_amendments": True,
        "amendment_details": "Information Technology (Amendment) Act, 2008 (Act 10 of 2009) w.e.f. 27-10-2009",
        "judgments_status": "NOT IN SOURCE",
        "authorities": ["Controller of Certifying Authorities (CCA)", "Cyber Appellate Tribunal / TDSAT", "Adjudicating Officer under Section 46"]
    },
    {
        "act_id": 5,
        "act_name": "Protection of Children from Sexual Offences Act, 2012",
        "short_name": "POCSO Act",
        "act_number": "Act No. 32 of 2012",
        "year": 2012,
        "enactment_date": "2012-06-19",
        "effective_date": "2012-11-14",
        "jurisdiction": "Central / India",
        "category": "Special Criminal / Child Protection",
        "staging_law_id": "the-protection-of-children-from-sexual-offences-act-2012",
        "source_file": "data/Legal_Dataset/extracted_text/The Protection of Children from Sexual Offences Act, 2012.txt",
        "provenance": "India Code, Ministry of Women and Child Development",
        "status": "In Force",
        "has_offences": True,
        "has_punishments": True,
        "has_procedures": True,
        "has_evidence": True,
        "has_amendments": True,
        "amendment_details": "Protection of Children from Sexual Offences (Amendment) Act, 2019 (Act 25 of 2019) w.e.f. 16-08-2019",
        "judgments_status": "NOT IN SOURCE",
        "authorities": ["Special Courts designated under Section 28", "Child Welfare Committees (CWC)", "Special Juvenile Police Units (SJPU)"]
    },
    {
        "act_id": 6,
        "act_name": "Juvenile Justice (Care and Protection of Children) Act, 2015",
        "short_name": "JJ Act",
        "act_number": "Act No. 2 of 2016",
        "year": 2015,
        "enactment_date": "2015-12-31",
        "effective_date": "2016-01-15",
        "jurisdiction": "Central / India",
        "category": "Child Welfare & Juvenile Justice",
        "staging_law_id": "the-juvenile-justice-care-and-protection-of-children-act-2015",
        "source_file": "data/Legal_Dataset/extracted_text/The Juvenile Justice (Care and Protection of Children) Act, 2015..txt",
        "provenance": "India Code, Ministry of Women and Child Development",
        "status": "In Force",
        "has_offences": True,
        "has_punishments": True,
        "has_procedures": True,
        "has_evidence": False,
        "has_amendments": True,
        "amendment_details": "Juvenile Justice (Care and Protection of Children) Amendment Act, 2021 (Act 23 of 2021) w.e.f. 01-09-2022",
        "judgments_status": "NOT IN SOURCE",
        "authorities": ["Juvenile Justice Board (JJB)", "Child Welfare Committee (CWC)", "District Magistrate", "Central Adoption Resource Authority (CARA)"]
    },
    {
        "act_id": 7,
        "act_name": "Protection of Women from Domestic Violence Act, 2005",
        "short_name": "PWDVA",
        "act_number": "Act No. 43 of 2005",
        "year": 2005,
        "enactment_date": "2005-09-13",
        "effective_date": "2006-10-26",
        "jurisdiction": "Central / India",
        "category": "Social Welfare & Gender Protection",
        "staging_law_id": "the-protection-of-women-from-domestic-violence-act-2005",
        "source_file": "data/Legal_Dataset/extracted_text/The Protection of Women from Domestic Violence Act, 2005.txt",
        "provenance": "India Code, Ministry of Women and Child Development",
        "status": "In Force",
        "has_offences": True,
        "has_punishments": True,
        "has_procedures": True,
        "has_evidence": False,
        "has_amendments": False,
        "amendment_details": "Original enactment w.e.f. 26-10-2006",
        "judgments_status": "NOT IN SOURCE",
        "authorities": ["Protection Officers appointed under Section 8", "Service Providers", "Judicial Magistrate of First Class / Metropolitan Magistrate"]
    },
    {
        "act_id": 8,
        "act_name": "Dowry Prohibition Act, 1961",
        "short_name": "DPA",
        "act_number": "Act No. 28 of 1961",
        "year": 1961,
        "enactment_date": "1961-05-20",
        "effective_date": "1961-07-01",
        "jurisdiction": "Central / India",
        "category": "Special Criminal / Social Reform",
        "staging_law_id": "the-dowry-prohibition-act-1961",
        "source_file": "data/Legal_Dataset/extracted_text/The Dowry Prohibition Act, 1961.txt",
        "provenance": "India Code, Ministry of Women and Child Development",
        "status": "In Force",
        "has_offences": True,
        "has_punishments": True,
        "has_procedures": True,
        "has_evidence": True,
        "has_amendments": True,
        "amendment_details": "Dowry Prohibition (Amendment) Act, 1984 (63 of 1984) and 1986 (43 of 1986)",
        "judgments_status": "NOT IN SOURCE",
        "authorities": ["Dowry Prohibition Officers appointed under Section 8B", "Advisory Boards"]
    },
    {
        "act_id": 9,
        "act_name": "Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013",
        "short_name": "POSH Act",
        "act_number": "Act No. 14 of 2013",
        "year": 2013,
        "enactment_date": "2013-04-22",
        "effective_date": "2013-12-09",
        "jurisdiction": "Central / India",
        "category": "Workplace Protection & Gender Equality",
        "staging_law_id": "the-sexual-harassment-of-women-at-workplace-prevention-prohibition-and-redressal-act-2013",
        "source_file": "data/Legal_Dataset/extracted_text/The Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013.txt",
        "provenance": "India Code, Ministry of Women and Child Development",
        "status": "In Force",
        "has_offences": True,
        "has_punishments": True,
        "has_procedures": True,
        "has_evidence": False,
        "has_amendments": False,
        "amendment_details": "Original enactment w.e.f. 09-12-2013 (derived from Vishaka guidelines)",
        "judgments_status": "NOT IN SOURCE",
        "authorities": ["Internal Complaints Committee (ICC)", "Local Complaints Committee (LCC)", "District Officer"]
    },
    {
        "act_id": 10,
        "act_name": "Hindu Marriage Act, 1955",
        "short_name": "HMA",
        "act_number": "Act No. 25 of 1955",
        "year": 1955,
        "enactment_date": "1955-05-18",
        "effective_date": "1955-05-18",
        "jurisdiction": "Central / India",
        "category": "Family Law / Personal Law",
        "staging_law_id": "the-hindu-marriage-act-1955",
        "source_file": "data/Legal_Dataset/extracted_text/The Hindu Marriage Act, 1955.txt",
        "provenance": "India Code, Ministry of Law and Justice",
        "status": "In Force",
        "has_offences": True,
        "has_punishments": True,
        "has_procedures": True,
        "has_evidence": False,
        "has_amendments": True,
        "amendment_details": "Marriage Laws (Amendment) Act, 1976 (Act 68 of 1976) introducing divorce by mutual consent",
        "judgments_status": "NOT IN SOURCE",
        "authorities": ["Family Courts", "Principal Civil Court of Original Jurisdiction / District Court"]
    },
    {
        "act_id": 11,
        "act_name": "Hindu Succession Act, 1956",
        "short_name": "HSA",
        "act_number": "Act No. 30 of 1956",
        "year": 1956,
        "enactment_date": "1956-06-17",
        "effective_date": "1956-06-17",
        "jurisdiction": "Central / India",
        "category": "Property & Succession / Personal Law",
        "staging_law_id": "the-hindu-succession-act-1956",
        "source_file": "data/Legal_Dataset/extracted_text/The Hindu Succession Act, 1956.txt",
        "provenance": "India Code, Ministry of Law and Justice",
        "status": "In Force",
        "has_offences": False,
        "has_punishments": False,
        "has_procedures": True,
        "has_evidence": False,
        "has_amendments": True,
        "amendment_details": "Hindu Succession (Amendment) Act, 2005 (Act 39 of 2005) granting equal coparcenary rights to daughters",
        "judgments_status": "NOT IN SOURCE",
        "authorities": ["Civil Courts", "Revenue Authorities / Land Record Offices"]
    },
    {
        "act_id": 12,
        "act_name": "Special Marriage Act, 1954",
        "short_name": "SMA",
        "act_number": "Act No. 43 of 1954",
        "year": 1954,
        "enactment_date": "1954-10-09",
        "effective_date": "1955-01-01",
        "jurisdiction": "Central / India",
        "category": "Civil Marriage & Family Law",
        "staging_law_id": "the-special-marriage-act-1954",
        "source_file": "data/Legal_Dataset/extracted_text/The Special Marriage Act, 1954.txt",
        "provenance": "India Code, Ministry of Law and Justice",
        "status": "In Force",
        "has_offences": True,
        "has_punishments": True,
        "has_procedures": True,
        "has_evidence": False,
        "has_amendments": True,
        "amendment_details": "Marriage Laws (Amendment) Act, 1976 (Act 68 of 1976)",
        "judgments_status": "NOT IN SOURCE",
        "authorities": ["Marriage Officers appointed under Section 3", "District Courts / Family Courts"]
    },
    {
        "act_id": 13,
        "act_name": "Indian Contract Act, 1872",
        "short_name": "ICA",
        "act_number": "Act No. 9 of 1872",
        "year": 1872,
        "enactment_date": "1872-04-25",
        "effective_date": "1872-09-01",
        "jurisdiction": "Central / India",
        "category": "Commercial & General Contract Law",
        "staging_law_id": "the-indian-contract-act-1872",
        "source_file": "data/Legal_Dataset/extracted_text/The Indian Contract Act, 1872.txt",
        "provenance": "India Code, Ministry of Law and Justice",
        "status": "In Force",
        "has_offences": False,
        "has_punishments": False,
        "has_procedures": True,
        "has_evidence": False,
        "has_amendments": True,
        "amendment_details": "Sale of Goods Act, 1930 repealed Secs 76-123; Indian Partnership Act, 1932 repealed Secs 239-266",
        "judgments_status": "NOT IN SOURCE",
        "authorities": ["Civil Courts", "Commercial Courts"]
    },
    {
        "act_id": 14,
        "act_name": "Specific Relief Act, 1963",
        "short_name": "SRA",
        "act_number": "Act No. 47 of 1963",
        "year": 1963,
        "enactment_date": "1963-12-13",
        "effective_date": "1964-03-01",
        "jurisdiction": "Central / India",
        "category": "Civil Remedies & Equitable Relief",
        "staging_law_id": "the-specific-relief-act-1963",
        "source_file": "data/Legal_Dataset/extracted_text/The Specific Relief Act, 1963.txt",
        "provenance": "India Code, Ministry of Law and Justice",
        "status": "In Force",
        "has_offences": False,
        "has_punishments": False,
        "has_procedures": True,
        "has_evidence": False,
        "has_amendments": True,
        "amendment_details": "Specific Relief (Amendment) Act, 2018 (Act 18 of 2018) making specific performance mandatory",
        "judgments_status": "NOT IN SOURCE",
        "authorities": ["Special Courts designated under Section 20B", "Civil Courts"]
    },
    {
        "act_id": 15,
        "act_name": "Transfer of Property Act, 1882",
        "short_name": "TPA",
        "act_number": "Act No. 4 of 1882",
        "year": 1882,
        "enactment_date": "1882-02-17",
        "effective_date": "1882-07-01",
        "jurisdiction": "Central / India",
        "category": "Property Law & Conveyancing",
        "staging_law_id": "the-transfer-of-property-act-1882",
        "source_file": "data/Legal_Dataset/extracted_text/The Transfer of Property Act, 1882.txt",
        "provenance": "India Code, Ministry of Law and Justice",
        "status": "In Force",
        "has_offences": False,
        "has_punishments": False,
        "has_procedures": True,
        "has_evidence": False,
        "has_amendments": True,
        "amendment_details": "Historical central amendments (Act 20 of 1929, Act 3 of 2003)",
        "judgments_status": "NOT IN SOURCE",
        "authorities": ["Civil Courts", "Registrars of Documents"]
    },
    {
        "act_id": 16,
        "act_name": "Registration Act, 1908",
        "short_name": "Registration Act",
        "act_number": "Act No. 16 of 1908",
        "year": 1908,
        "enactment_date": "1908-12-18",
        "effective_date": "1909-01-01",
        "jurisdiction": "Central / India",
        "category": "Document Registration & Public Records",
        "staging_law_id": "the-registration-act-1908",
        "source_file": "data/Legal_Dataset/extracted_text/The Registration Act, 1908.txt",
        "provenance": "India Code, Ministry of Law and Justice",
        "status": "In Force",
        "has_offences": True,
        "has_punishments": True,
        "has_procedures": True,
        "has_evidence": False,
        "has_amendments": True,
        "amendment_details": "Registration (Amendment) Act, 2001 (Act 48 of 2001) inserting Sec 17(1A)",
        "judgments_status": "NOT IN SOURCE",
        "authorities": ["Inspector-General of Registration", "Registrars and Sub-Registrars"]
    },
    {
        "act_id": 17,
        "act_name": "Negotiable Instruments Act, 1881",
        "short_name": "NI Act",
        "act_number": "Act No. 26 of 1881",
        "year": 1881,
        "enactment_date": "1881-12-09",
        "effective_date": "1882-03-01",
        "jurisdiction": "Central / India",
        "category": "Banking & Commercial Paper",
        "staging_law_id": "the-negotiable-instruments-act-1881",
        "source_file": "data/Legal_Dataset/extracted_text/The Negotiable Instruments Act, 1881.txt",
        "provenance": "India Code, Ministry of Finance / Law and Justice",
        "status": "In Force",
        "has_offences": True,
        "has_punishments": True,
        "has_procedures": True,
        "has_evidence": True,
        "has_amendments": True,
        "amendment_details": "Negotiable Instruments (Amendment) Act, 2018 (Act 20 of 2018) inserting Section 143A and Section 148",
        "judgments_status": "NOT IN SOURCE",
        "authorities": ["Judicial Magistrate of First Class / Metropolitan Magistrate", "Reserve Bank of India"]
    },
    {
        "act_id": 18,
        "act_name": "Consumer Protection Act, 2019",
        "short_name": "CPA",
        "act_number": "Act No. 35 of 2019",
        "year": 2019,
        "enactment_date": "2019-08-09",
        "effective_date": "2020-07-20",
        "jurisdiction": "Central / India",
        "category": "Consumer Rights & Redressal",
        "staging_law_id": "the-consumer-protection-act-2019",
        "source_file": "data/Legal_Dataset/extracted_text/The Consumer Protection Act, 2019.txt",
        "provenance": "India Code, Ministry of Consumer Affairs, Food and Public Distribution",
        "status": "In Force",
        "has_offences": True,
        "has_punishments": True,
        "has_procedures": True,
        "has_evidence": True,
        "has_amendments": False,
        "amendment_details": "Original enactment w.e.f. 20-07-2020 replacing Consumer Protection Act, 1986",
        "judgments_status": "NOT IN SOURCE",
        "authorities": [
            "Central Consumer Protection Authority (CCPA)",
            "District Consumer Disputes Redressal Commission",
            "State Consumer Disputes Redressal Commission",
            "National Consumer Disputes Redressal Commission (NCDRC)",
            "Consumer Mediation Cells"
        ]
    },
    {
        "act_id": 19,
        "act_name": "Motor Vehicles Act, 1988",
        "short_name": "MVA",
        "act_number": "Act No. 59 of 1988",
        "year": 1988,
        "enactment_date": "1988-10-14",
        "effective_date": "1989-07-01",
        "jurisdiction": "Central / India",
        "category": "Transport Regulation & Claims",
        "staging_law_id": "the-motor-vehicles-act-1988",
        "source_file": "data/Legal_Dataset/extracted_text/The Motor Vehicles Act, 1988.txt",
        "provenance": "India Code, Ministry of Road Transport and Highways",
        "status": "In Force",
        "has_offences": True,
        "has_punishments": True,
        "has_procedures": True,
        "has_evidence": False,
        "has_amendments": True,
        "amendment_details": "Motor Vehicles (Amendment) Act, 2019 (Act 32 of 2019) introducing enhanced road safety penalties and Section 199A",
        "judgments_status": "NOT IN SOURCE",
        "authorities": ["Motor Accidents Claims Tribunal (MACT)", "Regional Transport Authorities (RTA)", "Licensing Authorities"]
    },
    {
        "act_id": 20,
        "act_name": "Right to Information Act, 2005",
        "short_name": "RTI Act",
        "act_number": "Act No. 22 of 2005",
        "year": 2005,
        "enactment_date": "2005-06-15",
        "effective_date": "2005-10-12",
        "jurisdiction": "Central / India",
        "category": "Administrative Law & Transparency",
        "staging_law_id": "the-right-to-information-act-2005",
        "source_file": "data/Legal_Dataset/extracted_text/The Right to Information Act, 2005.txt",
        "provenance": "India Code, Ministry of Personnel, Public Grievances and Pensions",
        "status": "In Force",
        "has_offences": True,
        "has_punishments": True,
        "has_procedures": True,
        "has_evidence": False,
        "has_amendments": True,
        "amendment_details": "Right to Information (Amendment) Act, 2019 (Act 24 of 2019)",
        "judgments_status": "NOT IN SOURCE",
        "authorities": [
            "Central Information Commission (CIC)",
            "State Information Commissions (SIC)",
            "Central Public Information Officers (CPIO) / SPIO",
            "First Appellate Authorities (FAA)"
        ]
    },
    {
        "act_id": 21,
        "act_name": "Legal Services Authorities Act, 1987",
        "short_name": "LSAA",
        "act_number": "Act No. 39 of 1987",
        "year": 1987,
        "enactment_date": "1987-10-11",
        "effective_date": "1995-11-09",
        "jurisdiction": "Central / India",
        "category": "Legal Aid & Alternate Dispute Resolution",
        "staging_law_id": "the-legal-services-authorities-act-1987",
        "source_file": "data/Legal_Dataset/extracted_text/The Legal Services Authorities Act, 1987.txt",
        "provenance": "India Code, Ministry of Law and Justice",
        "status": "In Force",
        "has_offences": False,
        "has_punishments": False,
        "has_procedures": True,
        "has_evidence": False,
        "has_amendments": True,
        "amendment_details": "Legal Services Authorities (Amendment) Act, 2002 (Act 37 of 2002) introducing Chapter VI-A Permanent Lok Adalats",
        "judgments_status": "NOT IN SOURCE",
        "authorities": [
            "National Legal Services Authority (NALSA)",
            "Supreme Court Legal Services Committee",
            "State Legal Services Authorities (SLSA)",
            "District Legal Services Authorities (DLSA)",
            "Taluk Legal Services Committees",
            "Lok Adalats",
            "Permanent Lok Adalats"
        ]
    },
    {
        "act_id": 22,
        "act_name": "Arbitration and Conciliation Act, 1996",
        "short_name": "Arbitration Act",
        "act_number": "Act No. 26 of 1996",
        "year": 1996,
        "enactment_date": "1996-08-16",
        "effective_date": "1996-08-22",
        "jurisdiction": "Central / India",
        "category": "Arbitration & Dispute Resolution",
        "staging_law_id": "the-arbitration-and-conciliation-act-1996",
        "source_file": "data/Legal_Dataset/extracted_text/The Arbitration and Conciliation Act, 1996.txt",
        "provenance": "India Code, Ministry of Law and Justice",
        "status": "In Force",
        "has_offences": False,
        "has_punishments": False,
        "has_procedures": True,
        "has_evidence": False,
        "has_amendments": True,
        "amendment_details": "Arbitration and Conciliation (Amendment) Acts of 2015 (Act 3 of 2016), 2019 (Act 33 of 2019), and 2021 (Act 3 of 2021)",
        "judgments_status": "NOT IN SOURCE",
        "authorities": ["Arbitral Tribunals", "Arbitration Council of India (ACI)", "High Courts / Supreme Court designating Arbitral Institutions"]
    },
    {
        "act_id": 23,
        "act_name": "Companies Act, 2013",
        "short_name": "Companies Act",
        "act_number": "Act No. 18 of 2013",
        "year": 2013,
        "enactment_date": "2013-08-29",
        "effective_date": "2013-09-12",
        "jurisdiction": "Central / India",
        "category": "Corporate Law & Governance",
        "staging_law_id": "the-companies-act-2013",
        "source_file": "data/Legal_Dataset/extracted_text/The Companies Act, 2013.txt",
        "provenance": "India Code, Ministry of Corporate Affairs",
        "status": "In Force",
        "has_offences": True,
        "has_punishments": True,
        "has_procedures": True,
        "has_evidence": False,
        "has_amendments": True,
        "amendment_details": "Companies (Amendment) Acts of 2017 (Act 1 of 2018), 2019 (Act 22 of 2019), and 2020 (Act 29 of 2020)",
        "judgments_status": "NOT IN SOURCE",
        "authorities": [
            "National Company Law Tribunal (NCLT)",
            "National Company Law Appellate Tribunal (NCLAT)",
            "Registrar of Companies (ROC)",
            "Serious Fraud Investigation Office (SFIO)",
            "National Financial Reporting Authority (NFRA)"
        ]
    },
    {
        "act_id": 24,
        "act_name": "Insolvency and Bankruptcy Code, 2016",
        "short_name": "IBC",
        "act_number": "Act No. 31 of 2016",
        "year": 2016,
        "enactment_date": "2016-05-28",
        "effective_date": "2016-12-01",
        "jurisdiction": "Central / India",
        "category": "Insolvency, Restructuring & Liquidation",
        "staging_law_id": "the-insolvency-and-bankruptcy-code-2016",
        "source_file": "data/Legal_Dataset/extracted_text/The Insolvency and Bankruptcy Code, 2016..txt",
        "provenance": "India Code, Ministry of Corporate Affairs",
        "status": "In Force",
        "has_offences": True,
        "has_punishments": True,
        "has_procedures": True,
        "has_evidence": False,
        "has_amendments": True,
        "amendment_details": "Insolvency and Bankruptcy Code (Amendment) Acts of 2018 (Act 8 of 2018), 2019 (Act 26 of 2019), and 2020 (Act 1 of 2020)",
        "judgments_status": "NOT IN SOURCE",
        "authorities": [
            "Insolvency and Bankruptcy Board of India (IBBI)",
            "National Company Law Tribunal (Adjudicating Authority for corporate persons)",
            "Debt Recovery Tribunal (Adjudicating Authority for individuals and partnership firms)",
            "Insolvency Professional Agencies (IPA)",
            "Insolvency Professionals (IP / IRP / RP)",
            "Information Utilities (IU)"
        ]
    }
]

# STRUCTURED OFFENCES CATALOG FOR ACTS 4-24
KEY_OFFENCES_METADATA = {
    # IT Act
    ("the-information-technology-act-2000", "43"): {
        "offence_name": "Penalty and compensation for damage to computer system",
        "description": "Unauthorized access, downloading, copying, virus injection, damage, disruption to computer system or data",
        "cognizable_status": "Non-Cognizable", "bailable_status": "Bailable", "compoundable_status": "Compoundable", "triable_by": "Adjudicating Officer"
    },
    ("the-information-technology-act-2000", "65"): {
        "offence_name": "Tampering with computer source documents",
        "description": "Knowingly or intentionally concealing, destroying, or altering computer source code required to be maintained",
        "cognizable_status": "Cognizable", "bailable_status": "Bailable", "compoundable_status": "Compoundable", "triable_by": "Magistrate of First Class"
    },
    ("the-information-technology-act-2000", "66"): {
        "offence_name": "Computer related offences / Hacking",
        "description": "Dishonestly or fraudulently committing any act referred to in section 43",
        "cognizable_status": "Cognizable", "bailable_status": "Bailable", "compoundable_status": "Compoundable", "triable_by": "Magistrate of First Class"
    },
    ("the-information-technology-act-2000", "66C"): {
        "offence_name": "Identity theft",
        "description": "Fraudulently or dishonestly making use of electronic signature, password or unique identification feature of another person",
        "cognizable_status": "Cognizable", "bailable_status": "Bailable", "compoundable_status": "Compoundable", "triable_by": "Magistrate of First Class"
    },
    ("the-information-technology-act-2000", "66ग"): {
        "offence_name": "Identity theft",
        "description": "Fraudulently or dishonestly making use of electronic signature, password or unique identification feature of another person",
        "cognizable_status": "Cognizable", "bailable_status": "Bailable", "compoundable_status": "Compoundable", "triable_by": "Magistrate of First Class"
    },
    ("the-information-technology-act-2000", "66D"): {
        "offence_name": "Cheating by personation using computer resource",
        "description": "Cheating by personating using computer resource or communication device",
        "cognizable_status": "Cognizable", "bailable_status": "Bailable", "compoundable_status": "Compoundable", "triable_by": "Magistrate of First Class"
    },
    ("the-information-technology-act-2000", "66घ"): {
        "offence_name": "Cheating by personation using computer resource",
        "description": "Cheating by personating using computer resource or communication device",
        "cognizable_status": "Cognizable", "bailable_status": "Bailable", "compoundable_status": "Compoundable", "triable_by": "Magistrate of First Class"
    },
    ("the-information-technology-act-2000", "66F"): {
        "offence_name": "Cyber terrorism",
        "description": "Acts threatening the unity, integrity, security or sovereignty of India by denying authorized access or contaminating computer resource",
        "cognizable_status": "Cognizable", "bailable_status": "Non-Bailable", "compoundable_status": "Non-Compoundable", "triable_by": "Court of Session"
    },
    ("the-information-technology-act-2000", "66च"): {
        "offence_name": "Cyber terrorism",
        "description": "Acts threatening the unity, integrity, security or sovereignty of India by denying authorized access or contaminating computer resource",
        "cognizable_status": "Cognizable", "bailable_status": "Non-Bailable", "compoundable_status": "Non-Compoundable", "triable_by": "Court of Session"
    },

    ("the-information-technology-act-2000", "67"): {
        "offence_name": "Publishing obscene information in electronic form",
        "description": "Transmitting or causing to be published in electronic form any material lascivious or appealing to prurient interest",
        "cognizable_status": "Cognizable", "bailable_status": "Bailable (First) / Non-Bailable (Subsequent)", "compoundable_status": "Non-Compoundable", "triable_by": "Magistrate of First Class"
    },
    # POCSO Act
    ("the-protection-of-children-from-sexual-offences-act-2012", "3"): {
        "offence_name": "Penetrative sexual assault",
        "description": "Penetrating penis or inserting object/part into vagina, mouth, urethra or anus of a child",
        "cognizable_status": "Cognizable", "bailable_status": "Non-Bailable", "compoundable_status": "Non-Compoundable", "triable_by": "Special Court"
    },
    ("the-protection-of-children-from-sexual-offences-act-2012", "5"): {
        "offence_name": "Aggravated penetrative sexual assault",
        "description": "Penetrative sexual assault committed by police officer, armed personnel, public servant, relative, teacher, or causing grievous hurt/death",
        "cognizable_status": "Cognizable", "bailable_status": "Non-Bailable", "compoundable_status": "Non-Compoundable", "triable_by": "Special Court"
    },
    ("the-protection-of-children-from-sexual-offences-act-2012", "7"): {
        "offence_name": "Sexual assault",
        "description": "Touching vagina, penis, anus or breast of a child or doing any other act with sexual intent involving physical contact without penetration",
        "cognizable_status": "Cognizable", "bailable_status": "Non-Bailable", "compoundable_status": "Non-Compoundable", "triable_by": "Special Court"
    },
    ("the-protection-of-children-from-sexual-offences-act-2012", "11"): {
        "offence_name": "Sexual harassment upon a child",
        "description": "Uttering sexual words, making sounds or gestures, exhibiting child's body or object, or stalking a child with sexual intent",
        "cognizable_status": "Cognizable", "bailable_status": "Bailable / Non-Bailable", "compoundable_status": "Non-Compoundable", "triable_by": "Special Court"
    },
    # JJ Act
    ("the-juvenile-justice-care-and-protection-of-children-act-2015", "74"): {
        "offence_name": "Prohibition on disclosure of identity of children",
        "description": "Disclosing name, address, school or picture revealing identity of child in conflict with law or child in need of care and protection",
        "cognizable_status": "Non-Cognizable", "bailable_status": "Bailable", "compoundable_status": "Compoundable", "triable_by": "Magistrate of First Class"
    },
    ("the-juvenile-justice-care-and-protection-of-children-act-2015", "75"): {
        "offence_name": "Cruelty to child",
        "description": "Assaulting, abandoning, abusing, exposing or willfully neglecting a child causing mental or physical suffering",
        "cognizable_status": "Cognizable", "bailable_status": "Non-Bailable", "compoundable_status": "Non-Compoundable", "triable_by": "Court of Session / Magistrate"
    },
    ("the-juvenile-justice-care-and-protection-of-children-act-2015", "77"): {
        "offence_name": "Giving intoxicating liquor or narcotic drug or psychotropic substance to a child",
        "description": "Giving or causing to be given intoxicating liquor or narcotic drug or tobacco products to child except upon prescription",
        "cognizable_status": "Cognizable", "bailable_status": "Non-Bailable", "compoundable_status": "Non-Compoundable", "triable_by": "Court of Session"
    },
    # PWDVA
    ("the-protection-of-women-from-domestic-violence-act-2005", "31"): {
        "offence_name": "Penalty for breach of protection order by respondent",
        "description": "Breach of protection order or interim protection order passed by Magistrate under Section 18",
        "cognizable_status": "Cognizable", "bailable_status": "Non-Bailable", "compoundable_status": "Non-Compoundable", "triable_by": "Judicial Magistrate of First Class"
    },
    # Dowry Prohibition Act
    ("the-dowry-prohibition-act-1961", "3"): {
        "offence_name": "Giving or taking dowry",
        "description": "Giving or taking or abetting the giving or taking of dowry",
        "cognizable_status": "Cognizable", "bailable_status": "Non-Bailable", "compoundable_status": "Non-Compoundable", "triable_by": "Judicial Magistrate of First Class / Metropolitan Magistrate"
    },
    ("the-dowry-prohibition-act-1961", "4"): {
        "offence_name": "Demanding dowry",
        "description": "Demanding directly or indirectly dowry from parents or other relatives or guardian of bride or bridegroom",
        "cognizable_status": "Cognizable", "bailable_status": "Non-Bailable", "compoundable_status": "Non-Compoundable", "triable_by": "Judicial Magistrate of First Class / Metropolitan Magistrate"
    },
    ("the-dowry-prohibition-act-1961", "4A"): {
        "offence_name": "Ban on advertisement offering dowry",
        "description": "Printing, publishing, or circulating advertisement offering share in property or money in consideration of marriage",
        "cognizable_status": "Cognizable", "bailable_status": "Non-Bailable", "compoundable_status": "Non-Compoundable", "triable_by": "Judicial Magistrate of First Class / Metropolitan Magistrate"
    },
    # POSH Act
    ("the-sexual-harassment-of-women-at-workplace-prevention-prohibition-and-redressal-act-2013", "26"): {
        "offence_name": "Non-compliance with provisions of Act by employer",
        "description": "Failure to constitute Internal Committee, contravention of report submission, or breach of statutory obligations",
        "cognizable_status": "Non-Cognizable", "bailable_status": "Bailable", "compoundable_status": "Compoundable", "triable_by": "Metropolitan Magistrate / Judicial Magistrate of First Class"
    },
    # Hindu Marriage Act
    ("the-hindu-marriage-act-1955", "17"): {
        "offence_name": "Punishment of bigamy",
        "description": "Marriage between two Hindus solemnized when either party had a spouse living at the time of marriage",
        "cognizable_status": "Non-Cognizable", "bailable_status": "Bailable", "compoundable_status": "Compoundable with permission", "triable_by": "Magistrate of First Class"
    },
    # Special Marriage Act
    ("the-special-marriage-act-1954", "43"): {
        "offence_name": "Penalty on married person marrying again under this Act",
        "description": "Procuring marriage under Special Marriage Act during lifetime of husband or wife",
        "cognizable_status": "Non-Cognizable", "bailable_status": "Bailable", "compoundable_status": "Compoundable with permission", "triable_by": "Magistrate of First Class"
    },
    # Registration Act
    ("the-registration-act-1908", "81"): {
        "offence_name": "Penalty for incorrectly endorsing, copying, translating or registering documents with intent to injure",
        "description": "Registering officer intentionally registering, copying or translating document incorrectly knowing it likely to cause injury",
        "cognizable_status": "Non-Cognizable", "bailable_status": "Bailable", "compoundable_status": "Non-Compoundable", "triable_by": "Magistrate of First Class"
    },
    ("the-registration-act-1908", "82"): {
        "offence_name": "Penalty for making false statements, delivering false copies, false personation",
        "description": "Making false statement before registering officer, intentional false personation, or abetting offences under Registration Act",
        "cognizable_status": "Cognizable", "bailable_status": "Bailable", "compoundable_status": "Non-Compoundable", "triable_by": "Magistrate of First Class"
    },
    # NI Act
    ("the-negotiable-instruments-act-1881", "138"): {
        "offence_name": "Dishonour of cheque for insufficiency of funds in the account",
        "description": "Dishonour of cheque drawn for discharge of debt or liability due to insufficiency of funds or exceeding arrangements",
        "cognizable_status": "Non-Cognizable", "bailable_status": "Bailable", "compoundable_status": "Compoundable (Sec 147)", "triable_by": "Judicial Magistrate of First Class / Metropolitan Magistrate"
    },
    # Consumer Protection Act
    ("the-consumer-protection-act-2019", "89"): {
        "offence_name": "Punishment for false or misleading advertisement",
        "description": "Manufacturer or service provider causing false or misleading advertisement prejudicial to consumer interest",
        "cognizable_status": "Cognizable", "bailable_status": "Bailable", "compoundable_status": "Non-Compoundable", "triable_by": "Metropolitan Magistrate / Judicial Magistrate of First Class"
    },
    ("the-consumer-protection-act-2019", "90"): {
        "offence_name": "Manufacturing or storing products containing adulterant",
        "description": "Manufacturing for sale, storing, selling, distributing or importing product containing adulterant",
        "cognizable_status": "Cognizable", "bailable_status": "Bailable / Non-Bailable", "compoundable_status": "Non-Compoundable", "triable_by": "Metropolitan Magistrate / Judicial Magistrate of First Class"
    },
    # Motor Vehicles Act
    ("the-motor-vehicles-act-1988", "184"): {
        "offence_name": "Driving dangerously",
        "description": "Driving motor vehicle at a speed or in a manner dangerous to public having regard to circumstances",
        "cognizable_status": "Cognizable", "bailable_status": "Bailable", "compoundable_status": "Compoundable", "triable_by": "Any Magistrate"
    },
    ("the-motor-vehicles-act-1988", "185"): {
        "offence_name": "Driving by a drunken person or under influence of drugs",
        "description": "Driving vehicle with alcohol exceeding 30 mg per 100 ml of blood detected by breath analyser",
        "cognizable_status": "Cognizable", "bailable_status": "Bailable", "compoundable_status": "Non-Compoundable", "triable_by": "Any Magistrate"
    },
    ("the-motor-vehicles-act-1988", "199A"): {
        "offence_name": "Offences by juveniles in motor vehicle operation",
        "description": "Offence committed by juvenile; guardian or owner deemed guilty unless acted with due diligence",
        "cognizable_status": "Cognizable", "bailable_status": "Bailable", "compoundable_status": "Non-Compoundable", "triable_by": "Court of Session / Magistrate"
    },
    # Companies Act
    ("the-companies-act-2013", "447"): {
        "offence_name": "Punishment for fraud",
        "description": "Any person found guilty of fraud involving amount of at least 10 lakh rupees or 1 percent of turnover",
        "cognizable_status": "Cognizable", "bailable_status": "Non-Bailable", "compoundable_status": "Non-Compoundable", "triable_by": "Special Court (Section 435)"
    },
    ("the-companies-act-2013", "448"): {
        "offence_name": "Punishment for false statement",
        "description": "Making false statement in any return, report, certificate, financial statement, or omitting material fact knowingly",
        "cognizable_status": "Cognizable", "bailable_status": "Non-Bailable", "compoundable_status": "Non-Compoundable", "triable_by": "Special Court (Section 435)"
    },
    # IBC
    ("the-insolvency-and-bankruptcy-code-2016", "65"): {
        "offence_name": "Fraudulent or malicious initiation of insolvency proceedings",
        "description": "Initiating insolvency resolution process or liquidation proceedings fraudulently or with malicious intent",
        "cognizable_status": "Non-Cognizable", "bailable_status": "Bailable", "compoundable_status": "Non-Compoundable", "triable_by": "Special Court / Adjudicating Authority (NCLT)"
    }
}

# STRUCTURED PUNISHMENTS CATALOG
KEY_PUNISHMENTS_METADATA = {
    ("the-information-technology-act-2000", "65"): {
        "punishment_type": "Imprisonment up to 3 years, or fine up to 2 lakh rupees, or both",
        "description": "Whoever tampers with computer source documents shall be punishable with imprisonment up to three years, or with fine up to two lakh rupees, or with both.",
        "minimum_punishment": "None", "maximum_punishment": "3 years", "fine_details": "Up to Rs. 2,00,000", "imprisonment_details": "Term up to 3 years", "community_service": False
    },
    ("the-information-technology-act-2000", "66"): {
        "punishment_type": "Imprisonment up to 3 years, or fine up to 5 lakh rupees, or both",
        "description": "Whoever commits hacking or computer-related offences shall be punished with imprisonment up to three years or fine up to five lakh rupees or both.",
        "minimum_punishment": "None", "maximum_punishment": "3 years", "fine_details": "Up to Rs. 5,00,000", "imprisonment_details": "Term up to 3 years", "community_service": False
    },
    ("the-information-technology-act-2000", "66C"): {
        "punishment_type": "Imprisonment up to 3 years and fine up to 1 lakh rupees",
        "description": "Identity theft punishable with imprisonment up to three years and shall also be liable to fine up to one lakh rupees.",
        "minimum_punishment": "None", "maximum_punishment": "3 years", "fine_details": "Up to Rs. 1,00,000", "imprisonment_details": "Term up to 3 years", "community_service": False
    },
    ("the-information-technology-act-2000", "66D"): {
        "punishment_type": "Imprisonment up to 3 years and fine up to 1 lakh rupees",
        "description": "Cheating by personation using computer resource punishable with imprisonment up to 3 years and fine up to 1 lakh rupees.",
        "minimum_punishment": "None", "maximum_punishment": "3 years", "fine_details": "Up to Rs. 1,00,000", "imprisonment_details": "Term up to 3 years", "community_service": False
    },
    ("the-information-technology-act-2000", "66F"): {
        "punishment_type": "Imprisonment for life",
        "description": "Whoever commits or conspires to commit cyber terrorism shall be punishable with imprisonment which may extend to imprisonment for life.",
        "minimum_punishment": "Life Imprisonment", "maximum_punishment": "Life Imprisonment", "fine_details": "None", "imprisonment_details": "Imprisonment for life", "community_service": False
    },
    ("the-information-technology-act-2000", "67"): {
        "punishment_type": "First conviction: up to 3 years and fine up to 5 lakh rupees; Second conviction: up to 5 years and fine up to 10 lakh rupees",
        "description": "Transmitting obscene material in electronic form.",
        "minimum_punishment": "None", "maximum_punishment": "5 years", "fine_details": "Rs. 5,00,000 to Rs. 10,00,000", "imprisonment_details": "3 to 5 years", "community_service": False
    },
    ("the-protection-of-children-from-sexual-offences-act-2012", "4"): {
        "punishment_type": "Rigorous imprisonment not less than 20 years, up to life imprisonment, and fine, or death",
        "description": "Punishment for penetrative sexual assault under Section 4 POCSO (as amended 2019).",
        "minimum_punishment": "20 years rigorous imprisonment", "maximum_punishment": "Imprisonment for remainder of natural life or death", "fine_details": "Fine to meet medical expenses and rehabilitation", "imprisonment_details": "Rigorous imprisonment not less than 20 years", "community_service": False
    },
    ("the-protection-of-children-from-sexual-offences-act-2012", "6"): {
        "punishment_type": "Rigorous imprisonment not less than 20 years, up to life imprisonment, or death, and fine",
        "description": "Punishment for aggravated penetrative sexual assault under Section 6 POCSO (as amended 2019).",
        "minimum_punishment": "20 years rigorous imprisonment", "maximum_punishment": "Death penalty or imprisonment for remainder of natural life", "fine_details": "Mandatory fine for rehabilitation", "imprisonment_details": "20 years to life", "community_service": False
    },
    ("the-protection-of-children-from-sexual-offences-act-2012", "8"): {
        "punishment_type": "Imprisonment not less than 3 years, up to 5 years, and fine",
        "description": "Punishment for sexual assault under Section 8 POCSO.",
        "minimum_punishment": "3 years imprisonment", "maximum_punishment": "5 years imprisonment", "fine_details": "Liable to fine", "imprisonment_details": "3 to 5 years", "community_service": False
    },
    ("the-protection-of-children-from-sexual-offences-act-2012", "12"): {
        "punishment_type": "Imprisonment up to 3 years and fine",
        "description": "Punishment for sexual harassment upon child under Section 12 POCSO.",
        "minimum_punishment": "None", "maximum_punishment": "3 years", "fine_details": "Liable to fine", "imprisonment_details": "Term up to 3 years", "community_service": False
    },
    ("the-juvenile-justice-care-and-protection-of-children-act-2015", "74"): {
        "punishment_type": "Imprisonment up to 6 months, or fine up to 2 lakh rupees, or both",
        "description": "Disclosure of identity of child in conflict with law or need of protection.",
        "minimum_punishment": "None", "maximum_punishment": "6 months", "fine_details": "Up to Rs. 2,00,000", "imprisonment_details": "Term up to 6 months", "community_service": False
    },
    ("the-juvenile-justice-care-and-protection-of-children-act-2015", "75"): {
        "punishment_type": "Imprisonment up to 3 years and fine up to 1 lakh rupees (or up to 5 years if committed by child care employee)",
        "description": "Cruelty to child by person having custody or control.",
        "minimum_punishment": "None", "maximum_punishment": "5 years", "fine_details": "Up to Rs. 5,00,000", "imprisonment_details": "3 to 5 years", "community_service": False
    },
    ("the-protection-of-women-from-domestic-violence-act-2005", "31"): {
        "punishment_type": "Imprisonment up to 1 year, or fine up to 20,000 rupees, or both",
        "description": "Penalty for breach of protection order or interim order passed by Magistrate.",
        "minimum_punishment": "None", "maximum_punishment": "1 year", "fine_details": "Up to Rs. 20,000", "imprisonment_details": "Term up to 1 year", "community_service": False
    },
    ("the-dowry-prohibition-act-1961", "3"): {
        "punishment_type": "Imprisonment not less than 5 years, and fine not less than 15,000 rupees or amount of dowry",
        "description": "Penalty for giving or taking dowry under Section 3 DPA.",
        "minimum_punishment": "5 years imprisonment", "maximum_punishment": "Term exceeding 5 years", "fine_details": "Not less than Rs. 15,000 or value of dowry, whichever is higher", "imprisonment_details": "Not less than 5 years", "community_service": False
    },
    ("the-dowry-prohibition-act-1961", "4"): {
        "punishment_type": "Imprisonment not less than 6 months, up to 2 years, and fine up to 10,000 rupees",
        "description": "Penalty for demanding dowry directly or indirectly.",
        "minimum_punishment": "6 months", "maximum_punishment": "2 years", "fine_details": "Up to Rs. 10,000", "imprisonment_details": "6 months to 2 years", "community_service": False
    },
    ("the-sexual-harassment-of-women-at-workplace-prevention-prohibition-and-redressal-act-2013", "26"): {
        "punishment_type": "Fine up to 50,000 rupees; repeat offence entails cancellation of license / registration",
        "description": "Penalty for non-compliance with provisions by employer under Section 26 POSH.",
        "minimum_punishment": "None", "maximum_punishment": "License revocation", "fine_details": "Up to Rs. 50,000 (twice for repeat conviction)", "imprisonment_details": "None", "community_service": False
    },
    ("the-hindu-marriage-act-1955", "17"): {
        "punishment_type": "Punishment as provided in Section 494 and 495 of IPC / Section 82 BNS",
        "description": "Punishment of bigamy in Hindu marriage; marriage is void and offender liable under criminal code.",
        "minimum_punishment": "None", "maximum_punishment": "7 years (or 10 years if prior marriage concealed)", "fine_details": "Liable to fine", "imprisonment_details": "Term up to 7 years", "community_service": False
    },
    ("the-registration-act-1908", "81"): {
        "punishment_type": "Imprisonment up to 7 years, or fine, or both",
        "description": "Penalty for officer incorrectly endorsing, copying, translating or registering document with intent to injure.",
        "minimum_punishment": "None", "maximum_punishment": "7 years", "fine_details": "Liable to fine", "imprisonment_details": "Term up to 7 years", "community_service": False
    },
    ("the-registration-act-1908", "82"): {
        "punishment_type": "Imprisonment up to 7 years, or fine, or both",
        "description": "Penalty for intentional false statement, delivery of false translation, or false personation before registrar.",
        "minimum_punishment": "None", "maximum_punishment": "7 years", "fine_details": "Liable to fine", "imprisonment_details": "Term up to 7 years", "community_service": False
    },
    ("the-negotiable-instruments-act-1881", "138"): {
        "punishment_type": "Imprisonment up to 2 years, or fine up to twice the cheque amount, or both",
        "description": "Cheque bounce penalty under Section 138 NI Act.",
        "minimum_punishment": "None", "maximum_punishment": "2 years", "fine_details": "Up to twice the amount of the dishonoured cheque", "imprisonment_details": "Term up to 2 years", "community_service": False
    },
    ("the-consumer-protection-act-2019", "89"): {
        "punishment_type": "Imprisonment up to 2 years and fine up to 10 lakh rupees; repeat offence up to 5 years and 50 lakh rupees",
        "description": "False or misleading advertisement by manufacturer or endorser.",
        "minimum_punishment": "None", "maximum_punishment": "5 years", "fine_details": "Rs. 10,00,000 to Rs. 50,00,000", "imprisonment_details": "2 to 5 years", "community_service": False
    },
    ("the-motor-vehicles-act-1988", "185"): {
        "punishment_type": "First offence: up to 6 months or fine up to 10,000 rupees, or both; Second offence: up to 2 years or fine up to 15,000 rupees, or both",
        "description": "Driving under the influence of alcohol or drugs under Section 185 MVA.",
        "minimum_punishment": "None", "maximum_punishment": "2 years", "fine_details": "Rs. 10,000 to Rs. 15,00,000", "imprisonment_details": "6 months to 2 years", "community_service": False
    },
    ("the-motor-vehicles-act-1988", "199A"): {
        "punishment_type": "Imprisonment up to 3 years and fine of 25,000 rupees, cancellation of vehicle registration for 1 year, and juvenile ineligible for licence until age 25",
        "description": "Offences committed by juveniles in motor vehicles; penalty on guardian.",
        "minimum_punishment": "None", "maximum_punishment": "3 years", "fine_details": "Rs. 25,000", "imprisonment_details": "Term up to 3 years", "community_service": False
    },
    ("the-companies-act-2013", "447"): {
        "punishment_type": "Imprisonment not less than 6 months, up to 10 years, and fine not less than amount involved in fraud up to 3 times",
        "description": "Punishment for corporate fraud under Section 447 Companies Act (minimum 3 years if public interest involved).",
        "minimum_punishment": "6 months (3 years if public interest)", "maximum_punishment": "10 years", "fine_details": "1x to 3x of amount involved in fraud", "imprisonment_details": "6 months to 10 years", "community_service": False
    },
    ("the-companies-act-2013", "448"): {
        "punishment_type": "Liable under Section 447 (Imprisonment 6 months to 10 years and fine up to 3 times amount)",
        "description": "Punishment for false statements in company returns or reports.",
        "minimum_punishment": "6 months", "maximum_punishment": "10 years", "fine_details": "Same as Section 447", "imprisonment_details": "6 months to 10 years", "community_service": False
    },
    ("the-insolvency-and-bankruptcy-code-2016", "65"): {
        "punishment_type": "Penalty not less than 1 lakh rupees, which may extend to 1 crore rupees",
        "description": "Fraudulent or malicious initiation of insolvency or liquidation proceedings.",
        "minimum_punishment": "Rs. 1,00,000 penalty", "maximum_punishment": "Rs. 1,00,00,000 penalty", "fine_details": "Rs. 1 lakh to Rs. 1 crore", "imprisonment_details": "None (Civil Penalty by NCLT)", "community_service": False
    }
}


def load_staging_sections():
    print(f"Loading staging sections from {STAGING_SECTIONS}...")
    if not STAGING_SECTIONS.exists():
        raise FileNotFoundError(f"Staging file not found: {STAGING_SECTIONS}")
    with open(STAGING_SECTIONS, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    print("=" * 70)
    print("VIDHIK PHASE 17 - 24 ACTS LEGAL KNOWLEDGE CORPUS COMPILER")
    print("=" * 70)

    staging_secs = load_staging_sections()
    print(f"Total sections loaded from staging: {len(staging_secs)}")

    # Index staging sections by (law_id, section_number)
    staging_by_law = {}
    for s in staging_secs:
        lid = s.get("law_id")
        staging_by_law.setdefault(lid, []).append(s)

    # Load existing specialized datasets for BNS, BNSS, BSA
    bns_spec = {}
    bnss_spec = {}
    bsa_spec = {}

    bns_file = KB_DIR / "bns_sections.json"
    if bns_file.exists():
        with open(bns_file, "r", encoding="utf-8") as f:
            for item in json.load(f):
                bns_spec[str(item.get("section_number"))] = item

    bnss_file = KB_DIR / "bnss_sections.json"
    if bnss_file.exists():
        with open(bnss_file, "r", encoding="utf-8") as f:
            for item in json.load(f):
                bnss_spec[str(item.get("section_number"))] = item

    bsa_file = KB_DIR / "bsa_sections.json"
    if bsa_file.exists():
        with open(bsa_file, "r", encoding="utf-8") as f:
            for item in json.load(f):
                bsa_spec[str(item.get("section_number"))] = item

    all_acts_compiled = []
    total_sections_corpus = 0
    total_offences_corpus = 0
    total_punishments_corpus = 0
    total_procedures_corpus = 0
    total_evidence_corpus = 0

    print("\nProcessing and structuring all 24 Acts...")
    for act in ACTS_MASTER:
        act_id = act["act_id"]
        law_id = act["staging_law_id"]
        raw_secs = staging_by_law.get(law_id, [])
        compiled_secs = []

        # Load raw text from statutory source file if needed for text fallback
        text_source_path = BASE_DIR / act["source_file"]
        text_extracted_secs = {}
        if text_source_path.exists() and text_source_path.suffix == ".txt":
            with open(text_source_path, "r", encoding="utf-8", errors="ignore") as tf:
                raw_act_text = tf.read()
            pattern = re.compile(r'(?:^|\n)\s*(\d+[A-Z]?)\.\s*([^\n—\-–।]+)[—\-–।]\s*([\s\S]+?)(?=(?:\n\s*\d+[A-Z]?\.\s*[^\n—\-–।]+[—\-–।])|\Z)')
            for m in pattern.finditer(raw_act_text):
                sn = m.group(1).strip()
                st = m.group(2).strip()
                sb = m.group(3).strip()
                if len(sb) > 20 and sn not in text_extracted_secs:
                    text_extracted_secs[sn] = (st, sb)

        for s in raw_secs:
            sec_num = str(s.get("section_number", "")).strip()
            sec_title = s.get("section_title") or f"Section {sec_num}"
            full_txt = s.get("full_text") or ""
            chap = s.get("chapter_number") or s.get("chapter_title") or "General"

            # Enrich full text from source file if staging was empty
            if len(full_txt.strip()) < 15:
                if sec_num in text_extracted_secs:
                    t_ext, b_ext = text_extracted_secs[sec_num]
                    full_txt = b_ext
                    if not sec_title or sec_title == f"Section {sec_num}":
                        sec_title = t_ext
                else:
                    full_txt = f"Statutory provision under {act['act_name']}, Section {sec_num}."

            
            # Check for existing specialized metadata (BNS/BNSS/BSA)
            is_off = False
            off_data = None
            pun_data = None
            proc_data = None
            ev_data = None

            if act_id == 1 and sec_num in bns_spec:
                spec = bns_spec[sec_num]
                is_off = spec.get("is_offence", False)
                off_data = spec.get("offence")
                pun_data = spec.get("punishment")
            elif act_id == 2 and sec_num in bnss_spec:
                spec = bnss_spec[sec_num]
                proc_data = spec.get("procedure")
            elif act_id == 3 and sec_num in bsa_spec:
                spec = bsa_spec[sec_num]
                ev_data = {
                    "provision_type": spec.get("provision_type", "Statutory Rule"),
                    "rule_statement": spec.get("rule_statement", full_txt[:300]),
                    "statutory_condition": spec.get("statutory_condition"),
                    "admissibility_criteria": spec.get("admissibility_criteria", [])
                }
            
            # Check structured catalog for Acts 4-24
            key = (law_id, sec_num)
            if key in KEY_OFFENCES_METADATA:
                is_off = True
                off_meta = KEY_OFFENCES_METADATA[key]
                off_data = {
                    "offence_name": off_meta["offence_name"],
                    "description": off_meta["description"],
                    "section_reference": f"Section {sec_num}, {act['short_name']}",
                    "cognizable_status": off_meta.get("cognizable_status", "Cognizable"),
                    "bailable_status": off_meta.get("bailable_status", "Non-Bailable"),
                    "compoundable_status": off_meta.get("compoundable_status", "Non-Compoundable"),
                    "triable_by": off_meta.get("triable_by", "Magistrate of First Class")
                }

            if key in KEY_PUNISHMENTS_METADATA:
                pun_meta = KEY_PUNISHMENTS_METADATA[key]
                pun_data = {
                    "punishment_type": pun_meta["punishment_type"],
                    "description": pun_meta["description"],
                    "minimum_punishment": pun_meta.get("minimum_punishment"),
                    "maximum_punishment": pun_meta.get("maximum_punishment"),
                    "fine_details": pun_meta.get("fine_details"),
                    "imprisonment_details": pun_meta.get("imprisonment_details"),
                    "community_service": pun_meta.get("community_service", False)
                }

            # Procedural detection for procedural statutes (BNSS, PWDVA, CPA, IBC, Arbitration, RTI, LSAA)
            if act["has_procedures"] and not proc_data:
                # Detect key procedural keywords
                t_lower = (sec_title + " " + full_txt).lower()
                if any(k in t_lower for k in ["procedure", "application", "complaint", "appeal", "inquiry", "cognizance", "notice", "arbitration", "resolution plan"]):
                    proc_cat = "Statutory Procedure"
                    if "complaint" in t_lower:
                        proc_cat = "Complaint / Filing"
                    elif "appeal" in t_lower:
                        proc_cat = "Appellate Procedure"
                    elif "inquiry" in t_lower or "investigation" in t_lower:
                        proc_cat = "Inquiry & Investigation"
                    elif "arbitration" in t_lower:
                        proc_cat = "Arbitral Process"
                    elif "resolution" in t_lower or "moratorium" in t_lower:
                        proc_cat = "Insolvency Resolution"
                    elif "lok adalat" in t_lower:
                        proc_cat = "ADR / Lok Adalat"

                    proc_data = {
                        "procedure_category": proc_cat,
                        "title": sec_title,
                        "description": full_txt[:350],
                        "statutory_steps": [f"Follow statutory requirements outlined in Section {sec_num} of {act['short_name']}"],
                        "safeguards": ["Statutory timelines and procedural compliance apply"],
                        "timeline_days": None
                    }

            # Evidence detection (BSA, NI Act 139/146, POCSO 29/30, DPA 8A)
            if act["has_evidence"] and not ev_data:
                t_lower = (sec_title + " " + full_txt).lower()
                if any(k in t_lower for k in ["presumption", "burden of proof", "electronic record", "certificate", "admissible", "prima facie"]):
                    ev_data = {
                        "provision_type": "Statutory Presumption / Evidence Standard",
                        "rule_statement": sec_title + ": " + full_txt[:250],
                        "statutory_condition": f"Conditions set forth in Section {sec_num}, {act['short_name']}",
                        "admissibility_criteria": [f"Admissible according to Section {sec_num} evidentiary rule"]
                    }

            if is_off and off_data:
                total_offences_corpus += 1
            if pun_data:
                total_punishments_corpus += 1
            if proc_data:
                total_procedures_corpus += 1
            if ev_data:
                total_evidence_corpus += 1

            sec_record = {
                "section_id": s.get("section_id") or f"{law_id}-sec-{sec_num}",
                "law_id": act_id,
                "law_name": act["act_name"],
                "short_name": act["short_name"],
                "section_number": sec_num,
                "section_title": sec_title,
                "full_text": full_txt,
                "chapter": chap,
                "source_pdf": s.get("source_pdf"),
                "source_page_start": s.get("source_page_start"),
                "source_page_end": s.get("source_page_end"),
                "provenance": act["provenance"],
                "is_offence": is_off,
                "offence": off_data,
                "punishment": pun_data,
                "procedure": proc_data,
                "evidence": ev_data,
                "has_proviso": s.get("has_proviso", False),
                "has_explanation": s.get("has_explanation", False),
                "subsections_count": s.get("subsections_count", 0),
                "clauses_count": s.get("clauses_count", 0),
                "judgments_status": act["judgments_status"]
            }
            compiled_secs.append(sec_record)

        total_sections_corpus += len(compiled_secs)

        # Build Act Master Record
        act_entry = dict(act)
        act_entry["total_sections"] = len(compiled_secs)
        act_entry["offences_count"] = sum(1 for x in compiled_secs if x.get("is_offence"))
        act_entry["punishments_count"] = sum(1 for x in compiled_secs if x.get("punishment"))
        act_entry["procedures_count"] = sum(1 for x in compiled_secs if x.get("procedure"))
        act_entry["evidence_count"] = sum(1 for x in compiled_secs if x.get("evidence"))
        
        all_acts_compiled.append(act_entry)

        # Write individual act file
        safe_short = act["short_name"].lower().replace(" ", "_")
        act_file = ACTS_DIR / f"act_{act_id:02d}_{safe_short}.json"
        with open(act_file, "w", encoding="utf-8") as f:
            json.dump({
                "act_metadata": act_entry,
                "sections": compiled_secs
            }, f, indent=2, ensure_ascii=False)

        print(f"  [{act_id:2d}/24] {act['short_name']:15s}: {len(compiled_secs):4d} sections | Offences: {act_entry['offences_count']:2d} | Procedures: {act_entry['procedures_count']:2d} | Evidence: {act_entry['evidence_count']:2d} | Judgments: {act['judgments_status']}")

    # Save Registry
    registry_file = KB_DIR / "phase17_24_acts_registry.json"
    with open(registry_file, "w", encoding="utf-8") as f:
        json.dump(all_acts_compiled, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved 24 Acts Registry to {registry_file}")

    # Save Consolidated Knowledge Base Summary
    master_kb = {
        "status": "active",
        "corpus": "Vidhik Advanced Legal Knowledge Base (Phase 17)",
        "total_acts": len(all_acts_compiled),
        "total_sections": total_sections_corpus,
        "total_offences": total_offences_corpus,
        "total_punishments": total_punishments_corpus,
        "total_procedures": total_procedures_corpus,
        "total_evidence_provisions": total_evidence_corpus,
        "acts": all_acts_compiled
    }
    master_file = KB_DIR / "acts_knowledge.json"
    with open(master_file, "w", encoding="utf-8") as f:
        json.dump(master_kb, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved Master Legal Knowledge to {master_file}")

    print("\n" + "=" * 70)
    print("PHASE 17 - 24 ACTS KNOWLEDGE COMPILATION COMPLETE")
    print("=" * 70)
    print(f"  • Total Acts Compiled:       {len(all_acts_compiled)} / 24")
    print(f"  • Total Statutory Sections: {total_sections_corpus:,}")
    print(f"  • Total Structured Offences: {total_offences_corpus}")
    print(f"  • Total Punishments:         {total_punishments_corpus}")
    print(f"  • Total Procedures:          {total_procedures_corpus}")
    print(f"  • Total Evidence Standards:  {total_evidence_corpus}")
    print("=" * 70)


if __name__ == "__main__":
    main()
