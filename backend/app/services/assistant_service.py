"""
Vidhik Platform - AI Legal Assistant Service
=============================================
Orchestrates natural-language legal interactions:
- Sits on top of the Phase 9 Legal RAG engine (`LegalRAGService`)
- Manages conversational history and session continuity
- Resolves contextual follow-up inquiries deterministically
- Applies AI Safety Guardrails (`AISafetyService`) and Emergency Interception (`EmergencyInterceptorService`)
- Preserves statutory grounding, sources, citations, and telemetry
- Strictly avoids hallucination and enforces zero leakage of internal errors
- Supports full streaming chat synthesis
"""

import os
import re
import json
import uuid
import logging
import threading
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple, Iterator
from psycopg2.extras import RealDictCursor

from app.schemas.rag import (
    RAGQueryRequest,
    RAGResponse,
    LegalSourceCitation,
    RetrievedSectionContext,
    RetrievalMetadata
)
from app.schemas.assistant import (
    ChatMessage,
    AssistantChatRequest,
    AssistantChatResponse
)
from app.schemas.ai_safety import SafetyCheckRequest
from app.schemas.emergency import EmergencyEvaluationRequest
from app.services.ai_safety_service import AISafetyService
from app.services.emergency_service import EmergencyInterceptorService
from app.services.rag_service import LegalRAGService
from app.services.llm_provider import BaseLLMProvider, get_llm_provider

logger = logging.getLogger("vidhik.assistant_service")

# Mapping Devanagari numerals to ASCII
DEVANAGARI_DIGIT_MAP = str.maketrans("०१२३४५६७८९", "0123456789")


# ==============================================================================
# CONVERSATION STORE ABSTRACTION
# ==============================================================================

class BaseConversationStore(ABC):
    """
    Abstract contract for storing and retrieving conversation histories.
    """

    @abstractmethod
    def get_history(self, conversation_id: str) -> List[ChatMessage]:
        """Retrieve chronological history for a given conversation ID."""
        pass

    @abstractmethod
    def add_message(self, conversation_id: str, message: ChatMessage) -> None:
        """Append a message turn to the conversation history."""
        pass

    @abstractmethod
    def clear(self, conversation_id: str) -> None:
        """Clear conversation history for a given conversation ID."""
        pass


class InMemoryConversationStore(BaseConversationStore):
    """
    Thread-safe in-memory conversation store with automatic LRU-style eviction
    and per-session turn bounds to avoid unbounded memory expansion.
    """

    def __init__(self, max_conversations: int = 1000, max_turns_per_conversation: int = 20):
        self.max_conversations = max_conversations
        self.max_turns_per_conversation = max_turns_per_conversation
        self._store: Dict[str, List[ChatMessage]] = {}
        self._lock = threading.Lock()

    def get_history(self, conversation_id: str) -> List[ChatMessage]:
        with self._lock:
            history = self._store.get(conversation_id, [])
            return list(history)

    def add_message(self, conversation_id: str, message: ChatMessage) -> None:
        with self._lock:
            if conversation_id not in self._store:
                if len(self._store) >= self.max_conversations:
                    # Evict oldest conversation
                    oldest_id = next(iter(self._store))
                    del self._store[oldest_id]
                self._store[conversation_id] = []

            history = self._store[conversation_id]
            history.append(message)
            # Bound conversation turn length
            if len(history) > self.max_turns_per_conversation:
                self._store[conversation_id] = history[-self.max_turns_per_conversation:]

    def clear(self, conversation_id: str) -> None:
        with self._lock:
            self._store.pop(conversation_id, None)


# Default global in-memory conversation store
_global_conversation_store = InMemoryConversationStore()


def get_conversation_store() -> BaseConversationStore:
    """Returns the active conversation store instance."""
    return _global_conversation_store


# ==============================================================================
# CONTEXTUAL FOLLOW-UP HANDLER
# ==============================================================================

