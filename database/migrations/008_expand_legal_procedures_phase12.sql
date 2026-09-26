-- ====================================================================
-- VIDHIK LEGAL PLATFORM - PHASE 12: DOCUMENTATION SUPPORT EXPANSION
-- Schema Migration 008: Expansion to 25 Legal Procedures & Checklists
-- ====================================================================
-- Expands legal procedures from 8 to 25 authoritative procedures.
-- Preserves existing procedures 1-8 completely intact.
-- Grounded in Indian statutory enactments and Maharashtra-specific
-- authorities, portals, and citizen charters.
-- Fully relational, idempotent, and non-destructive.
-- ====================================================================

BEGIN;

-- ====================================================================
-- 1. SEED PROCEDURES 9 TO 25
-- ====================================================================

-- 9. MARRIAGE REGISTRATION
INSERT INTO legal_procedures (
    procedure_id, procedure_name, procedure_slug, category, description,
    governing_law_id, governing_section_id, jurisdiction, authority_type,
    estimated_processing_days, official_portal_url
) VALUES (
    9,
    'Registration of Marriage (Special & Hindu Marriage Acts)',
    'marriage-registration',
    'Family / Personal',
    'Statutory registration of solemnized or intended marriage under the Special Marriage Act, 1954 or Hindu Marriage Act, 1955 before the Marriage Officer or Sub-Registrar.',
    754, 33824, 'Central / Maharashtra State', 'Marriage Officer / Sub-Registrar of Assurances / Municipal Ward Office',
    15, 'https://igrmaharashtra.gov.in'
) ON CONFLICT (procedure_slug) DO UPDATE SET
    procedure_name = EXCLUDED.procedure_name,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    governing_law_id = EXCLUDED.governing_law_id,
    governing_section_id = EXCLUDED.governing_section_id,
    jurisdiction = EXCLUDED.jurisdiction,
    authority_type = EXCLUDED.authority_type,
    estimated_processing_days = EXCLUDED.estimated_processing_days,
    official_portal_url = EXCLUDED.official_portal_url;

-- 10. BIRTH CERTIFICATE REGISTRATION AND CORRECTION
INSERT INTO legal_procedures (
    procedure_id, procedure_name, procedure_slug, category, description,
    governing_law_id, governing_section_id, jurisdiction, authority_type,
    estimated_processing_days, official_portal_url
) VALUES (
    10,
    'Birth Certificate Registration and Correction',
    'birth-certificate-registration-correction',
    'Certificates / Registrations',
    'Statutory registration of birth within 21 days, delayed registration under Section 13, and clerical name addition/correction in the Register of Births under the Registration of Births and Deaths Act, 1969.',
    681, 31463, 'Central / Maharashtra State', 'Registrar of Births and Deaths (Municipal Corporation / Gram Panchayat / Health Dept)',
    21, 'https://crsorgi.gov.in'
) ON CONFLICT (procedure_slug) DO UPDATE SET
    procedure_name = EXCLUDED.procedure_name,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    governing_law_id = EXCLUDED.governing_law_id,
    governing_section_id = EXCLUDED.governing_section_id,
    jurisdiction = EXCLUDED.jurisdiction,
    authority_type = EXCLUDED.authority_type,
    estimated_processing_days = EXCLUDED.estimated_processing_days,
    official_portal_url = EXCLUDED.official_portal_url;

-- 11. DEATH CERTIFICATE REGISTRATION AND CORRECTION
INSERT INTO legal_procedures (
    procedure_id, procedure_name, procedure_slug, category, description,
    governing_law_id, governing_section_id, jurisdiction, authority_type,
    estimated_processing_days, official_portal_url
) VALUES (
    11,
    'Death Certificate Registration and Correction',
    'death-certificate-registration-correction',
    'Certificates / Registrations',
    'Mandatory reporting of death within 21 days, delayed registration upon Magistrate order, and clerical correction in the Register of Deaths pursuant to the Registration of Births and Deaths Act, 1969.',
    681, 31467, 'Central / Maharashtra State', 'Registrar of Births and Deaths (Municipal Corporation / Municipal Council / Gram Panchayat)',
    21, 'https://crsorgi.gov.in'
) ON CONFLICT (procedure_slug) DO UPDATE SET
    procedure_name = EXCLUDED.procedure_name,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    governing_law_id = EXCLUDED.governing_law_id,
    governing_section_id = EXCLUDED.governing_section_id,
    jurisdiction = EXCLUDED.jurisdiction,
    authority_type = EXCLUDED.authority_type,
    estimated_processing_days = EXCLUDED.estimated_processing_days,
    official_portal_url = EXCLUDED.official_portal_url;

-- 12. NAME CHANGE AND OFFICIAL GAZETTE PUBLICATION
INSERT INTO legal_procedures (
    procedure_id, procedure_name, procedure_slug, category, description,
    governing_law_id, governing_section_id, jurisdiction, authority_type,
    estimated_processing_days, official_portal_url
) VALUES (
    12,
    'Name Change and Official Gazette Publication',
    'name-change-gazette-publication',
    'Certificates / Registrations',
    'Formal legal procedure for changing or correcting a citizen''s name through sworn affidavit, newspaper announcement, and statutory notification in the Official Government Gazette.',
    NULL, NULL, 'Central / Maharashtra State', 'Directorate of Government Printing, Stationery and Publications (Maharashtra / Central Gazette)',
    30, 'https://dgps.maharashtra.gov.in'
) ON CONFLICT (procedure_slug) DO UPDATE SET
    procedure_name = EXCLUDED.procedure_name,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    governing_law_id = EXCLUDED.governing_law_id,
    governing_section_id = EXCLUDED.governing_section_id,
    jurisdiction = EXCLUDED.jurisdiction,
    authority_type = EXCLUDED.authority_type,
    estimated_processing_days = EXCLUDED.estimated_processing_days,
    official_portal_url = EXCLUDED.official_portal_url;

-- 13. DOMICILE & NATIONALITY CERTIFICATE
INSERT INTO legal_procedures (
    procedure_id, procedure_name, procedure_slug, category, description,
    governing_law_id, governing_section_id, jurisdiction, authority_type,
    estimated_processing_days, official_portal_url
) VALUES (
    13,
    'Application for Domicile and Nationality Certificate',
    'domicile-certificate-application',
    'Certificates / Registrations',
    'Statutory application to the Revenue Department establishing 15+ years continuous residency in Maharashtra and Indian nationality under Aaple Sarkar citizen services.',
    1331, 7252, 'Maharashtra', 'Sub-Divisional Officer (SDO) / Tahsildar (Revenue Department)',
    15, 'https://aaplesarkar.mahaonline.gov.in'
) ON CONFLICT (procedure_slug) DO UPDATE SET
    procedure_name = EXCLUDED.procedure_name,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    governing_law_id = EXCLUDED.governing_law_id,
    governing_section_id = EXCLUDED.governing_section_id,
    jurisdiction = EXCLUDED.jurisdiction,
    authority_type = EXCLUDED.authority_type,
    estimated_processing_days = EXCLUDED.estimated_processing_days,
    official_portal_url = EXCLUDED.official_portal_url;

-- 14. INCOME CERTIFICATE
INSERT INTO legal_procedures (
    procedure_id, procedure_name, procedure_slug, category, description,
    governing_law_id, governing_section_id, jurisdiction, authority_type,
    estimated_processing_days, official_portal_url
) VALUES (
    14,
    'Application for Income Certificate',
    'income-certificate-application',
    'Certificates / Registrations',
    'Statutory certification of annual household income for educational scholarships, government welfare schemes, fee concessions, and EWS reservations under Maharashtra Right to Public Services.',
    NULL, NULL, 'Maharashtra', 'Tahsildar / Nayab Tahsildar (Revenue Department)',
    15, 'https://aaplesarkar.mahaonline.gov.in'
) ON CONFLICT (procedure_slug) DO UPDATE SET
    procedure_name = EXCLUDED.procedure_name,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    governing_law_id = EXCLUDED.governing_law_id,
    governing_section_id = EXCLUDED.governing_section_id,
    jurisdiction = EXCLUDED.jurisdiction,
    authority_type = EXCLUDED.authority_type,
    estimated_processing_days = EXCLUDED.estimated_processing_days,
    official_portal_url = EXCLUDED.official_portal_url;

