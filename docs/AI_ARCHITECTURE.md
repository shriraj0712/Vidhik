# VIDHIK AI — Intelligence Architecture & Capabilities

## 1. Overview & System Philosophy

**VIDHIK AI** is an Indian legal-tech intelligence backend built around deterministic statutory grounding, zero hallucination, strict PII privacy, and verifiable legal citations.

The core philosophy ensures that all legal classifications, rights evaluations, emergency escalations, and statutory references are anchored in authentic Indian law (Bharatiya Nyaya Sanhita, Bharatiya Nagarik Suraksha Sanhita, Bharatiya Sakshya Adhiniyam, Constitution of India, Motor Vehicles Act, Consumer Protection Act, RTI Act, etc.) rather than relying solely on unbounded generative LLM outputs.

---

## 2. Core AI Subsystems & Routing

```
                              [ User Query / Document / Speech ]
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │ AI Safety Filter │ (Prompt injection, jailbreak, PII, forgery)
                                    └─────────┬────────┘
                                              │ (If Safe)
                                              ▼
                                  ┌──────────────────────┐
                                  │ Emergency Interceptor│ (112, 1091, 1098, 1930, 15100)
                                  └───────────┬──────────┘
                                              │
                                              ▼
                                     ┌─────────────────┐
                                     │  Intent Router  │
                                     └────────┬────────┘
                                              │
        ┌───────────────────┬─────────────────┼───────────────────┬──────────────────┐
        ▼                   ▼                 ▼                   ▼                  ▼
┌───────────────┐   ┌───────────────┐ ┌───────────────┐   ┌───────────────┐  ┌───────────────┐
│ Constitutional│   │ Traffic Legal │ │ Authority Rec │   │ Statutory     │  │ Grounded RAG  │
│ Rights Engine │   │ Engine (MVA)  │ │ Intelligence  │   │ Elements      │  │ & Assistant   │
└───────────────┘   └───────────────┘ └───────────────┘   └───────────────┘  └───────────────┘
```

---

## 3. Subsystem Breakdown

### 3.1. AI Safety Guardrails (`AISafetyService`)
- **Location**: `backend/app/services/ai_safety_service.py`, `backend/app/routers/ai_safety.py`
- **Endpoints**: `POST /api/safety/check`, `GET /api/safety/health`
- **Capabilities**:
  - Detects prompt injection, jailbreak, and system prompt exfiltration attempts.
  - Blocks requests to fabricate false evidence, forged receipts, medical certificates, or bogus witnesses.
  - Rejects police evasion, evidence destruction, and bribery advice.
  - Detects and redacts sensitive Indian PII (Aadhaar numbers, PAN cards, Credit Cards, Bank Accounts, Phone numbers, Emails).

### 3.2. Legal Issue Classifier (`LegalClassifierService`)
- **Location**: `backend/app/services/legal_classifier_service.py`, `backend/app/routers/legal_classifier.py`
- **Endpoints**: `POST /api/classifier/classify`, `GET /api/classifier/health`
- **Capabilities**:
  - Deterministic taxonomy mapping across 12+ domains: Criminal, Civil, Family, Property, Consumer, Cyber, Labour, Constitutional, Traffic, RTI, Tenancy, Financial Fraud.
  - Native multilingual support for English, Hindi, and Marathi terminology.
  - Computes confidence scores and flags ambiguous/insufficient narratives.

### 3.3. Intent Router (`IntentRouterService`)
- **Location**: `backend/app/services/intent_router_service.py`, `backend/app/routers/intent_router.py`
- **Endpoints**: `POST /api/intent/route`, `GET /api/intent/health`
- **Capabilities**:
  - Deterministically routes user queries to specialized micro-engines (FIR generator, complaint generator, emergency interceptor, resolution engine, traffic engine, constitutional rights engine, RAG assistant).

### 3.4. Emergency Interceptor (`EmergencyInterceptorService`)
- **Location**: `backend/app/services/emergency_service.py`, `backend/app/routers/emergency.py`
- **Endpoints**: `POST /api/emergency/intercept`, `GET /api/emergency/helplines`, `GET /api/emergency/health`
- **Capabilities**:
  - Escalates immediate physical danger, domestic violence in progress, child endangerment, cyber financial fraud (within golden hour), and imminent unlawful arrest.
  - Supplies verified government helplines: **112** (All Emergency), **1091** (Women in Distress), **1098** (Childline), **1930** (Cyber Crime), **15100** (NALSA Free Legal Aid).

