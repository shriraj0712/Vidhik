import re
import time
from typing import List, Dict, Any, Optional, Tuple
from app.schemas.ai_safety import SafetyCheckRequest, SafetyCheckResponse, SafetyViolation


class AISafetyService:
    """
    Centralized, deterministic safety and guardrail verification service for VIDHIK AI.
    Scans inputs and outputs for prompt injections, jailbreaks, malicious legal generation,
    fabricated evidence/witnesses, police evasion, evidence destruction, coercion, and PII.
    """

    # Prompt Injection & Jailbreak Patterns
    PROMPT_INJECTION_PATTERNS = [
        (r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)", "ignore_instructions"),
        (r"disregard\s+(all\s+)?(previous|prior|system)\s+(instructions|directives)", "disregard_instructions"),
        (r"forget\s+(all\s+)?(previous|prior)\s+rules", "forget_rules"),
        (r"(reveal|show|print|output|display|leak)\s+(your\s+)?(system\s+prompt|initial\s+instructions|system\s+instructions|developer\s+prompt)", "system_prompt_extraction"),
        (r"you\s+are\s+now\s+(in\s+)?(developer\s+mode|unrestricted\s+mode|dan\s+mode|god\s+mode|jailbroken)", "jailbreak_developer_mode"),
        (r"act\s+as\s+an\s+unfiltered|act\s+as\s+dan|do\s+anything\s+now", "dan_jailbreak"),
        (r"bypass\s+(safety|content|ethical)\s+filters", "filter_bypass"),
        (r"<\|im_start\|>|<\|im_end\|>|\[SYSTEM\]|\[INST\]", "delimiter_injection"),
    ]

    # Fabricated Evidence / Forgery Patterns
    FABRICATION_PATTERNS = [
        (r"(create|draft|generate|forge|make)\s+(a\s+)?(fake|forged|fraudulent|bogus|counterfeit)\s+(bill|receipt|invoice|signature|stamp|medical\s+certificate|document|affidavit|agreement|will|cheque)", "fabricated_document"),
        (r"(invent|make\s+up|fabricate|create)\s+(a\s+)?(fake|false|bogus)\s+(witness|testimony|statement|alibi)", "fabricated_witness"),
        (r"how\s+to\s+(forge|fake)\s+(signatures?|stamps?|notary\s+seal|government\s+seal)", "forgery_guidance"),
        (r"(plant|manufacture|fake)\s+(evidence|proof|weapon|drugs)", "fabricating_evidence"),
    ]

    # Police Evasion / Obstructing Justice / Evidence Destruction
    OBSTRUCTION_PATTERNS = [
        (r"how\s+to\s+(escape|evade|flee|hide\s+from)\s+(police|arrest|warrant|cops|authorities)", "police_evasion"),
        (r"how\s+to\s+(bribe|pay\s+off)\s+(police|judge|officer|constable|magistrate)", "bribery"),
        (r"bribe\s+(the\s+)?(constable|police|officer|judge|magistrate)", "bribery"),
        (r"how\s+to\s+(destroy|erase|delete|wipe|burn)\s+(evidence|cctv|records|documents|weapon)\s+(before|during)?\s*(police|investigation|raid)?", "evidence_destruction"),
        (r"how\s+to\s+(smuggle|hide|launder)\s+(contraband|black\s+money|illicit\s+funds)", "illicit_activity"),
    ]

    # Coercion / Threat / Extortion Patterns
    COERCION_PATTERNS = [
        (r"(draft|write|create)\s+(a\s+)?.*(threatening|blackmail|extortion).*(letter|notice|message|demand)", "threat_extortion"),
        (r"how\s+to\s+(blackmail|extort|intimidate|coerce)\s+(someone|a\s+witness|victim)", "intimidation"),
        (r"\b(blackmail\s+letter|extortion\s+letter|threatening\s+letter)\b", "coercion_document")
    ]

    # PII Regular Expressions
    PII_PATTERNS = [
        (r"\b[2-9]{1}[0-9]{3}\s?[0-9]{4}\s?[0-9]{4}\b", "aadhaar_number"),
        (r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", "pan_number"),
        (r"\b(?:\d{4}[ -]?){3}\d{4}\b", "credit_card_number"),
        (r"\b\d{9,18}\b", "bank_account_number"),
        (r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b", "email_address"),
        (r"\b(?:\+91|91)?[-.\s]?[6-9]\d{9}\b", "phone_number"),
    ]

    @classmethod
    def audit_text(cls, request: SafetyCheckRequest) -> SafetyCheckResponse:
        start_time = time.time()
        text = request.text
        violations: List[SafetyViolation] = []
        
        # 1. Check Prompt Injections
        for pattern, tag in cls.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(SafetyViolation(
                    category="prompt_injection",
                    description=f"Prompt injection or system manipulation pattern detected ({tag}).",
                    severity="high",
                    matched_patterns=[tag]
                ))

        # 2. Check Fabrications / Forgery
        for pattern, tag in cls.FABRICATION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(SafetyViolation(
                    category="fabrication_or_forgery",
                    description=f"Attempt to fabricate evidence, witnesses, or forged legal documents ({tag}).",
                    severity="critical",
                    matched_patterns=[tag]
                ))

        # 3. Check Police Evasion / Evidence Destruction
        for pattern, tag in cls.OBSTRUCTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(SafetyViolation(
                    category="obstruction_of_justice",
                    description=f"Attempt to evade law enforcement, destroy evidence, or bribe officials ({tag}).",
                    severity="critical",
                    matched_patterns=[tag]
                ))

        # 4. Check Coercion / Extortion
        for pattern, tag in cls.COERCION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(SafetyViolation(
                    category="coercion_or_extortion",
                    description=f"Attempt to generate blackmail, extortion, or threatening content ({tag}).",
                    severity="high",
                    matched_patterns=[tag]
                ))

        # 5. Check PII
        detected_pii_tags = []
        sanitized_text = text
        for pattern, tag in cls.PII_PATTERNS:
            if tag in ["email_address", "phone_number"]:
                matches = list(re.finditer(pattern, sanitized_text))
                if matches:
                    detected_pii_tags.append(tag)
                    sanitized_text = re.sub(pattern, f"[{tag.upper()}_REDACTED]", sanitized_text)
            else:
                matches = list(re.finditer(pattern, sanitized_text))
                if matches:
                    detected_pii_tags.append(tag)
                    sanitized_text = re.sub(pattern, f"[{tag.upper()}_REDACTED]", sanitized_text)
                    if request.strict_mode and tag in ["aadhaar_number", "credit_card_number"]:
                        violations.append(SafetyViolation(
                            category="sensitive_pii_exposure",
                            description=f"Sensitive identifier detected ({tag}).",
                            severity="medium",
                            matched_patterns=[tag]
                        ))

        is_safe = len(violations) == 0
        risk_level = "safe"
        blocked_reason = None

        if not is_safe:
            severities = [v.severity for v in violations]
            if "critical" in severities:
                risk_level = "critical"
                blocked_reason = "Request violates legal ethics and Indian statutory safety policies (unlawful assistance or evidence manipulation)."
            elif "high" in severities:
                risk_level = "high"
                blocked_reason = "Request contains disallowed adversarial manipulation or coercion instructions."
            else:
                risk_level = "medium"
                blocked_reason = "Request contains sensitive personal data requiring redaction."

        latency_ms = round((time.time() - start_time) * 1000, 2)

        return SafetyCheckResponse(
            is_safe=is_safe,
            risk_level=risk_level,
            violations=violations,
            contains_pii=len(detected_pii_tags) > 0,
            sanitized_text=sanitized_text if len(detected_pii_tags) > 0 else None,
            blocked_reason=blocked_reason,
            metadata={
                "latency_ms": latency_ms,
                "detected_pii_types": list(set(detected_pii_tags)),
                "strict_mode": request.strict_mode,
            }
        )

    @classmethod
    def sanitize_for_logging(cls, text: str) -> str:
        if not text:
            return ""
        sanitized = text
        for pattern, tag in cls.PII_PATTERNS:
            sanitized = re.sub(pattern, f"[{tag.upper()}_REDACTED]", sanitized)
        return sanitized