-- 15. CASTE CERTIFICATE & SCRUTINY VERIFICATION
INSERT INTO legal_procedures (
    procedure_id, procedure_name, procedure_slug, category, description,
    governing_law_id, governing_section_id, jurisdiction, authority_type,
    estimated_processing_days, official_portal_url
) VALUES (
    15,
    'Caste Certificate Issuance and Scrutiny Verification',
    'caste-certificate-verification',
    'Certificates / Registrations',
    'Statutory grant of SC/ST/VJNT/OBC/SBC caste certificate by the Sub-Divisional Officer and validation by the Divisional Caste Scrutiny Committee under Maharashtra Act XXIII of 2001.',
    NULL, NULL, 'Maharashtra', 'Sub-Divisional Officer (SDO) & Divisional Caste Scrutiny Committee',
    45, 'https://castecertificate.maharashtra.gov.in'
) ON CONFLICT (procedure_slug) DO UPDATE SET
    procedure_name = EXCLUDED.procedure_name,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    governing_law_id = EXCLUDED.governing_law_id,
    governing_section_id = EXCLUDED.governing_section_id,
    jurisdiction = EXCLUDED.jurisdiction,
    authority_type = EXCLUDED.authority_type,
    estimated_processing_days = EXCLUDED.estimated_processing_days,
    official_portal_url = EXCLUDED.official_portal_url;

-- 16. LEGAL HEIR / SURVIVING MEMBER CERTIFICATE
INSERT INTO legal_procedures (
    procedure_id, procedure_name, procedure_slug, category, description,
    governing_law_id, governing_section_id, jurisdiction, authority_type,
    estimated_processing_days, official_portal_url
) VALUES (
    16,
    'Legal Heir / Surviving Member Certificate',
    'legal-heir-surviving-member-certificate',
    'Certificates / Registrations',
    'Administrative inquiry and issuance of Surviving Member Certificate by the Revenue Tehsildar / SDM for settlement of gratuity, provident fund, family pension, and utility meter transfers.',
    362, 17292, 'Central / Maharashtra State', 'Tahsildar / Sub-Divisional Magistrate (Revenue Department)',
    30, 'https://aaplesarkar.mahaonline.gov.in'
) ON CONFLICT (procedure_slug) DO UPDATE SET
    procedure_name = EXCLUDED.procedure_name,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    governing_law_id = EXCLUDED.governing_law_id,
    governing_section_id = EXCLUDED.governing_section_id,
    jurisdiction = EXCLUDED.jurisdiction,
    authority_type = EXCLUDED.authority_type,
    estimated_processing_days = EXCLUDED.estimated_processing_days,
    official_portal_url = EXCLUDED.official_portal_url;

-- 17. PROPERTY ENCUMBRANCE CERTIFICATE & TITLE SEARCH
INSERT INTO legal_procedures (
    procedure_id, procedure_name, procedure_slug, category, description,
    governing_law_id, governing_section_id, jurisdiction, authority_type,
    estimated_processing_days, official_portal_url
) VALUES (
    17,
    'Property Encumbrance Certificate (EC) & Title Search',
    'property-encumbrance-certificate-search',
    'Property',
    'Statutory search of Book 1 and Index II registers and issuance of Encumbrance Certificate (Form 15/16) or certified copies of registered deeds under Section 57 of the Registration Act, 1908.',
    680, 31407, 'Central / Maharashtra State', 'Sub-Registrar of Assurances / Inspector General of Registration (IGR Maharashtra)',
    7, 'https://igrmaharashtra.gov.in'
) ON CONFLICT (procedure_slug) DO UPDATE SET
    procedure_name = EXCLUDED.procedure_name,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    governing_law_id = EXCLUDED.governing_law_id,
    governing_section_id = EXCLUDED.governing_section_id,
    jurisdiction = EXCLUDED.jurisdiction,
    authority_type = EXCLUDED.authority_type,
    estimated_processing_days = EXCLUDED.estimated_processing_days,
    official_portal_url = EXCLUDED.official_portal_url;

-- 18. BANKING OMBUDSMAN / RBI GRIEVANCE REDRESSAL
INSERT INTO legal_procedures (
    procedure_id, procedure_name, procedure_slug, category, description,
    governing_law_id, governing_section_id, jurisdiction, authority_type,
    estimated_processing_days, official_portal_url
) VALUES (
    18,
    'Banking Ombudsman / RBI Grievance Redressal',
    'banking-ombudsman-rbi-complaint',
    'Consumer / Commercial',
    'Escalation of unresolved banking grievances, unauthorized electronic fund deductions, or service deficiencies under the Reserve Bank - Integrated Ombudsman Scheme, 2021.',
    1243, 3035, 'Central / National', 'Banking Ombudsman / Reserve Bank of India (CMS Portal)',
    30, 'https://cms.rbi.org.in'
) ON CONFLICT (procedure_slug) DO UPDATE SET
    procedure_name = EXCLUDED.procedure_name,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    governing_law_id = EXCLUDED.governing_law_id,
    governing_section_id = EXCLUDED.governing_section_id,
    jurisdiction = EXCLUDED.jurisdiction,
    authority_type = EXCLUDED.authority_type,
    estimated_processing_days = EXCLUDED.estimated_processing_days,
    official_portal_url = EXCLUDED.official_portal_url;

-- 19. INSURANCE OMBUDSMAN COMPLAINT FILING
INSERT INTO legal_procedures (
    procedure_id, procedure_name, procedure_slug, category, description,
    governing_law_id, governing_section_id, jurisdiction, authority_type,
    estimated_processing_days, official_portal_url
) VALUES (
    19,
    'Insurance Ombudsman Complaint Filing',
    'insurance-ombudsman-complaint',
    'Consumer / Commercial',
    'Statutory dispute redressal for policyholders against unfair repudiation of claim, partial settlement, or delay in claim settlement under the Insurance Ombudsman Rules, 2017.',
    389, NULL, 'Central / National', 'Insurance Ombudsman / Council for Insurance Ombudsmen (CIO)',
    90, 'https://www.cioins.co.in'
) ON CONFLICT (procedure_slug) DO UPDATE SET
    procedure_name = EXCLUDED.procedure_name,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    governing_law_id = EXCLUDED.governing_law_id,
    governing_section_id = EXCLUDED.governing_section_id,
    jurisdiction = EXCLUDED.jurisdiction,
    authority_type = EXCLUDED.authority_type,
    estimated_processing_days = EXCLUDED.estimated_processing_days,
    official_portal_url = EXCLUDED.official_portal_url;

-- 20. EMPLOYEES' PROVIDENT FUND (EPFO / PF) SETTLEMENT CLAIM
INSERT INTO legal_procedures (
    procedure_id, procedure_name, procedure_slug, category, description,
    governing_law_id, governing_section_id, jurisdiction, authority_type,
    estimated_processing_days, official_portal_url
) VALUES (
    20,
    'Employees'' Provident Fund (EPFO / PF) Settlement Claim',
    'epfo-pf-settlement-claim',
    'Employment / Social',
    'Online or physical claim submission for final provident fund withdrawal (Form 19), pension benefit (Form 10C), or non-refundable advances (Form 31) under the EPF Scheme.',
    1347, 8170, 'Central / National', 'Employees'' Provident Fund Organisation (EPFO), Ministry of Labour and Employment',
    20, 'https://unifiedportal-mem.epfindia.gov.in'
) ON CONFLICT (procedure_slug) DO UPDATE SET
    procedure_name = EXCLUDED.procedure_name,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    governing_law_id = EXCLUDED.governing_law_id,
    governing_section_id = EXCLUDED.governing_section_id,
    jurisdiction = EXCLUDED.jurisdiction,
    authority_type = EXCLUDED.authority_type,
    estimated_processing_days = EXCLUDED.estimated_processing_days,
    official_portal_url = EXCLUDED.official_portal_url;

