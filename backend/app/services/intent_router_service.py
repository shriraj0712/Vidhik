import re
import time
from typing import Dict, Any, List, Tuple
from app.schemas.intent_router import IntentRoutingRequest, IntentRoutingResponse


class IntentRouterService:
    """
    Deterministic Intent Router for VIDHIK AI.
    Routes incoming user interactions to the appropriate specialized legal engine or assistant service.
    """

    INTENT_CONFIG = [
        {
            "intent": "emergency",
            "service": "emergency_interceptor",
            "endpoint": "/api/emergency/intercept",
            "patterns": [
                r"\b(danger|immediate help|someone is attacking|being assaulted|kill me|suicide|save me|emergency|urgent police)\b",
                r"\b(जीव धोक्यात|तातडीने मदत|हल्ला|आत्महत्या|बचाव)\b",
                r"\b(खतरे में|तुरंत मदद|हमला|बचाओ)\b"
            ]
        },
        {
            "intent": "fir_generation",
            "service": "complaint_generator_service",
            "endpoint": "/api/complaints/generate",
            "patterns": [
                r"\b(draft\s+(an?\s+)?fir|generate\s+(an?\s+)?fir|write\s+(an?\s+)?fir|file\s+(an?\s+)?fir|sample fir|fir template|fir for|एफआयआर|प्राथमिकी)\b"
            ]
        },
        {
            "intent": "complaint_generation",
            "service": "complaint_generator_service",
            "endpoint": "/api/complaints/generate",
            "patterns": [
                r"\b(draft\s+(a\s+)?complaint|write\s+(a\s+)?complaint|file\s+(a\s+)?complaint|consumer complaint format|police complaint format|तक्रार अर्ज|शिकायत)\b"
            ]
        },
        {
            "intent": "traffic_issue",
            "service": "traffic_service",
            "endpoint": "/api/traffic/analyze",
            "patterns": [
                r"\b(traffic challan|e-challan|speeding fine|signal jumping|helmet|riding without helmet|seatbelt|driving licence penalty|mva section|ट्रॅफिक चलन|वाहतूक दंड)\b"
            ]
        },
        {
            "intent": "resolution_triage",
            "service": "resolution_service",
            "endpoint": "/api/resolution/evaluate",
            "patterns": [
                r"\b(do i need a lawyer|can i resolve myself|triage my legal issue|should i hire an advocate|legal triage|वकिलाची गरज आहे का|कायद्याचा सल्ला)\b"
            ]
        },
        {
            "intent": "constitutional_rights",
            "service": "constitutional_service",
            "endpoint": "/api/constitutional/analyze",
            "patterns": [
                r"\b(fundamental right|article 21|article 19|article 14|article 32|article 226|writ petition|right to life|freedom of speech|संविधान|मूलभूत हक्क)\b"
            ]
        },
        {
            "intent": "authority_recommendation",
            "service": "authority_service",
            "endpoint": "/api/authority/recommend",
            "patterns": [
                r"\b(where to report|which department|which authority|whom to complain|who handles this|योग्य प्राधिकरण|कुठे तक्रार करावी)\b"
            ]
        },
        {
            "intent": "document_analysis",
            "service": "document_analysis_service",
            "endpoint": "/api/document-analysis/analyze",
            "patterns": [
                r"\b(analyze document|review contract|review agreement|check agreement clauses|दस्तऐवज तपासणी|करार तपासणी)\b"
            ]
        },
        {
            "intent": "section_lookup",
            "service": "rag_service",
            "endpoint": "/api/rag/query",
            "patterns": [
                r"\b(section \d+|article \d+|कलम \d+|अनुच्छेद \d+|धारा \d+|bns section|ipc section)\b"
            ]
        },
        {
            "intent": "greeting",
            "service": "assistant_service",
            "endpoint": "/api/assistant/chat",
            "patterns": [
                r"^(hello|hi|hey|namaste|good morning|good evening|नमस्कार|प्रणाम)$"
            ]
        }
    ]

    @classmethod
    def route_intent(cls, request: IntentRoutingRequest) -> IntentRoutingResponse:
        start_time = time.time()
        query = request.query.strip().lower()

        for config in cls.INTENT_CONFIG:
            matched = []
            for pattern in config["patterns"]:
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    matched.append(match.group(0))
            if matched:
                return IntentRoutingResponse(
                    intent=config["intent"],
                    confidence=0.9,
                    suggested_target_service=config["service"],
                    suggested_api_endpoint=config["endpoint"],
                    matched_triggers=matched,
                    metadata={"latency_ms": round((time.time() - start_time) * 1000, 2)}
                )

        # Default fallback: General legal question handled by Legal Assistant / RAG
        return IntentRoutingResponse(
            intent="legal_question",
            confidence=0.6,
            suggested_target_service="assistant_service",
            suggested_api_endpoint="/api/assistant/chat",
            matched_triggers=[],
            metadata={"latency_ms": round((time.time() - start_time) * 1000, 2), "fallback": True}
        )
