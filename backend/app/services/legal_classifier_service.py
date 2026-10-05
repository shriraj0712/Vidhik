import re
import time
from typing import List, Dict, Any, Tuple
from app.schemas.legal_classifier import LegalClassificationRequest, LegalClassificationResponse, AreaScore


class LegalClassifierService:
    """
    Deterministic multilingual Legal Issue Classifier.
    Maps factual narratives and legal questions to established Indian legal domains,
    identifying relevant Bare Acts, confidence levels, and ambiguity flags.
    """

    DOMAINS_CONFIG = {
        "criminal": {
            "keywords": [
                "fir", "police", "arrest", "theft", "robbery", "murder", "assault", "bail", "bns", "ipc", "crpc",
                "bnss", "cheating", "fraud", "extortion", "kidnap", "threat", "dowry", "domestic violence", "custody",
                "चोरी", "खून", "मारहाण", "पोलीस", "तक्रार", "जामीन", "धमकी", "दरोडा", "हत्या", "गिरफ्तारी", "जमानत", "धोखाधड़ी"
            ],
            "acts": ["Bharatiya Nyaya Sanhita, 2023", "Bharatiya Nagarik Suraksha Sanhita, 2023", "Bharatiya Sakshya Adhiniyam, 2023"]
        },
        "cyber": {
            "keywords": [
                "cyber", "hacked", "phishing", "otp", "online fraud", "data leak", "unauthorized access", "social media fake profile",
                "it act", "cyber cell", "identity theft", "1930", "सायबर", "हॅक", "ऑनलाइन फसवणूक", "ओटीपी", "सायबर क्राईम"
            ],
            "acts": ["Information Technology Act, 2000", "Digital Personal Data Protection Act, 2023", "Bharatiya Nyaya Sanhita, 2023"]
        },
        "consumer": {
            "keywords": [
                "consumer", "defective product", "refund", "warranty", "ecommerce", "unfair trade practice", "deficiency in service",
                "consumer court", "dcdrc", "scdrc", "ncdrc", "refrigerator", "mobile phone defect", "flight refund",
                "ग्राहक", "ग्राहक मंच", "परतावा", "वस्तू खराब", "दोषी सेवा", "उपभोक्ता", "रिफंड", "वारंटी"
            ],
            "acts": ["Consumer Protection Act, 2019"]
        },
        "traffic": {
            "keywords": [
                "traffic", "challan", "e-challan", "fine", "speeding", "signal jumping", "helmet", "seatbelt", "driving licence",
                "rc", "puc", "motor vehicle", "mva", "drunk driving", "वाहतूक", "चलन", "दंड", "हेल्मेट", "परवाना", "ट्रैफिक", "चालान"
            ],
            "acts": ["Motor Vehicles Act, 1988"]
        },
        "rti": {
            "keywords": [
                "rti", "right to information", "pio", "first appellate", "information commissioner", "public authority", "section 6",
                "माहिती अधिकार", "माहिती", "अर्ज", "जन माहिती अधिकारी", "सूचना का अधिकार"
            ],
            "acts": ["Right to Information Act, 2005"]
        },
        "labour": {
            "keywords": [
                "labour", "employment", "termination", "salary unpaid", "wages", "gratuity", "provident fund", "pf", "workplace harassment",
                "factory", "workman", "overtime", "unpaid salary", "कामगार", "पगार", "नोकरी", "कामावरून काढले", "वेतन", "मजदूर", "भविष्य निधि"
            ],
            "acts": ["Industrial Disputes Act, 1947", "Payment of Gratuity Act, 1972", "Code on Wages, 2019"]
        },
        "property": {
            "keywords": [
                "property", "land", "encroachment", "registry", "title deed", "partition", "ancestral property", "sale deed",
                "mutation", "patta", "survey number", "stamp duty", "जमीन", "मालमत्ता", "वारसा", "खरेदीखत", "सातबारा", "संपत्ति", "कब्जा"
            ],
            "acts": ["Transfer of Property Act, 1882", "Registration Act, 1908", "Specific Relief Act, 1963"]
        },
        "tenancy": {
            "keywords": [
                "tenant", "landlord", "rent", "eviction", "security deposit", "lease agreement", "rent agreement", "unlawful eviction",
                "भाडेकरू", "घरमालक", "भाडे", "डिपॉझिट", "किरायेदार", "मकान मालिक", "किराया"
            ],
            "acts": ["Transfer of Property Act, 1882", "Model Tenancy Act / State Rent Control Acts"]
        },
        "family": {
            "keywords": [
                "divorce", "maintenance", "alimony", "child custody", "marriage", "matrimonial", "hindu marriage act", "special marriage act",
                "restitution", "domestic violence", "घटस्फोट", "पोटगी", "लग्नाचे वाद", "मुलांचा ताबा", "तलाक", "गुजारा भत्ता", "विवाह"
            ],
            "acts": ["Hindu Marriage Act, 1955", "Special Marriage Act, 1954", "Protection of Women from Domestic Violence Act, 2005"]
        },
        "constitutional": {
            "keywords": [
                "fundamental right", "constitution", "article 14", "article 19", "article 21", "article 32", "article 226", "writ",
                "habeas corpus", "mandamus", "discrimination", "freedom of speech", "arbitrary state action",
                "मूलभूत हक्क", "संविधान", "भेदभाव", "मौलिक अधिकार", "संविधान"
            ],
            "acts": ["Constitution of India"]
        },
        "financial_fraud": {
            "keywords": [
                "cheque bounce", "section 138", "ni act", "loan recovery", "harassment by recovery agents", "ponzi", "chit fund", "bank fraud",
                "धनादेश", "चेक बाउंस", "कर्ज वसुली", "धोका", "चेक अनादर", "बैंक धोखाधड़ी"
            ],
            "acts": ["Negotiable Instruments Act, 1881", "Bharatiya Nyaya Sanhita, 2023", "SARFAESI Act, 2002"]
        },
        "civil": {
            "keywords": [
                "contract", "breach of agreement", "injunction", "damages", "money recovery", "cpc", "specific performance",
                "करार", "नुकसानभरपाई", "दावा", "दिवाणी", "अनुबंध", "सिविल दावा"
            ],
            "acts": ["Indian Contract Act, 1872", "Code of Civil Procedure, 1908", "Specific Relief Act, 1963"]
        }
    }

    @classmethod
    def classify(cls, request: LegalClassificationRequest) -> LegalClassificationResponse:
        start_time = time.time()
        query_clean = request.query.strip().lower()

        # Handle very short or trivial queries
        if len(query_clean.split()) < 3 and len(query_clean) < 15:
            return LegalClassificationResponse(
                category="other",
                confidence=0.1,
                matched_terms=[],
                possible_legal_areas=[],
                requires_more_information=True,
                explanation="The input is too brief to definitively classify into a specific legal domain. Please provide more factual details.",
                candidate_acts=[],
                metadata={"latency_ms": round((time.time() - start_time) * 1000, 2), "query_length": len(query_clean)}
            )

        area_scores: List[AreaScore] = []

        for category, config in cls.DOMAINS_CONFIG.items():
            matched = []
            for kw in config["keywords"]:
                pattern = r"\b" + re.escape(kw) + r"\b" if re.match(r"^[a-zA-Z0-9_\s]+$", kw) else re.escape(kw)
                if re.search(pattern, query_clean):
                    matched.append(kw)
            
            if matched:
                # Score based on number of matches with ceiling at 1.0
                score = min(1.0, round(0.4 + (len(matched) * 0.2), 2))
                area_scores.append(AreaScore(
                    category=category,
                    score=score,
                    matched_terms=matched,
                    applicable_acts=config["acts"]
                ))

        # Sort areas descending by score
        area_scores.sort(key=lambda x: x.score, reverse=True)

        if not area_scores:
            return LegalClassificationResponse(
                category="other",
                confidence=0.2,
                matched_terms=[],
                possible_legal_areas=[],
                requires_more_information=True,
                explanation="No strong domain-specific statutory keywords were detected. The matter may involve general legal principles or require additional facts.",
                candidate_acts=["Constitution of India", "Bharatiya Nyaya Sanhita, 2023", "Code of Civil Procedure, 1908"],
                metadata={"latency_ms": round((time.time() - start_time) * 1000, 2)}
            )

        top_area = area_scores[0]
        # Ambiguity check: if top 2 have almost identical score and score < 0.6
        requires_more_info = False
        if top_area.score < 0.5:
            requires_more_info = True

        explanation = f"Classified primarily under '{top_area.category}' based on detected terms: {', '.join(top_area.matched_terms[:5])}."
        if len(area_scores) > 1 and area_scores[1].score >= 0.5:
            explanation += f" Related domain detected: '{area_scores[1].category}'."

        latency_ms = round((time.time() - start_time) * 1000, 2)

        return LegalClassificationResponse(
            category=top_area.category,
            confidence=top_area.score,
            matched_terms=top_area.matched_terms,
            possible_legal_areas=area_scores,
            requires_more_information=requires_more_info,
            explanation=explanation,
            candidate_acts=top_area.applicable_acts,
            metadata={"latency_ms": latency_ms, "evaluated_categories": len(cls.DOMAINS_CONFIG)}
        )