-- 21. PAYMENT OF GRATUITY CLAIM & DISPUTE APPLICATION
INSERT INTO legal_procedures (
    procedure_id, procedure_name, procedure_slug, category, description,
    governing_law_id, governing_section_id, jurisdiction, authority_type,
    estimated_processing_days, official_portal_url
) VALUES (
    21,
    'Payment of Gratuity Claim and Controlling Authority Application',
    'payment-of-gratuity-claim',
    'Employment / Social',
    'Statutory application in Form ''I'' to the employer or Form ''N'' before the Controlling Authority seeking determination and payment of earned gratuity under the Payment of Gratuity Act, 1972.',
    1347, 8219, 'Central / State Labour Authority', 'Controlling Authority under Payment of Gratuity Act / Assistant Labour Commissioner',
    30, 'https://shramsuvidha.gov.in'
) ON CONFLICT (procedure_slug) DO UPDATE SET
    procedure_name = EXCLUDED.procedure_name,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    governing_law_id = EXCLUDED.governing_law_id,
    governing_section_id = EXCLUDED.governing_section_id,
    jurisdiction = EXCLUDED.jurisdiction,
    authority_type = EXCLUDED.authority_type,
    estimated_processing_days = EXCLUDED.estimated_processing_days,
    official_portal_url = EXCLUDED.official_portal_url;

-- 22. EMPLOYEE COMPENSATION CLAIM FOR WORKPLACE INJURY
INSERT INTO legal_procedures (
    procedure_id, procedure_name, procedure_slug, category, description,
    governing_law_id, governing_section_id, jurisdiction, authority_type,
    estimated_processing_days, official_portal_url
) VALUES (
    22,
    'Employee Compensation Claim for Workplace Injury',
    'employee-compensation-injury-claim',
    'Employment / Social',
    'Statutory application before the Commissioner for Employee''s Compensation seeking statutory indemnity and damages for employment injuries, occupational diseases, or death under the Employees'' Compensation Act, 1923.',
    1347, 8240, 'Central / State Labour Authority', 'Commissioner for Employee''s Compensation (Labour Court / Industrial Tribunal)',
    90, 'https://mahakamgar.maharashtra.gov.in'
) ON CONFLICT (procedure_slug) DO UPDATE SET
    procedure_name = EXCLUDED.procedure_name,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    governing_law_id = EXCLUDED.governing_law_id,
    governing_section_id = EXCLUDED.governing_section_id,
    jurisdiction = EXCLUDED.jurisdiction,
    authority_type = EXCLUDED.authority_type,
    estimated_processing_days = EXCLUDED.estimated_processing_days,
    official_portal_url = EXCLUDED.official_portal_url;

-- 23. FIRST INFORMATION REPORT (FIR) / POLICE COMPLAINT FILING
INSERT INTO legal_procedures (
    procedure_id, procedure_name, procedure_slug, category, description,
    governing_law_id, governing_section_id, jurisdiction, authority_type,
    estimated_processing_days, official_portal_url
) VALUES (
    23,
    'First Information Report (FIR) / Police Complaint Filing',
    'fir-police-complaint-filing',
    'Court / Litigation',
    'Statutory reporting of cognizable offences under Section 154 CrPC / Section 173 BNSS, 2023, Zero FIR registration, and complaints to Superintendent of Police.',
    1255, 40538, 'Central / Maharashtra Police', 'Station House Officer (SHO) / Senior Inspector of Police / Superintendent of Police',
    1, 'https://citizen.mahapolice.gov.in'
) ON CONFLICT (procedure_slug) DO UPDATE SET
    procedure_name = EXCLUDED.procedure_name,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    governing_law_id = EXCLUDED.governing_law_id,
    governing_section_id = EXCLUDED.governing_section_id,
    jurisdiction = EXCLUDED.jurisdiction,
    authority_type = EXCLUDED.authority_type,
    estimated_processing_days = EXCLUDED.estimated_processing_days,
    official_portal_url = EXCLUDED.official_portal_url;

-- 24. BAIL APPLICATION (REGULAR & ANTICIPATORY BAIL)
INSERT INTO legal_procedures (
    procedure_id, procedure_name, procedure_slug, category, description,
    governing_law_id, governing_section_id, jurisdiction, authority_type,
    estimated_processing_days, official_portal_url
) VALUES (
    24,
    'Bail Application (Regular & Anticipatory Bail)',
    'bail-application-regular-anticipatory',
    'Court / Litigation',
    'Judicial application seeking grant of regular bail after arrest (Sec 437/439 CrPC / Sec 480/483 BNSS) or anticipatory pre-arrest bail (Sec 438 CrPC / Sec 482 BNSS) before Sessions Court or High Court.',
    1255, NULL, 'Central / State Judiciary', 'Court of Session / High Court of Judicature / Judicial Magistrate (JMFC)',
    14, 'https://ecourts.gov.in'
) ON CONFLICT (procedure_slug) DO UPDATE SET
    procedure_name = EXCLUDED.procedure_name,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    governing_law_id = EXCLUDED.governing_law_id,
    governing_section_id = EXCLUDED.governing_section_id,
    jurisdiction = EXCLUDED.jurisdiction,
    authority_type = EXCLUDED.authority_type,
    estimated_processing_days = EXCLUDED.estimated_processing_days,
    official_portal_url = EXCLUDED.official_portal_url;

-- 25. STATUTORY LEGAL NOTICE & DEMAND
INSERT INTO legal_procedures (
    procedure_id, procedure_name, procedure_slug, category, description,
    governing_law_id, governing_section_id, jurisdiction, authority_type,
    estimated_processing_days, official_portal_url
) VALUES (
    25,
    'Statutory Legal Notice & Demand (Cheque Dishonour / Section 80 CPC)',
    'statutory-legal-notice-demand',
    'Court / Litigation',
    'Mandatory statutory demand notice served through an advocate demanding payment within 15 days upon cheque dishonour (Section 138 NI Act) or giving 2 months pre-suit notice to government (Section 80 CPC).',
    549, 25803, 'Central / National', 'Practicing Advocate / High Court Bar Association',
    30, 'https://www.indiapost.gov.in'
) ON CONFLICT (procedure_slug) DO UPDATE SET
    procedure_name = EXCLUDED.procedure_name,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    governing_law_id = EXCLUDED.governing_law_id,
    governing_section_id = EXCLUDED.governing_section_id,
    jurisdiction = EXCLUDED.jurisdiction,
    authority_type = EXCLUDED.authority_type,
    estimated_processing_days = EXCLUDED.estimated_processing_days,
    official_portal_url = EXCLUDED.official_portal_url;

-- Ensure sequence matches highest ID
SELECT setval('legal_procedures_procedure_id_seq', (SELECT COALESCE(MAX(procedure_id), 1) FROM legal_procedures));

-- ====================================================================
-- 2. DOCUMENT CHECKLIST REQUIREMENTS FOR PROCEDURES 9 TO 25
-- ====================================================================

-- 2.1 MARRIAGE REGISTRATION DOCUMENTS (Procedure 9)
DELETE FROM procedure_required_documents WHERE procedure_id = 9;
INSERT INTO procedure_required_documents (
    procedure_id, document_name, document_type, is_mandatory, purpose,
    preparation_guidance, statutory_reference_id, order_index
) VALUES
(9, 'Duly Signed Memorandum of Marriage (Form I / Form A)', 'Statutory Form', TRUE,
 'Statutory memorandum signed by both husband and wife and three witnesses under Section 16.',
 'Complete Form I with exact solemnization details, addresses, and signatures matching official identity cards.', 33824, 1),
(9, 'Age and Date of Birth Proof of Bridegroom and Bride', 'Identity Proof', TRUE,
 'Establishes lawful age of marriage (male 21 years, female 18 years) pursuant to statutory requirements.',
 'Attach self-attested School Leaving Certificate, Birth Certificate, or Passport for both parties.', NULL, 2),
