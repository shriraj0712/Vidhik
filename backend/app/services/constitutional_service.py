import re
import time
from typing import List, Dict, Any, Tuple
from app.schemas.constitutional import (
    ConstitutionalAnalysisRequest,
    ConstitutionalAnalysisResponse,
    ConstitutionalRightMatch
)


class ConstitutionalService:
    """
    Constitutional Rights Engine for VIDHIK AI.
    Grounds user narratives in Part III (Fundamental Rights) and Part IV-A/Articles 32 & 226 of the Constitution of India.
    """

    CONSTITUTIONAL_RIGHTS_DB = [
        {
            "article": "Article 14",
            "title": "Equality before Law & Equal Protection of the Laws",
            "category": "Right to Equality",
            "citizen_explanation": "Guarantees that the State shall not deny any person equality before the law or equal protection of laws within India, prohibiting arbitrary state action.",
            "patterns": [
                r"\b(discrimination|unequal treatment|arbitrary action|treated unfairly by government|bias by official|nepotism|reservation injustice)\b",
                r"\b(भेदभाव|असमान वागणूक|पक्षपात|सरकारी मनमानी)\b",
                r"\b(भेदभाव|असमानता|सरकारी पक्षपात)\b"
            ],
            "key_doctrines": ["Doctrine of Non-Arbitrariness (E.P. Royappa)", "Reasonable Classification Test"],
            "remedy": "Writ of Mandamus / Certiorari before High Court (Art. 226) or Supreme Court (Art. 32)"
        },
        {
            "article": "Article 19(1)(a)",
            "title": "Freedom of Speech and Expression",
            "category": "Right to Freedom",
            "citizen_explanation": "Protects the right to freely express views, opinions, journalistic reporting, peaceful dissent, and access to public information, subject only to reasonable restrictions under 19(2).",
            "patterns": [
                r"\b(freedom of speech|speech|expression|silenced|censorship|protest|banned.*protest|journalism|journalist|social media post|defamation gag order)\b",
                r"\b(भाषण स्वातंत्र्य|अभिव्यक्ती स्वातंत्र्य|पत्रकारिता बंदी|शांततापूर्ण आंदोलन)\b",
                r"\b(अभिव्यक्ति की स्वतंत्रता|आंदोलन पर रोक|पत्रकारिता)\b"
            ],
            "key_doctrines": ["Chilling Effect Doctrine", "Proportionality Test (Puttaswamy / Anuradha Bhasin)"],
            "remedy": "Writ of Mandamus / Quashing of Gag Orders under Article 226 / Article 32"
        },
        {
            "article": "Article 21",
            "title": "Protection of Life and Personal Liberty",
            "category": "Right to Life & Personal Liberty",
            "citizen_explanation": "Fundamental guarantee that no person shall be deprived of life or personal liberty except according to fair, just and reasonable procedure established by law. Encompasses privacy, dignity, speedy trial, and clean environment.",
            "patterns": [
                r"\b(right to life|privacy|wiretapping|phone tapped|illegal surveillance|clean environment|speedy trial|harassed in custody|dignity violated|right to livelihood)\b",
                r"\b(जीवनाचा अधिकार|गोपनीयतेचा हक्क|व्यक्तिगत स्वातंत्र्य|कस्टडीत छळ|मानवी हक्क)\b",
                r"\b(जीवन का अधिकार|निजता का अधिकार|हिरासत में प्रताड़ना)\b"
            ],
            "key_doctrines": ["Substantive Due Process (Maneka Gandhi)", "Right to Privacy (K.S. Puttaswamy)", "Right to Clean Environment (M.C. Mehta)"],
            "remedy": "Writ of Habeas Corpus / Mandamus under Article 32 (Supreme Court) or Article 226 (High Court)"
        },
        {
            "article": "Article 21A",
            "title": "Right to Free and Compulsory Education",
            "category": "Right to Education",
            "citizen_explanation": "Mandates the State to provide free and compulsory education to all children aged 6 to 14 years.",
            "patterns": [
                r"\b(denied school admission|rte quota|child expelled unfairly|free education right|school fees harassment)\b",
                r"\b(शाळेत प्रवेश नाकारला|मोफत शिक्षण|आरटीई कोटा)\b",
                r"\b(स्कूल में दाखिला नहीं|मुफ्त शिक्षा|आरटीई)\b"
            ],
            "key_doctrines": ["Universal Elementary Education Mandate (RTE Act, 2009)"],
            "remedy": "Complaint to State Commission for Protection of Child Rights (SCPCR) or Writ under Art. 226"
        },
        {
            "article": "Article 22",
            "title": "Protection Against Arbitrary Arrest and Detention",
            "category": "Arrest Safeguards",
            "citizen_explanation": "Provides mandatory safeguards upon arrest: right to be informed of grounds of arrest, right to consult and be defended by a legal practitioner, and mandatory production before a Magistrate within 24 hours.",
            "patterns": [
                r"\b(arrested\s+without\s+(reason|grounds)|without\s+grounds\s+of\s+arrest|denied\s+lawyer|custody\s+over\s+24\s+hours|24\s+hours\s+without|illegal\s+arrest|without\s+producing\s+before\s+magistrate|not\s+produced\s+before\s+magistrate|held\s+me\s+over\s+24\s+hours)\b",
                r"\b(अटकेचे कारण सांगितले नाही|वकील नाकारला|२४ तासांपेक्षा जास्त कोठडी|बेकायदेशीर अटक)\b",
                r"\b(बिना कारण गिरफ्तारी|वकील नहीं मिलने दिया|२४ घंटे से अधिक हिरासत)\b"
            ],
            "key_doctrines": ["D.K. Basu Guidelines on Arrest", "Arnesh Kumar Safeguards"],
            "remedy": "Writ of Habeas Corpus (Art. 226/32) and Bail Application under Section 480 BNSS / 437 CrPC"
        },
        {
            "article": "Article 32 & Article 226",
            "title": "Constitutional Remedies & Writs",
            "category": "Judicial Enforcement of Rights",
            "citizen_explanation": "Empowers citizens to approach the Supreme Court (Art. 32) and High Courts (Art. 226) directly through Prerogative Writs (Habeas Corpus, Mandamus, Prohibition, Quo Warranto, Certiorari) when fundamental rights are infringed.",
            "patterns": [
                r"\b(writ petition|habeas corpus|mandamus|certiorari|quo warranto|file in high court|file in supreme court|constitutional remedy)\b",
                r"\b(रिट याचिका|हेबियस कॉर्पस|मँडॅमस|उच्च न्यायालयात याचिका|सर्वोच्च न्यायालय)\b",
                r"\b(रिट याचिका|बंदी प्रत्यक्षीकरण|परमादेश|हाई कोर्ट याचिका)\b"
            ],
            "key_doctrines": ["Heart and Soul of the Constitution (Dr. B.R. Ambedkar)", "Basic Structure Doctrine (Kesavananda Bharati)"],
            "remedy": "Filing of Writ Petition under Article 226 before the jurisdictional High Court"
        },
        {
            "article": "Article 300A",
            "title": "Right to Property",
            "category": "Constitutional Property Protection",
            "citizen_explanation": "Guarantees that no citizen shall be deprived of their property save by authority of law, prohibiting arbitrary demolition or state land seizure without lawful compensation.",
            "patterns": [
                r"\b(demolished|demolition|bulldozer|land grabbed by authority|property seized unlawfully|unlawful acquisition)\b",
                r"\b(घरावर बुलडोझर|विना नोटीस पाडकाम|सरकारी जमीन बळकावणे|मालमत्ता जप्ती)\b",
                r"\b(बिना नोटिस मकान तोड़ा|अवैध कब्जा|जमीन अधिग्रहण)\b"
            ],
            "key_doctrines": ["Rule of Law against Arbitrary Demolitions (Supreme Court 2024 Guidelines)", "Fair Compensation (RFCTLARR Act)"],
            "remedy": "Writ Petition under Article 226 seeking Stay / Injunction against unlawful demolition"
        }
    ]

    STATE_ACTION_PATTERNS = [
        r"\b(police|collector|municipal corporation|government|ministry|psu|state|tehsildar|rto|electricity board|discom|public authority|panchayat)\b",
        r"\b(पोलीस|कलेक्टर|महानगरपालिका|शासकीय|प्रशासन|तहसीलदार|आरटीओ)\b",
        r"\b(पुलिस|कलेक्टर|नगर निगम|सरकारी|तहसीलदार)\b"
    ]

    @classmethod
    def analyze(cls, request: ConstitutionalAnalysisRequest) -> ConstitutionalAnalysisResponse:
        start_time = time.time()
        facts_clean = request.facts.strip().lower()

        # Check for state action / public authority context
        is_state_action = any(re.search(p, facts_clean, re.IGNORECASE) for p in cls.STATE_ACTION_PATTERNS)

        matched_rights: List[ConstitutionalRightMatch] = []
        recommended_remedies: List[str] = []

        for right in cls.CONSTITUTIONAL_RIGHTS_DB:
            is_matched = False
            for pattern in right["patterns"]:
                if re.search(pattern, facts_clean, re.IGNORECASE):
                    is_matched = True
                    break
            
            if is_matched:
                matched_rights.append(ConstitutionalRightMatch(
                    article=right["article"],
                    title=right["title"],
                    category=right["category"],
                    citizen_explanation=right["citizen_explanation"],
                    relevance_to_facts=f"Facts trigger protections under {right['article']} concerning {right['category'].lower()}.",
                    key_doctrines=right["key_doctrines"],
                    remedy_available=right["remedy"]
                ))
                if right["remedy"] not in recommended_remedies:
                    recommended_remedies.append(right["remedy"])

        # Fallback to Article 21 & Article 226 if state action is present but specific right wasn't explicitly matched
        if is_state_action and not matched_rights:
            art21 = cls.CONSTITUTIONAL_RIGHTS_DB[2] # Art 21
            matched_rights.append(ConstitutionalRightMatch(
                article=art21["article"],
                title=art21["title"],
                category=art21["category"],
                citizen_explanation=art21["citizen_explanation"],
                relevance_to_facts="General state action requires compliance with the fair and reasonable procedure of Article 21.",
                key_doctrines=art21["key_doctrines"],
                remedy_available=art21["remedy"]
            ))
            recommended_remedies.append(art21["remedy"])

        if matched_rights:
            summary = (
                f"Identified {len(matched_rights)} constitutional protection(s) potentially applicable: "
                f"{', '.join([r.article for r in matched_rights])}. "
                f"{'State action is detected, making Constitutional Writ remedies (Art. 226/32) viable.' if is_state_action else 'Note: Fundamental rights are primarily enforceable against State entities (Article 12).'}"
            )
        else:
            summary = "No clear Fundamental Rights infringement detected based on the narrative provided. If the dispute is between private individuals, ordinary civil/criminal law remedies apply."
            recommended_remedies.append("Standard statutory remedy (Civil Suit, Police Complaint, Consumer Forum)")

        return ConstitutionalAnalysisResponse(
            is_state_action_involved=is_state_action,
            primary_rights_engaged=matched_rights,
            recommended_remedies=recommended_remedies,
            summary_analysis=summary,
            metadata={"latency_ms": round((time.time() - start_time) * 1000, 2), "articles_scanned": len(cls.CONSTITUTIONAL_RIGHTS_DB)}
        )