### 3.5. Statutory Element Verification (`ElementVerificationService`)
- **Location**: `backend/app/services/element_verification_service.py`, `backend/app/routers/element_verification.py`
- **Endpoints**: `POST /api/elements/verify`, `GET /api/elements/health`
- **Capabilities**:
  - Cross-references user factual narratives against statutory prerequisites (Theft, Cheating/Fraud, Criminal Intimidation, Cheque Bounce, Cyber Impersonation).
  - Categorizes status into `supported`, `partially_supported`, `insufficient_facts`, `not_supported`.
  - Enforces explicit non-adjudication and non-guilt disclaimers.

### 3.6. Constitutional Rights Engine (`ConstitutionalService`)
- **Location**: `backend/app/services/constitutional_service.py`, `backend/app/routers/constitutional.py`
- **Endpoints**: `POST /api/constitutional/analyze`, `GET /api/constitutional/rights`, `GET /api/constitutional/health`
- **Capabilities**:
  - Grounds inquiries in Part III Fundamental Rights (Articles 14, 19, 21, 21A, 22, 300A).
  - Identifies public authority state action and recommends prerogative writ remedies (Articles 32 and 226) including Habeas Corpus and Mandamus.

### 3.7. Traffic Legal Engine (`TrafficService`)
- **Location**: `backend/app/services/traffic_service.py`, `backend/app/routers/traffic.py`
- **Endpoints**: `POST /api/traffic/analyze`, `GET /api/traffic/offences`, `GET /api/traffic/health`
- **Capabilities**:
  - Grounds violations in the Motor Vehicles Act, 1988 (as amended by Act 32 of 2019).
  - Provides statutory penalties for helmet offences (194D), seatbelts (194B), speeding (183), signal jumping (184), drunk driving (185), uninsured driving (196), and PUC violations (190(2)).
  - Details dispute workflows through the National e-Challan Portal and Virtual Courts.

### 3.8. Authority Recommendation Intelligence (`AuthorityService`)
- **Location**: `backend/app/services/authority_service.py`, `backend/app/routers/authority.py`
- **Endpoints**: `POST /api/authority/recommend`, `GET /api/authority/domains`, `GET /api/authority/health`
- **Capabilities**:
  - Recommends verified statutory bodies (Police, Cyber Cell, DCDRC/SCDRC Consumer Commissions, RTI PIO/FAA/CIC, Labour Commissioners, RERA, DLSA Legal Services Authorities).
  - Provides official portal URLs, statutory enabling sections, and step-by-step statutory escalation hierarchies.

### 3.9. AI Legal Assistant & Streaming Chat (`LegalAssistantService`)
- **Location**: `backend/app/services/assistant_service.py`, `backend/app/routers/assistant.py`
- **Endpoints**: `POST /api/assistant/chat`, `POST /api/assistant/chat/stream`, `GET /api/assistant/health`
- **Capabilities**:
  - Full multi-turn conversational legal assistant with in-memory bounded LRU session persistence.
  - Pre-execution safety audit and emergency notice prefixing.
  - Server-Sent Events (SSE) streaming support via `StreamingResponse`.

### 3.10. Voice / STT Backend Abstraction (`VoiceService`)
- **Location**: `backend/app/services/voice_service.py`, `backend/app/routers/voice.py`
- **Endpoints**: `POST /api/voice/transcribe`, `GET /api/voice/status`, `GET /api/voice/health`
- **Capabilities**:
  - Provides extensible STT adapter contract supporting English (en-IN), Hindi (hi-IN), and Marathi (mr-IN).
  - Unconfigured provider gracefully returns explicit standby status without fabricating speech transcriptions.

### 3.11. AI Quality & Diagnostic Suite (`AIEvaluationService`)
- **Location**: `backend/app/services/ai_evaluation_service.py`, `backend/app/routers/ai_evaluation.py`
- **Endpoints**: `GET /api/ai-evaluation/run-suite`, `GET /api/ai-evaluation/health`
- **Capabilities**:
  - Automated continuous validation benchmark verifying 10 core AI subsystems in real-time with sub-50ms latency.

---

## 4. LLM Providers & Provider Support

The system adheres to `BaseLLMProvider` in `backend/app/services/llm_provider.py`:
1. **Google Gemini**: Gemini 2.5 Flash / Gemini 1.5 Pro using direct REST calls with zero external client libraries.
2. **OpenAI**: OpenAI GPT-4o-mini / GPT-4o compatibility.
3. **Offline Deterministic Fallback (`OfflineMockLLMProvider`)**: Offline statutory synthesizer used in local test suites and offline environments when no API keys are present.

### Ollama Verification Note
A comprehensive audit across all repository commits confirmed **zero** historical or active references to Ollama. The VIDHIK architecture uses direct REST adapters for Gemini and OpenAI with offline deterministic fallback.