(9, 'Address Proof of Husband and Wife', 'Address Proof', TRUE,
 'Establishes residential jurisdiction of the Marriage Officer / Sub-Registrar Office.',
 'Aadhaar Card, Voter Identity Card, Electricity Bill, or Registered Rent Agreement showing local residence.', NULL, 3),
(9, 'Wedding Invitation Card or Solemnization Certificate', 'Evidence', TRUE,
 'Primary documentary proof that marriage solemnization ceremony took place according to customary rites.',
 'Original printed wedding card or solemnization certificate issued by temple priest, church, or nikah registrar.', NULL, 4),
(9, 'Passport Size Photographs of Bride and Groom', 'Identity Proof', TRUE,
 'Required for physical register affixation and computerized marriage certificate issue.',
 'Four recent color passport-size photographs of bride and groom on white background.', NULL, 5),
(9, 'Identity and Address Proof of Three Adult Witnesses', 'Identity Proof', TRUE,
 'Statutory requirement under Section 15/16 requiring three witnesses to testify to the marriage.',
 'Self-attested copies of Aadhaar Card or PAN Card of 3 witnesses who must be physically present.', 33824, 6),
(9, 'Divorce Decree or Death Certificate of Former Spouse (if applicable)', 'Court Order / Certificate', FALSE,
 'Required only if either spouse was previously married to demonstrate legal capacity to marry.',
 'Certified copy of court divorce decree or official municipal death certificate of deceased spouse.', NULL, 7);

-- 2.2 BIRTH CERTIFICATE REGISTRATION DOCUMENTS (Procedure 10)
DELETE FROM procedure_required_documents WHERE procedure_id = 10;
INSERT INTO procedure_required_documents (
    procedure_id, document_name, document_type, is_mandatory, purpose,
    preparation_guidance, statutory_reference_id, order_index
) VALUES
(10, 'Institutional Birth Report (Form 1) from Hospital', 'Statutory Form', TRUE,
 'Statutory notification submitted by the medical institution to the local Registrar under Section 8.',
 'Original Form 1 signed and stamped by medical superintendent or hospital administration.', 31463, 1),
(10, 'Parents'' Identity and Address Proof', 'Identity Proof', TRUE,
 'Verifies parentage and residency jurisdiction for record entry.',
 'Self-attested photocopies of Aadhaar Cards and Voter IDs of both mother and father.', NULL, 2),
(10, 'Parents'' Marriage Certificate', 'Government Certificate', FALSE,
 'Corroborates legitimate marital status and joint surname registration for child.',
 'Copy of registered marriage certificate or joint affidavit if married.', NULL, 3),
(10, 'Sub-Divisional Magistrate (SDM) Order (for delayed registration > 1 year)', 'Magistrate Order', FALSE,
 'Section 13(3) mandates that births reported after 1 year require an order from an Executive Magistrate.',
 'Obtain delayed entry order from local Tahsildar / Executive Magistrate upon non-availability certificate.', 31468, 4),
(10, 'Notarized Affidavit for Child Name Inclusion or Clerical Correction', 'Affidavit', FALSE,
 'Required under Section 15 when adding child name later or rectifying parental spelling errors.',
 'Affidavit on non-judicial stamp paper attested by Notary Public detailing correct spelling and error reason.', 31470, 5),
(10, 'School Bonafide or Immunization Card (for delayed verification)', 'Supporting Record', FALSE,
 'Corroborating record of child''s birth date and birth place for revenue inquiry.',
 'Copy of child immunization card from hospital or school admission bonafide certificate.', NULL, 6);

-- 2.3 DEATH CERTIFICATE REGISTRATION DOCUMENTS (Procedure 11)
DELETE FROM procedure_required_documents WHERE procedure_id = 11;
INSERT INTO procedure_required_documents (
    procedure_id, document_name, document_type, is_mandatory, purpose,
    preparation_guidance, statutory_reference_id, order_index
) VALUES
(11, 'Institutional Death Report (Form 2) or Medical Cause of Death (Form 4/4A)', 'Statutory Form', TRUE,
 'Statutory notification of death and medical cause issued by hospital doctor under Section 8/10.',
 'Original Form 2 and Medical Cause of Death Certificate signed by attending medical practitioner.', 31463, 1),
(11, 'Crematorium / Burial Ground Receipt', 'Evidence', TRUE,
 'Conclusive physical proof of disposal of deceased body with exact date, time, and location.',
 'Original stamped slip or receipt issued by authorized municipal crematorium or cemetery.', NULL, 2),
(11, 'Identity Proof of Deceased Person', 'Identity Proof', TRUE,
 'Establishes legal identity, age, and UID particulars of the deceased for permanent registry entry.',
 'Original and copy of Aadhaar Card, PAN Card, or Voter Identity Card of the deceased.', NULL, 3),
(11, 'Applicant / Informant Identity Proof and Relationship Proof', 'Identity Proof', TRUE,
 'Identifies the informant who is family member or close relative reporting the death.',
 'Aadhaar Card and proof of familial relationship (ration card, marriage certificate, or birth certificate).', NULL, 4),
(11, 'Police Inquest and Post-Mortem Report (for unnatural death / accident)', 'Police Record', FALSE,
 'Mandatory in accidental, suicidal, or homicidal deaths to establish cause before registration.',
 'Certified copies of Police Inquest Panchnama (Form 174 CrPC) and Post-Mortem Examination Report.', NULL, 5),
(11, 'Executive Magistrate Order for Delayed Registration (if reported after 1 year)', 'Magistrate Order', FALSE,
 'Section 13(3) requires permission of an Executive Magistrate for deaths unregistered after 365 days.',
 'File delayed death entry petition before Sub-Divisional Magistrate / Tahsildar with non-availability certificate.', 31468, 6);

-- 2.4 NAME CHANGE AND GAZETTE PUBLICATION DOCUMENTS (Procedure 12)
DELETE FROM procedure_required_documents WHERE procedure_id = 12;
INSERT INTO procedure_required_documents (
    procedure_id, document_name, document_type, is_mandatory, purpose,
    preparation_guidance, statutory_reference_id, order_index
) VALUES
(12, 'Sworn Name Change Affidavit on Non-Judicial Stamp Paper', 'Affidavit', TRUE,
 'Solemn legal affirmation declaring change of old name to new name and intention to be known by new name.',
 'Execute on ₹100 non-judicial stamp paper, state father/spouse name, address, and swear before Notary Public.', NULL, 1),
(12, 'Original Newspaper Clippings of Name Change Advertisement', 'Public Notice', TRUE,
 'Public intimation published in two newspapers (one English national daily and one regional state newspaper).',
 'Full original newspaper page showing publication date, newspaper title, and boxed name change declaration.', NULL, 2),
(12, 'Prescribed Official Gazette Application Form & Proforma CD', 'Statutory Form', TRUE,
 'Official application submitted to the Government Printing Directorate for printing in Gazette.',
 'Fill Gazette proforma typed in specified font and format along with MS Word copy on CD or digital upload.', NULL, 3),
(12, 'Identity Proof with Old Name (Aadhaar / PAN / Passport)', 'Identity Proof', TRUE,
 'Verification of applicant''s lawful existence and prior name record in government databases.',
 'Self-attested photocopy of existing Aadhaar Card, PAN Card, or Passport.', NULL, 4),
(12, 'Current Residential Address Proof', 'Address Proof', TRUE,
 'Establishes state jurisdiction for publication in the Maharashtra or Central Gazette.',
 'Self-attested copy of Electricity Bill, Voter ID, or Registered Lease Agreement.', NULL, 5),
(12, 'Marriage Certificate / Divorce Decree (for matrimonial name change)', 'Government Certificate', FALSE,
 'Required when name change is consequential to marriage, divorce, or remarriage.',
 'Copy of registered marriage certificate or certified family court divorce decree.', NULL, 6),