class ConversationContextHandler:
    """
    Resolves conversational follow-up questions by extracting statutory anchors
    (Section numbers, Article numbers, Act names, primary legal topics)
    from previous turns to enrich subsequent retrieval queries.
    """

    SECTION_REGEX = re.compile(
        r'(?:section|sec\.?|कलम|धारा)\s*([0-9०-९]+[A-Za-z\-]*)',
        re.IGNORECASE
    )
    ARTICLE_REGEX = re.compile(
        r'(?:article|art\.?|अनुच्छेद)\s*([0-9०-९]+[A-Za-z\-]*)',
        re.IGNORECASE
    )
    ORDER_RULE_REGEX = re.compile(
        r'(?:order|rule)\s*([0-9०-९]+[A-Za-z\-]*)',
        re.IGNORECASE
    )

    COMMON_ACTS = [
        "Indian Penal Code",
        "Code of Criminal Procedure",
        "Code of Civil Procedure",
        "Indian Contract Act",
        "Constitution of India",
        "Specific Relief Act",
        "Negotiable Instruments Act",
        "Arbitration and Conciliation Act",
        "Transfer of Property Act",
        "Evidence Act",
        "Bharatiya Nyaya Sanhita",
        "Bharatiya Nagarik Suraksha Sanhita",
        "Bharatiya Sakshya Adhiniyam",
        "भारतीय दंड संहिता",
        "भारतीय करार कायदा",
        "भारताचे संविधान",
        "फौजदारी प्रक्रिया संहिता"
    ]

    FOLLOW_UP_INDICATORS = {
        "it", "this", "that", "these", "those", "such", "the same",
        "he", "she", "they", "does it", "is it", "can it", "will it",
        "what about", "what is the punishment", "punishment", "penalty",
        "bailable", "non-bailable", "compoundable", "cognizable",
        "minor", "child", "applies to", "apply to", "exception", "exceptions",
        "procedure", "fine", "imprisonment", "appeal", "limitation",
        "हे", "या", "तो", "ती", "ते", "याची", "त्याची", "लागू", "शिक्षा", "दंड", "जामीन", "अल्पवयीन", "अपवाद",
        "यह", "इस", "इसकी", "सजा", "दंड", "जमानत", "नाबालिग", "लागू", "अपवाद"
    }

    @classmethod
    def is_follow_up(cls, message: str, history: List[ChatMessage]) -> bool:
        if not history:
            return False

        clean_msg = message.strip().lower()
        words = set(re.findall(r'\b\w+\b', clean_msg))

        has_section = bool(cls.SECTION_REGEX.search(message) or cls.ARTICLE_REGEX.search(message))
        has_act = any(act.lower() in clean_msg for act in cls.COMMON_ACTS)

        if has_section and len(words) >= 5:
            return False

        if not has_section and not has_act:
            if words.intersection(cls.FOLLOW_UP_INDICATORS):
                return True
            if len(words) <= 7:
                return True

        for indicator in cls.FOLLOW_UP_INDICATORS:
            if indicator in clean_msg:
                return True

        return False

    @classmethod
    def extract_legal_anchors(cls, history: List[ChatMessage]) -> Dict[str, List[str]]:
        sections: List[str] = []
        articles: List[str] = []
        acts: List[str] = []

        recent_history = history[-6:]
        for turn in reversed(recent_history):
            content = turn.content.translate(DEVANAGARI_DIGIT_MAP)

            for match in cls.SECTION_REGEX.finditer(content):
                sec_num = match.group(1).strip()
                if sec_num and sec_num not in sections:
                    sections.append(sec_num)

            for match in cls.ARTICLE_REGEX.finditer(content):
                art_num = match.group(1).strip()
                if art_num and art_num not in articles:
                    articles.append(art_num)

            for act in cls.COMMON_ACTS:
                if act.lower() in content.lower() and act not in acts:
                    acts.append(act)

        return {
            "sections": sections,
            "articles": articles,
            "acts": acts
        }

    @classmethod
    def resolve_query(cls, message: str, history: Optional[List[ChatMessage]]) -> str:
        clean_msg = message.strip()
        if not history:
            return clean_msg

        if not cls.is_follow_up(clean_msg, history):
            return clean_msg

        anchors = cls.extract_legal_anchors(history)
        sections = anchors.get("sections", [])
        articles = anchors.get("articles", [])
        acts = anchors.get("acts", [])

        anchor_parts: List[str] = []
        if sections:
            anchor_parts.append(f"Section {sections[0]}")
        elif articles:
            anchor_parts.append(f"Article {articles[0]}")

        if acts:
            anchor_parts.append(acts[0])

        if not anchor_parts:
            last_user_turn = next((t for t in reversed(history) if t.role == "user"), None)
            if last_user_turn:
                anchor_parts.append(last_user_turn.content.strip())

        if anchor_parts:
            context_prefix = " ".join(anchor_parts)
            if context_prefix.lower() not in clean_msg.lower():
                enriched_query = f"{context_prefix} {clean_msg}"
                logger.info(f"Contextualized follow-up query: '{clean_msg}' -> '{enriched_query}'")
                return enriched_query

        return clean_msg


# ==============================================================================
# LEGAL ASSISTANT SERVICE
# ==============================================================================