(12, 'Passport Size Photographs of Applicant', 'Identity Proof', TRUE,
 'Two recent passport photographs cross-signed by applicant for government archive records.',
 'Attach 2 passport-size color photographs matching specification.', NULL, 7);

-- 2.5 DOMICILE & NATIONALITY CERTIFICATE DOCUMENTS (Procedure 13)
DELETE FROM procedure_required_documents WHERE procedure_id = 13;
INSERT INTO procedure_required_documents (
    procedure_id, document_name, document_type, is_mandatory, purpose,
    preparation_guidance, statutory_reference_id, order_index
) VALUES
(13, 'Application Form for Domicile Certificate (Aaple Sarkar / Revenue Form)', 'Statutory Form', TRUE,
 'Prescribed statutory application for Domicile and Nationality Certificate under Maharashtra Citizen Charter.',
 'Complete through Aaple Sarkar portal or submit hardcopy at Tahsildar / Setu Suvidha Kendra.', 7252, 1),
(13, 'Proof of 15 Years Continuous Residence in Maharashtra', 'Residence Proof', TRUE,
 'Primary statutory criterion proving applicant has resided within Maharashtra for minimum 15 consecutive years.',
 'Produce continuous sequence of school leaving certificates, rent agreements, electricity bills, or property tax receipts.', NULL, 2),
(13, 'Birth Certificate or School Leaving Certificate of Applicant', 'Educational Document', TRUE,
 'Proof of age, birthplace, and schooling history establishing origin.',
 'Original or certified true copy of School Leaving Certificate (SLC) or Municipal Birth Certificate.', NULL, 3),
(13, 'Identity Proof of Applicant (Aadhaar / Voter ID)', 'Identity Proof', TRUE,
 'Biometric identity verification under Aaple Sarkar digital framework.',
 'Self-attested copy of Aadhaar Card and Voter Identity Card with active mobile number.', NULL, 4),
(13, 'Self-Declaration / Affidavit of Domicile in Prescribed Format', 'Affidavit', TRUE,
 'Sworn declaration affirming applicant has not obtained domicile of any other State or Union Territory.',
 'Signed self-declaration on Aaple Sarkar portal or notarized affidavit on stamp paper.', NULL, 5),
(13, 'Father / Parent''s Domicile Certificate (for minor applicant)', 'Parental Proof', FALSE,
 'Establishes derivative domicile for applicants below 18 years of age.',
 'Attach father''s or mother''s existing Domicile Certificate and parental relationship proof.', NULL, 6);

-- 2.6 INCOME CERTIFICATE DOCUMENTS (Procedure 14)
DELETE FROM procedure_required_documents WHERE procedure_id = 14;
INSERT INTO procedure_required_documents (
    procedure_id, document_name, document_type, is_mandatory, purpose,
    preparation_guidance, statutory_reference_id, order_index
) VALUES
(14, 'Prescribed Income Certificate Application Form (Aaple Sarkar Form)', 'Statutory Form', TRUE,
 'Statutory application submitted to Tahsildar for family annual income assessment.',
 'Fill online on Aaple Sarkar portal or submit at Taluka Setu Kendra with family details.', NULL, 1),
(14, 'Salary Certificate / Form 16 / ITR (for Salaried / Business Applicants)', 'Financial Document', TRUE,
 'Documentary proof of income for organized sector employees or business owners.',
 'Employer salary certificate with TDS deduction details, Form 16, or Income Tax Return acknowledgment.', NULL, 2),
(14, 'Talathi / Circle Officer Income Verification Report (for Agricultural / Informal Sector)', 'Revenue Document', TRUE,
 'Local field inquiry report assessing crop yield, agricultural holding, or informal family earnings.',
 'Obtain field verification signature from local Talathi after inspecting 7/12 extract and village records.', NULL, 3),
(14, 'Applicant and Head of Family Identity Proof (Aadhaar / PAN)', 'Identity Proof', TRUE,
 'KYC identification of the earning member and applicant.',
 'Self-attested copies of Aadhaar Card and PAN Card of family members.', NULL, 4),
(14, 'Ration Card / Family Member Listing Proof', 'Family Proof', TRUE,
 'Demonstrates total number of dependents living in the joint household.',
 'Photocopy of Ration Card (Yellow / Saffron / White) showing all family member names.', NULL, 5),
(14, 'Sworn Self-Declaration / Affidavit of Annual Household Income', 'Affidavit', TRUE,
 'Sworn undertaking affirming that total household earnings from all sources do not exceed declared amount.',
 'Standard Aaple Sarkar digital self-declaration or notarized affidavit on ₹100 stamp paper.', NULL, 6);

-- 2.7 CASTE CERTIFICATE & SCRUTINY DOCUMENTS (Procedure 15)
DELETE FROM procedure_required_documents WHERE procedure_id = 15;
INSERT INTO procedure_required_documents (
    procedure_id, document_name, document_type, is_mandatory, purpose,
    preparation_guidance, statutory_reference_id, order_index
) VALUES
(15, 'Application Form for Caste Certificate & Form ''E'' for Scrutiny Verification', 'Statutory Form', TRUE,
 'Statutory dual application for initial certificate from SDO and verification before Scrutiny Committee.',
 'Complete through CCVIS portal or Aaple Sarkar with father''s genealogy and native village details.', NULL, 1),
(15, 'Primary Paternal Proof Pre-dating Cut-off Date (1950 SC / 1961 VJNT / 1967 OBC)', 'Historical Revenue Record', TRUE,
 'Mandatory statutory proof establishing applicant''s forefathers resided in Maharashtra prior to deemed date.',
 'Extract of Village Kotwal Book (Form 14), Birth/Death extract of grandfather, or pre-cutoff school records.', NULL, 2),
(15, 'School Leaving Certificate of Applicant Showing Caste and Sub-caste', 'Educational Document', TRUE,
 'Primary personal school record recording recognized caste categorization.',
 'Certified true copy of General Register (GR) extract and School Leaving Certificate signed by Headmaster.', NULL, 3),
(15, 'School Leaving Certificate / Birth Extract of Father or Paternal Uncle', 'Family Proof', TRUE,
 'Establishes uninterrupted biological paternal lineage carrying the claimed caste.',
 'Certified copy of father''s or paternal blood relative''s school leaving certificate or municipal record.', NULL, 4),
(15, 'Genealogical Family Tree Affidavit (Varas Patrak / Vamshavali) on Stamp Paper', 'Affidavit', TRUE,
 'Detailed genealogical chart showing direct relationship from original ancestor to applicant.',
 'Executed on non-judicial stamp paper, sworn before Executive Magistrate or Notary with family signatures.', NULL, 5),
(15, '7/12 Extract or Village Land Records of Ancestral Village', 'Revenue Record', FALSE,
 'Demonstrates ancestral residence and landholding in native district prior to migration.',
 'Digital 7/12 extract or 8-A khata extract showing forefather''s name from native taluka.', NULL, 6),
(15, 'Caste Validity Certificate of Any Blood Relative from Paternal Line', 'Government Certificate', FALSE,
 'Provides strong corroborative precedent under Section 7 of Maharashtra Act XXIII of 2001.',
 'Attach attested copy of Caste Validity Certificate issued to father, sibling, or paternal cousin.', NULL, 7);

-- 2.8 LEGAL HEIR / SURVIVING MEMBER CERTIFICATE DOCUMENTS (Procedure 16)
DELETE FROM procedure_required_documents WHERE procedure_id = 16;
INSERT INTO procedure_required_documents (
    procedure_id, document_name, document_type, is_mandatory, purpose,
    preparation_guidance, statutory_reference_id, order_index
) VALUES
(16, 'Prescribed Legal Heir Application Form (Form VIII / Setu Form)', 'Statutory Form', TRUE,
 'Formal administrative application submitted to Tahsildar / SDM for surviving member listing.',
 'Complete Form VIII specifying deceased particulars, date of death, and all surviving direct heirs.', 17292, 1),
(16, 'Official Death Certificate of the Deceased', 'Government Certificate', TRUE,
 'Primary proof establishing fact and date of demise of the family head under Section 12.',
 'Original or certified true copy issued by Municipal Corporation, Nagar Parishad, or Gram Panchayat.', 31467, 2),
(16, 'Identity Proof (Aadhaar / Voter ID) of All Surviving Legal Heirs', 'Identity Proof', TRUE,
 'Verifies identities and ages of surviving spouse, children, and dependent parents.',
 'Self-attested photocopies of Aadhaar Cards and PAN Cards of all living family members listed in petition.', NULL, 3),
(16, 'Family Tree Affidavit (Varas Patrak) Sworn by Applicant on ₹100 Stamp Paper', 'Affidavit', TRUE,
 'Solemn affidavit affirming under oath the complete and exhaustive list of all surviving legal heirs.',
 'Must state deceased left no other heirs, whether first or second class, sworn before Notary Public.', NULL, 4),
(16, 'No Objection Certificates (NOC) / Consent Affidavits from Other Surviving Heirs', 'Affidavit', TRUE,
 'Consents from all adult legal heirs authorizing applicant to represent the estate or receive dues.',
 'Notarized affidavits executed on stamp paper signed by each surviving heir with passport photos.', NULL, 5),
(16, 'Talathi Spot Inquiry Report and Panchnama', 'Revenue Document', TRUE,
 'Independent revenue field verification verifying local family composition in the village/ward.',
 'Issued by local Talathi / Revenue Circle Officer following physical inspection and neighbor enquiry.', NULL, 6),
(16, 'Ration Card / Family Pension Book of Deceased', 'Family Proof', FALSE,
 'Corroborative household proof showing cohabitation and family dependency prior to death.',
 'Copy of ration card or service record sheet naming spouse and dependent children.', NULL, 7);

-- 2.9 PROPERTY ENCUMBRANCE CERTIFICATE & SEARCH DOCUMENTS (Procedure 17)
DELETE FROM procedure_required_documents WHERE procedure_id = 17;
INSERT INTO procedure_required_documents (
    procedure_id, document_name, document_type, is_mandatory, purpose,
    preparation_guidance, statutory_reference_id, order_index
) VALUES
(17, 'Application for Inspection and Search of Registration Books (Form 54 / Gras Form)', 'Statutory Form', TRUE,
 'Statutory application under Section 57 to inspect Book 1 records and obtain Encumbrance Certificate.',
 'Submit online via IGR Maharashtra e-Search portal or file physical Form 54 at Sub-Registrar office.', 31407, 1),
(17, 'Precise Property Demarcation Particulars (Survey / CTS / Flat Number)', 'Property Identifier', TRUE,
 'Essential identifiers required to locate property in Index II and revenue books under Section 51.',
 'Provide exact City Survey (CTS) No., Survey/Gat No., Village name, Sub-Registrar jurisdiction, and plot area.', 31401, 2),
(17, 'Copy of Preceding Registered Title Deed or Registration Number with Year', 'Title Deed', FALSE,
 'Facilitates fast retrieval of historical volume and page numbers in Sub-Registrar archives.',
 'Photocopy of registered sale deed, gift deed, or Index II extract mentioning registration number.', NULL, 3),
(17, 'Applicant Identity Proof (Aadhaar / PAN Card)', 'Identity Proof', TRUE,
 'Verification of search applicant pursuant to government e-governance guidelines.',
 'Self-attested copy of Aadhaar Card or PAN Card of the applicant or advocate conducting search.', NULL, 4),
(17, 'Government Treasury Search Fee Receipt (Gras Challan)', 'Financial Document', TRUE,
 'Statutory search fee and certified copy fee paid to government treasury.',
 'Attach cyber treasury receipt generated via GRAS (Government Receipt Accounting System) Maharashtra.', NULL, 5),
(17, 'Latest 7/12 Extract or Property Card (PR Card)', 'Revenue Document', FALSE,
 'Corroborating record of rights extract matching current revenue mutation entries.',
 'Digital 7/12 extract or City Survey Property Card downloaded within last 30 days.', NULL, 6);

-- 2.10 BANKING OMBUDSMAN COMPLAINT DOCUMENTS (Procedure 18)
DELETE FROM procedure_required_documents WHERE procedure_id = 18;
INSERT INTO procedure_required_documents (
    procedure_id, document_name, document_type, is_mandatory, purpose,
    preparation_guidance, statutory_reference_id, order_index
) VALUES
(18, 'Formal Complaint Statement before Ombudsman (CMS Portal / Physical Form)', 'Statutory Form', TRUE,
 'Statutory complaint stating nature of deficiency, disputed amount, and relief claimed under RBI Scheme.',
 'File online on RBI CMS portal stating chronological timeline, transaction reference IDs, and branch name.', 3035, 1),
(18, 'Copy of Initial Written Complaint to Concerned Bank Branch / GRO', 'Grievance Record', TRUE,
 'Clause 10 of Scheme mandates that customer must first approach bank grievance redressal.',
 'Attach stamped duplicate letter, email thread, or online complaint ticket acknowledgment from bank.', NULL, 2),
(18, 'Bank Rejection Reply or Proof of Lapse of 30 Days without Redressal', 'Evidence', TRUE,
 'Condition precedent establishing right to approach Ombudsman after 30 days of unaddressed grievance.',
 'Copy of bank''s rejection communication or proof that 30 calendar days elapsed since initial complaint.', NULL, 3),
(18, 'Bank Account Statement Highlighting Disputed Transactions', 'Financial Document', TRUE,
 'Primary financial evidence demonstrating unauthorized debit, excess interest, or uncredited deposit.',
 'Bank account statement or passbook photocopy clearly highlighting date, reference number, and amount.', NULL, 4),
(18, 'Supporting Evidence (Cheques, ATM Slips, SMS Alerts, Cyber Police Complaint)', 'Evidence', FALSE,
 'Corroborating materials proving non-dispensation of cash or fraudulent phishing transaction.',
 'Copies of disputed cheques, ATM error slips, SMS alerts, or National Cyber Crime Reporting acknowledgment.', NULL, 5),
(18, 'Complainant Identity Proof and Contact Particulars', 'Identity Proof', TRUE,
 'Verification of bank account holder identity and correspondence details.',
 'Self-attested copy of Aadhaar Card or Passport matching name registered with the bank.', NULL, 6);

-- 2.11 INSURANCE OMBUDSMAN COMPLAINT DOCUMENTS (Procedure 19)
DELETE FROM procedure_required_documents WHERE procedure_id = 19;
INSERT INTO procedure_required_documents (
    procedure_id, document_name, document_type, is_mandatory, purpose,
    preparation_guidance, statutory_reference_id, order_index
) VALUES
(19, 'Formal Complaint Petition in Form VI-A under Insurance Ombudsman Rules', 'Statutory Form', TRUE,
 'Statutory complaint stating policy number, repudiated claim amount, and grounds of dispute under Rule 14.',
 'Complete Form VI-A with full insurer name, policy number, loss date, and net compensation claimed (max ₹30L).', NULL, 1),
(19, 'Complete Policy Document Schedule and Terms & Conditions', 'Policy Document', TRUE,
 'Primary contractual agreement defining insurance cover, exclusions, and waiting periods.',
 'Photocopy of full insurance policy bond, schedule, and endorsement clauses issued by the insurer.', NULL, 2),
(19, 'Claim Intimation and Claim Form Submitted to Insurer / TPA', 'Claim Form', TRUE,
 'Proof that formal claim was lodged with insurer within prescribed policy timeline.',
 'Copy of filled claim form, claim reference number, and documentary submission checklist.', NULL, 3),
(19, 'Repudiation / Rejection Letter or Partial Settlement Voucher from Insurer', 'Evidence', TRUE,
 'Primary subject matter of grievance demonstrating unjust refusal or arbitrary deductions.',
 'Official repudiation letter citing rejection clause, or settlement voucher showing deductions.', NULL, 4),