class LegalAssistantService:
    """
    Core AI Legal Assistant service orchestrating conversational legal questions
    on top of the existing Phase 9 Legal RAG system with safety and emergency guards.
    """

    DEFAULT_DISCLAIMER = (
        "This legal assistant provides informational and research support grounded in Indian statutory law "
        "from the Vidhik legal database. It does not constitute formal legal advice or substitute for consultation "
        "with a qualified legal professional."
    )

    @classmethod
    def chat(
        cls,
        db: RealDictCursor,
        request: AssistantChatRequest,
        provider: Optional[BaseLLMProvider] = None,
        store: Optional[BaseConversationStore] = None
    ) -> AssistantChatResponse:
        """
        Processes a conversational legal question from the user.
        """
        clean_message = request.message.strip()
        if not clean_message:
            raise ValueError("Message cannot be empty or whitespace only.")

        conversation_id = request.conversation_id or str(uuid.uuid4())
        active_store = store or get_conversation_store()

        # -------------------------------------------------------------
        # STEP 1: AI Safety Guardrails Interception
        # -------------------------------------------------------------
        safety_audit = AISafetyService.audit_text(SafetyCheckRequest(text=clean_message))
        if not safety_audit.is_safe and safety_audit.risk_level in ["critical", "high"]:
            refusal_text = (
                f"I cannot fulfill this request. {safety_audit.blocked_reason or 'The inquiry violates legal safety and ethics policies.'} "
                "VIDHIK AI assists strictly with lawful legal research, rights education, and procedural guidance."
            )
            return AssistantChatResponse(
                conversation_id=conversation_id,
                message=clean_message,
                answer=refusal_text,
                language=request.language or "en",
                grounding_status="safety_refusal",
                confidence="low",
                is_grounded=False,
                sources=[],
                retrieved_sections=[],
                retrieval_metadata=RetrievalMetadata(
                    total_candidates_found=0,
                    sections_used=0,
                    query_terms_matched=[],
                    concept_categories=[],
                    multilingual_synonyms_applied=[],
                    retrieval_strategy="safety_refusal"
                ),
                disclaimer=cls.DEFAULT_DISCLAIMER
            )

        # -------------------------------------------------------------
        # STEP 2: Emergency Interception
        # -------------------------------------------------------------
        emergency_eval = EmergencyInterceptorService.evaluate(
            EmergencyEvaluationRequest(text=clean_message, language=request.language or "en")
        )
        emergency_prefix = ""
        if emergency_eval.is_emergency and emergency_eval.escalation_message:
            emergency_prefix = f"⚠️ **URGENT EMERGENCY NOTICE:**\n{emergency_eval.escalation_message}\n\n---\n\n"

        # -------------------------------------------------------------
        # STEP 3: History & Context Resolution
        # -------------------------------------------------------------
        if request.history is not None:
            effective_history = request.history[-10:] if len(request.history) > 10 else list(request.history)
        else:
            effective_history = active_store.get_history(conversation_id)
            if len(effective_history) > 10:
                effective_history = effective_history[-10:]

        contextualized_query = ConversationContextHandler.resolve_query(
            message=clean_message,
            history=effective_history
        )

        # -------------------------------------------------------------
        # STEP 4: Delegate to Phase 9 Legal RAG Service
        # -------------------------------------------------------------
        rag_request = RAGQueryRequest(
            query=contextualized_query,
            language=request.language or "en",
            jurisdiction=request.jurisdiction,
            law_id=request.law_id,
            max_sections=request.max_sections or 5,
            temperature=(
                request.temperature
                if request.temperature is not None
                else 0.1
            )
        )

        rag_response: RAGResponse = LegalRAGService.query(
            db=db,
            request=rag_request,
            provider=provider
        )

        final_answer = emergency_prefix + rag_response.answer

        # -------------------------------------------------------------
        # STEP 5: Record Turn in Conversation History
        # -------------------------------------------------------------
        try:
            user_msg = ChatMessage(role="user", content=clean_message)
            assistant_msg = ChatMessage(role="assistant", content=final_answer)
            active_store.add_message(conversation_id, user_msg)
            active_store.add_message(conversation_id, assistant_msg)
        except Exception as e:
            logger.warning(f"Could not persist conversation turn for session {conversation_id}: {e}")

        # -------------------------------------------------------------
        # STEP 6: Return Grounded Response
        # -------------------------------------------------------------
        return AssistantChatResponse(
            conversation_id=conversation_id,
            message=clean_message,
            answer=final_answer,
            language=rag_response.language,
            grounding_status=rag_response.confidence,
            confidence=rag_response.confidence,
            is_grounded=rag_response.is_grounded,
            sources=rag_response.sources,
            retrieved_sections=rag_response.retrieved_sections,
            retrieval_metadata=rag_response.retrieval_metadata,
            disclaimer=cls.DEFAULT_DISCLAIMER
        )

    @classmethod
    def chat_stream(
        cls,
        db: RealDictCursor,
        request: AssistantChatRequest,
        provider: Optional[BaseLLMProvider] = None,
        store: Optional[BaseConversationStore] = None
    ) -> Iterator[str]:
        """
        Streams assistant response tokens as SSE formatted events.
        """
        response = cls.chat(db=db, request=request, provider=provider, store=store)
        
        # Stream metadata header event
        yield f"event: metadata\ndata: {json.dumps({'conversation_id': response.conversation_id, 'is_grounded': response.is_grounded, 'sources_count': len(response.sources)})}\n\n"

        # Stream answer chunks
        words = response.answer.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield f"event: message\ndata: {json.dumps({'delta': chunk})}\n\n"

        # Stream done event
        yield f"event: done\ndata: [DONE]\n\n"