(19, 'Written Representation to Insurer''s Grievance Redressal Officer (GRO)', 'Grievance Record', TRUE,
 'Rule 14(3) requires policyholder to represent to insurer''s internal grievance cell prior to Ombudsman.',
 'Copy of email or speed post letter addressed to GRO and insurer''s final rejection or 30-day non-reply.', NULL, 5),
(19, 'Complete Hospital Medical Records / Loss Assessment Report', 'Medical / Loss Record', TRUE,
 'Substantive medical records proving hospitalization, diagnosis, indoor case papers, or surveyor report.',
 'Discharge summary, hospital indoor case papers (ICP), itemized pharmacy bills, diagnostic reports.', NULL, 6),
(19, 'Self-Declaration Confirming No Parallel Court / Consumer Commission Litigation', 'Affidavit / Declaration', TRUE,
 'Statutory declaration required by Ombudsman confirming dispute is not sub-judice before consumer court.',
 'Signed declaration confirming no suit, arbitration, or consumer complaint is pending on same cause.', NULL, 7);

-- 2.12 EPFO / PF SETTLEMENT CLAIM DOCUMENTS (Procedure 20)
DELETE FROM procedure_required_documents WHERE procedure_id = 20;
INSERT INTO procedure_required_documents (
    procedure_id, document_name, document_type, is_mandatory, purpose,
    preparation_guidance, statutory_reference_id, order_index
) VALUES
(20, 'Composite Claim Form (Aadhaar / Non-Aadhaar) (Form 19 / 10C / 31)', 'Statutory Form', TRUE,
 'Statutory claim form for full PF withdrawal (19), pension scheme certificate/withdrawal (10C), or advance (31).',
 'Submit online via EPFO Unified Member Portal or submit signed composite form to Regional PF Office.', 8170, 1),
(20, 'Original Cancelled Bank Cheque Leaf with Member Name and IFSC Printed', 'Financial Document', TRUE,
 'Proof of bank account for electronic NEFT credit of settlement funds by EPFO.',
 'Cancelled cheque leaf with pre-printed account holder name, account number, and IFSC, or attested passbook.', NULL, 2),
(20, 'UAN Card & Aadhaar Linked with EPFO Database', 'Identity Document', TRUE,
 'Mandatory e-KYC requirement for direct online settlement without employer intervention.',
 'Active Universal Account Number (UAN) with Aadhaar, PAN, and bank details verified and approved by employer.', NULL, 3),
(20, 'Member PAN Card Photocopy', 'Financial Document', TRUE,
 'Mandatory for TDS calculation under Section 192A if service period is less than 5 years and PF balance > ₹50,000.',
 'Self-attested copy of PAN Card linked with EPFO member account.', NULL, 4),
(20, 'Form 15G / Form 15H for TDS Exemption (if applicable)', 'Tax Form', FALSE,
 'Prevents deduction of TDS on taxable PF withdrawal if member income is below taxable threshold.',
 'Upload Form 15G (for individuals below 60 years) or Form 15H (for senior citizens) on portal.', NULL, 5),
(20, 'Date of Exit Mark Record Updated by Employer on Portal', 'Employment Record', TRUE,
 'Statutory requirement confirming cessation of employment for two consecutive months for final PF closure.',
 'Verify that Date of Exit is recorded by employer in service history tab on Member Unified Portal.', 8181, 6);

-- 2.13 PAYMENT OF GRATUITY CLAIM DOCUMENTS (Procedure 21)
DELETE FROM procedure_required_documents WHERE procedure_id = 21;
INSERT INTO procedure_required_documents (
    procedure_id, document_name, document_type, is_mandatory, purpose,
    preparation_guidance, statutory_reference_id, order_index
) VALUES
(21, 'Statutory Notice / Application for Gratuity in Form ''I'' or Form ''N''', 'Statutory Form', TRUE,
 'Form ''I'' is statutory notice to employer under Rule 7; Form ''N'' is petition before Controlling Authority.',
 'Submit Form ''I'' within 30 days of eligibility; if unpaid within 30 days, file Form ''N'' before Labour Commissioner.', 8219, 1),
(21, 'Appointment Letter / Employment Contract & Employee ID Proof', 'Employment Record', TRUE,
 'Proves employer-employee relationship and continuous service of at least 5 years.',
 'Copy of appointment letter, regularized employment orders, and employee identity badge.', NULL, 2),
(21, 'Relieving Letter, Resignation Acceptance, or Superannuation Order', 'Employment Record', TRUE,
 'Establishes lawful cessation of employment qualifying employee for statutory gratuity.',
 'Copy of employer relieving letter, resignation acceptance mail, or formal superannuation order.', NULL, 3),
(21, 'Last Drawn Salary Slip Demonstrating Basic Wages and DA', 'Financial Document', TRUE,
 'Gratuity computation formula (15 days wages per completed year of service) is calculated on basic + DA.',
 'Attach last 3 months salary slips or salary certificate from HR specifying basic wage and dearness allowance.', 8222, 4),
(21, 'Bank Account Details & Cancelled Cheque for Gratuity Disbursement', 'Financial Document', TRUE,
 'Enables employer or Controlling Authority to credit adjudicated gratuity sum directly.',
 'Cancelled bank cheque or bank account passbook copy showing account number and IFSC code.', NULL, 5),
(21, 'Proof of Service of Form ''I'' upon Employer (Speed Post Receipt / Tracking)', 'Evidence', TRUE,
 'Mandatory condition precedent proving employee demanded gratuity from employer before filing Form ''N''.',
 'India Post speed post receipt and delivery confirmation report proving employer received Form ''I''.', NULL, 6),
(21, 'Nomination Form in Form ''F'' (if claim filed by legal heirs upon death)', 'Statutory Form', FALSE,
 'Required when claim is submitted by nominee or legal heirs following demise of employee.',
 'Copy of Form ''F'' registered with employer, along with death certificate and legal heir certificate.', NULL, 7);

-- 2.14 EMPLOYEE COMPENSATION FOR WORKPLACE INJURY DOCUMENTS (Procedure 22)
DELETE FROM procedure_required_documents WHERE procedure_id = 22;
INSERT INTO procedure_required_documents (
    procedure_id, document_name, document_type, is_mandatory, purpose,
    preparation_guidance, statutory_reference_id, order_index
) VALUES
(22, 'Statutory Claim Application in Form ''A'' / Form ''F'' before Commissioner', 'Pleading', TRUE,
 'Formal petition under Section 10/22 claiming compensation for personal injury caused by accident.',
 'Drafted stating employment nature, hazardous conditions, date of mishap, and statutory compensation claimed.', 8240, 1),
(22, 'Notice of Accident Served on Employer under Section 10', 'Statutory Notice', TRUE,
 'Statutory requirement requiring employee or dependents to notify employer as soon as practicable.',
 'Copy of accident notice served on employer with proof of dispatch or factory injury book entry.', NULL, 2),
(22, 'Disability Certificate Issued by Civil Surgeon or Authorized Medical Board', 'Medical Record', TRUE,
 'Conclusive medical assessment establishing percentage of loss of earning capacity under Section 4.',
 'Certificate from Government Civil Hospital or Medical Board certifying percentage of permanent disablement.', 8242, 3),
(22, 'Hospital Treatment Records, Surgical Bills, and Discharge Summary', 'Medical Record', TRUE,
 'Proves immediate hospitalization, surgical intervention, medical expenses, and nature of trauma.',
 'Complete hospital records, operation theater notes, discharge summary, and medical expense vouchers.', NULL, 4),
(22, 'Proof of Employment and Wage Slip Showing Monthly Remuneration', 'Employment Record', TRUE,
 'Statutory compensation amount is directly linked to monthly wage and relevant age factor.',
 'Wage slip, attendance muster roll extract, or bank credit statement confirming employment.', NULL, 5),
(22, 'Police FIR / Accident Panchnama Report (for site or transport mishaps)', 'Police Record', FALSE,
 'Corroborating official inquiry conducted by police or factory inspector following workplace accident.',
 'Certified copy of Police FIR, spot panchnama, or Factory Inspectorate accident investigation report.', NULL, 6),
(22, 'Death Certificate & Legal Heir Certificate (in fatal injury claims)', 'Government Certificate', FALSE,
 'Required when fatal injury claim is presented by surviving dependents under Section 8.',
 'Original death certificate, post-mortem report, and Legal Heir Certificate from revenue authority.', NULL, 7);

-- 2.15 FIRST INFORMATION REPORT (FIR) / POLICE COMPLAINT DOCUMENTS (Procedure 23)
DELETE FROM procedure_required_documents WHERE procedure_id = 23;
INSERT INTO procedure_required_documents (
    procedure_id, document_name, document_type, is_mandatory, purpose,
    preparation_guidance, statutory_reference_id, order_index
) VALUES
(23, 'Written Complaint Statement Signed by Informant', 'Statutory Pleading', TRUE,
 'Statutory written information disclosing commission of a cognizable offence under Section 154 CrPC / 173 BNSS.',
 'State chronological sequence of events, exact date, time, location, suspect particulars, and role played.', 40538, 1),
(23, 'Informant KYC Identification Proof (Aadhaar / Voter ID / Passport)', 'Identity Proof', TRUE,
 'Establishes lawful identity and residential address of informant for police investigation records.',
 'Self-attested copy of Aadhaar Card, Passport, or Voter Identity Card with contact telephone number.', NULL, 2),
(23, 'Medical Examination / Medico-Legal Case (MLC) Injury Report', 'Medical Record', FALSE,
 'Primary forensic proof of physical injury, assault, or bodily trauma in violent offences.',
 'Obtain injury certificate or MLC slip from Government or Municipal hospital casualty ward.', NULL, 3),
(23, 'Supporting Documentary / Electronic Evidence (Invoices, Chats, CCTV Footage)', 'Evidence', FALSE,
 'Corroborating evidence proving criminal fraud, cheating, criminal breach of trust, or threats.',
 'Printouts of WhatsApp messages, email trails, bank transaction debits, photos, or CCTV pen-drive.', NULL, 4),
(23, 'Speed Post Proof of Complaint Sent to Superintendent of Police (SP) u/s 154(3)', 'Postal Record', FALSE,
 'Statutory remedy when Station House Officer refuses to register FIR; complaint is escalated to SP.',
 'Postal speed post receipt and delivery report of written complaint dispatched to District SP or Commissioner.', 40538, 5),
(23, 'Duly Endorsed Stamped Duplicate Acknowledgement of FIR Copy', 'Official Record', TRUE,
 'Statutory entitlement under Section 154(2) where copy of recorded FIR shall be given to informant free of cost.',
 'Obtain signed and stamped duplicate copy of FIR from police station immediately upon registration.', 28035, 6);

-- 2.16 BAIL APPLICATION DOCUMENTS (Procedure 24)
DELETE FROM procedure_required_documents WHERE procedure_id = 24;
INSERT INTO procedure_required_documents (
    procedure_id, document_name, document_type, is_mandatory, purpose,
    preparation_guidance, statutory_reference_id, order_index
) VALUES
(24, 'Formal Bail Application Petition Stating Legal Grounds', 'Pleading', TRUE,
 'Judicial petition under Section 437/438/439 CrPC / BNSS seeking pre-arrest or post-arrest enlargement on bail.',
 'State case background, false implication, absence of flight risk, willingness to abide by conditions, and parity.', NULL, 1),
(24, 'Supporting Verification Affidavit Sworn by Accused or Close Relative (Pairokar)', 'Affidavit', TRUE,
 'Mandatory affidavit affirming facts and confirming that no other bail petition is pending before higher courts.',
 'Sworn on court stamp paper before Oath Commissioner or Court Superintendent by accused or relative.', NULL, 2),
(24, 'Certified Copy of FIR and Police Remand Application / Charge-sheet', 'Court Record', TRUE,
 'Provides court with exact allegations, statutory penal sections applied, and investigation stage.',
 'Obtain certified copy from court copying agency or download e-Courts authenticated copy.', NULL, 3),
(24, 'Executed Vakalatnama with Court Fee and Advocate Welfare Stamps', 'Legal Authorization', TRUE,
 'Authorizes advocate to represent and argue bail application before the court of law.',
 'Signed by accused (or jail superintendent if in judicial custody) and accepted by practicing counsel.', NULL, 4),
(24, 'Identity and Solvency Proof of Two Proposed Local Sureties', 'Surety Proof', TRUE,
 'Required for executing bail bonds upon court order granting bail to ensure accused attendance.',
 'Aadhaar Cards, Ration Cards, Property Tax receipts, or Solvency Certificates of two local solvent sureties.', NULL, 5),
(24, 'Medical Records / Age Proof for Special Grounds (under Section 437 Proviso)', 'Evidence', FALSE,
 'Special grounds for women, sick, infirm, or juvenile accused entitled to statutory bail preference.',
 'Government hospital diagnostic records, surgical history, or birth certificates proving minority/age.', NULL, 6),
(24, 'Certified Copy of Lower Court Bail Rejection Order (if applying to Sessions/HC)', 'Court Order', FALSE,
 'Mandatory when approaching Sessions Court or High Court following dismissal by lower Magistrate.',
 'Obtain certified copy of speaking rejection order passed by Magistrate / Sessions Judge.', NULL, 7);

-- 2.17 STATUTORY LEGAL NOTICE & DEMAND DOCUMENTS (Procedure 25)
DELETE FROM procedure_required_documents WHERE procedure_id = 25;
INSERT INTO procedure_required_documents (
    procedure_id, document_name, document_type, is_mandatory, purpose,
    preparation_guidance, statutory_reference_id, order_index
) VALUES
(25, 'Formal Legal Notice of Demand Drafted and Signed by Advocate', 'Notice', TRUE,
 'Statutory notice demanding payment within 15 days under Section 138(b) or 2 months notice under Sec 80 CPC.',
 'Drafted on advocate letterhead specifying transaction details, cheque numbers, return date, and statutory cure period.', 25803, 1),
(25, 'Original Dishonoured Cheque / Negotiable Instrument', 'Financial Document', TRUE,
 'Primary financial instrument presented for encashment and subsequently dishonoured.',
 'Retain pristine original cheque signed by drawer showing payee name, amount in words, and date.', 25803, 2),
(25, 'Bank Return Memo Stating Official Reason for Dishonour', 'Banking Record', TRUE,
 'Statutory bank advice under Section 146 creating legal presumption of dishonour (Funds Insufficient, etc.).',
 'Original stamped bank return memo issued by drawee bank with cheque return date and reason code.', 25803, 3),
(25, 'Proof of Underlying Legally Enforceable Debt or Liability', 'Evidence', TRUE,
 'Demonstrates cheque was issued in discharge of a legally enforceable debt as required by Section 138.',
 'Invoices, work contracts, loan agreement, promissory notes, delivery challans, or ledger statements.', NULL, 4),
(25, 'Speed Post / Registered Post Acknowledgement Due (RPAD) Postal Receipts', 'Postal Record', TRUE,
 'Statutory proof of dispatching legal notice to drawer''s correct address within 30 days of return memo.',
 'Original postal receipts issued by India Post booking office showing date and recipient postal code.', NULL, 5),
(25, 'India Post Official Consignment Tracking Delivery Report', 'Postal Record', TRUE,
 'Conclusive proof of service or deemed service (refusal/intimation) of legal demand notice upon opposite party.',
 'Internet consignment tracking report downloaded from indiapost.gov.in showing date and status of item delivery.', NULL, 6),
(25, 'Notice before Suit against Government / Public Officer under Section 80 CPC (if applicable)', 'Notice', FALSE,
 'Mandatory 2 months advance notice prior to instituting civil suit against government or public officer.',
 'Drafted specifying plaintiff cause of action, relief claimed, and delivered to Secretary or District Collector.', 8022, 7);

COMMIT;
