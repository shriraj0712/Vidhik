"""
Vidhik Platform - AI Legal Assistant Service
=============================================
Orchestrates natural-language legal interactions for Phase 10:
- Sits on top of the Phase 9 Legal RAG engine (`LegalRAGService`)
- Manages conversational history and session continuity
- Resolves contextual follow-up inquiries deterministically
- Preserves statutory grounding, sources, citations, and telemetry
- Strictly avoids hallucination and enforces zero leakage of internal errors
"""

import os
import re
import uuid
import logging
import threading
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple
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
    Allows pluggable persistence (In-Memory, Redis, PostgreSQL, DynamoDB).
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

    # Patterns matching statutory section references in English, Marathi, and Hindi
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

    # Common Act mentions frequently queried
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
        "भारतीय दंड संहिता",
        "भारतीय करार कायदा",
        "भारताचे संविधान",
        "फौजदारी प्रक्रिया संहिता"
    ]

    # Referential tokens suggesting a follow-up question
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
        """
        Determines whether the given message is a follow-up referencing prior context.
        """
        if not history:
            return False

        clean_msg = message.strip().lower()
        words = set(re.findall(r'\b\w+\b', clean_msg))

        # Check if user message explicitly specifies a statutory provision (Section, Article, Act)
        has_section = bool(cls.SECTION_REGEX.search(message) or cls.ARTICLE_REGEX.search(message))
        has_act = any(act.lower() in clean_msg for act in cls.COMMON_ACTS)

        # If user explicitly specifies both Act/Section and a complete query, it is self-contained
        if has_section and len(words) >= 5:
            return False

        # If user has no section/act and contains follow-up indicator keywords
        if not has_section and not has_act:
            if words.intersection(cls.FOLLOW_UP_INDICATORS):
                return True
            # Short question fragment (< 8 words) following an earlier turn
            if len(words) <= 7:
                return True

        # Check for phrase-level follow-up cues
        for indicator in cls.FOLLOW_UP_INDICATORS:
            if indicator in clean_msg:
                return True

        return False

    @classmethod
    def extract_legal_anchors(cls, history: List[ChatMessage]) -> Dict[str, List[str]]:
        """
        Extracts statutory anchors (sections, articles, acts) from recent conversation history.
        Scans from newest to oldest message.
        """
        sections: List[str] = []
        articles: List[str] = []
        acts: List[str] = []

        # Look back up to last 6 messages
        recent_history = history[-6:]
        for turn in reversed(recent_history):
            content = turn.content.translate(DEVANAGARI_DIGIT_MAP)

            # Extract sections
            for match in cls.SECTION_REGEX.finditer(content):
                sec_num = match.group(1).strip()
                if sec_num and sec_num not in sections:
                    sections.append(sec_num)

            # Extract articles
            for match in cls.ARTICLE_REGEX.finditer(content):
                art_num = match.group(1).strip()
                if art_num and art_num not in articles:
                    articles.append(art_num)

            # Extract acts
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
        """
        Enriches a follow-up query with statutory anchors from conversation history.
        If the message is self-contained or no history exists, returns the original query.
        """
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
            # Fallback: extract primary subject from last user question
            last_user_turn = next((t for t in reversed(history) if t.role == "user"), None)
            if last_user_turn:
                anchor_parts.append(last_user_turn.content.strip())

        if anchor_parts:
            context_prefix = " ".join(anchor_parts)
            # Avoid repeating the anchor if already in clean_msg
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
    on top of the existing Phase 9 Legal RAG system.
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

        1. Validates and manages conversation ID and session history.
        2. Contextualizes follow-up questions using prior conversation turns.
        3. Delegates legal retrieval and grounded synthesis to Phase 9 `LegalRAGService`.
        4. Preserves statutory grounding, sources, citations, and telemetry.
        5. Records the turn in the conversation store.

        :param db: RealDictCursor PostgreSQL connection dependency
        :param request: Validated AssistantChatRequest
        :param provider: Optional LLM provider instance (defaults to environment provider)
        :param store: Optional conversation store instance (defaults to in-memory store)
        :return: Grounded AssistantChatResponse
        """
        clean_message = request.message.strip()
        if not clean_message:
            raise ValueError("Message cannot be empty or whitespace only.")

        # -------------------------------------------------------------
        # STEP 1: Conversation & Session Resolution
        # -------------------------------------------------------------
        conversation_id = request.conversation_id or str(uuid.uuid4())
        active_store = store or get_conversation_store()

        # Determine effective history:
        # Client-supplied history takes precedence (stateless mode).
        # Otherwise, load history from session store.
        if request.history is not None:
            # Bound context size: take at most the last 10 messages
            effective_history = request.history[-10:] if len(request.history) > 10 else list(request.history)
        else:
            effective_history = active_store.get_history(conversation_id)
            if len(effective_history) > 10:
                effective_history = effective_history[-10:]

        # -------------------------------------------------------------
        # STEP 2: Contextual Follow-Up Query Resolution
        # -------------------------------------------------------------
        contextualized_query = ConversationContextHandler.resolve_query(
            message=clean_message,
            history=effective_history
        )

        # -------------------------------------------------------------
        # STEP 2.5: Video Evidence Context Resolution
        # -------------------------------------------------------------
        evidence_observations: Optional[List[Dict[str, Any]]] = None
        evidence_transcripts: Optional[List[Dict[str, Any]]] = None
        evidence_context_text = ""
        evidence_title: Optional[str] = None

        if request.evidence_id:
            try:
                db.execute("SELECT * FROM video_evidence WHERE evidence_id = %s;", (request.evidence_id,))
                ev_row = db.fetchone()
                if ev_row:
                    evidence_title = f"Video Evidence #{request.evidence_id} ({ev_row['original_filename']})"

                    db.execute("SELECT * FROM video_visual_observations WHERE evidence_id = %s ORDER BY timestamp_seconds ASC;", (request.evidence_id,))
                    obs_rows = db.fetchall()
                    evidence_observations = [
                        {
                            "timestamp_seconds": float(o["timestamp_seconds"]),
                            "time_formatted": f"{int(float(o['timestamp_seconds']) // 60):02d}:{int(float(o['timestamp_seconds']) % 60):02d}",
                            "category": o["category"],
                            "observation": o["neutral_observation"],
                            "visible_marks": o.get("visible_physical_marks"),
                            "limitations": o.get("uncertainty_or_limitation")
                        }
                        for o in obs_rows
                    ]

                    db.execute("SELECT * FROM video_transcripts WHERE evidence_id = %s ORDER BY start_time ASC;", (request.evidence_id,))
                    tr_rows = db.fetchall()
                    evidence_transcripts = [
                        {
                            "start_time": float(t["start_time"]),
                            "end_time": float(t["end_time"]),
                            "time_formatted": f"{int(float(t['start_time']) // 60):02d}:{int(float(t['start_time']) % 60):02d}",
                            "text": t["text"],
                            "speaker": t.get("speaker")
                        }
                        for t in tr_rows
                    ]

                    # Build structured evidence context
                    lines = [
                        f"=== VERIFIED DIGITAL VIDEO EVIDENCE CONTEXT (EVD-{request.evidence_id}) ===",
                        f"File: {ev_row['original_filename']} | Duration: {float(ev_row.get('duration_seconds') or 0):.1f}s | SHA-256: {ev_row.get('file_hash_sha256')}",
                        f"Format: {str(ev_row.get('media_container', '')).upper()} | Resolution: {ev_row.get('resolution')} | Audio Present: {ev_row.get('has_audio')}",
                        "\n--- OBSERVED VISUAL EVENTS (SAMPLED FRAMES) ---"
                    ]
                    if evidence_observations:
                        for o in evidence_observations:
                            lines.append(f"- [{o['time_formatted']}] {o['observation']}")
                            if o.get("visible_marks"):
                                lines.append(f"  * Observable Mark: {o['visible_marks']}")
                    else:
                        lines.append("No sampled visual events recorded.")

                    lines.append("\n--- MACHINE-GENERATED AUDIO TRANSCRIPT ---")
                    if evidence_transcripts:
                        for t in evidence_transcripts:
                            spk = f" ({t['speaker']})" if t.get("speaker") else ""
                            lines.append(f"- [{t['time_formatted']}] \"{t['text']}\"{spk}")
                    else:
                        if not ev_row.get("has_audio"):
                            lines.append("Recording contains no audio stream.")
                        else:
                            lines.append("No machine transcript available.")

                    lines.append("\n=== STATUTORY EVIDENTIARY GUIDANCE ===")
                    lines.append("Under Bharatiya Sakshya Adhiniyam, 2023 (BSA Section 63), electronic evidence requires preservation of original media and section 63 certification.")
                    lines.append("[End of Video Evidence Context]\n")

                    evidence_context_text = "\n".join(lines)
            except Exception as e:
                logger.warning(f"Could not load evidence context for evidence_id={request.evidence_id}: {e}")

        # Combine document / evidence context
        effective_doc_text = request.document_text or ""
        if evidence_context_text:
            effective_doc_text = (
                f"{evidence_context_text}\n\n{effective_doc_text}".strip()
                if effective_doc_text
                else evidence_context_text
            )
        effective_doc_title = request.document_title or evidence_title

        # -------------------------------------------------------------
        # STEP 3: Delegate to Existing Phase 9 Legal RAG Service
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
            ),
            document_text=effective_doc_text if effective_doc_text else None,
            document_title=effective_doc_title
        )

        rag_response: RAGResponse = LegalRAGService.query(
            db=db,
            request=rag_request,
            provider=provider
        )

        # -------------------------------------------------------------
        # STEP 4: Record Turn in Conversation History
        # -------------------------------------------------------------
        try:
            user_msg = ChatMessage(role="user", content=clean_message)
            assistant_msg = ChatMessage(role="assistant", content=rag_response.answer)
            active_store.add_message(conversation_id, user_msg)
            active_store.add_message(conversation_id, assistant_msg)
        except Exception as e:
            logger.warning(f"Could not persist conversation turn for session {conversation_id}: {e}")

        # -------------------------------------------------------------
        # STEP 5: Format and Return Grounded Assistant Response
        # -------------------------------------------------------------
        return AssistantChatResponse(
            conversation_id=conversation_id,
            message=clean_message,
            answer=rag_response.answer,
            language=rag_response.language,
            grounding_status=rag_response.confidence,
            confidence=rag_response.confidence,
            is_grounded=rag_response.is_grounded,
            sources=rag_response.sources,
            retrieved_sections=rag_response.retrieved_sections,
            retrieval_metadata=rag_response.retrieval_metadata,
            evidence_id=request.evidence_id,
            evidence_observations=evidence_observations,
            evidence_transcripts=evidence_transcripts,
            disclaimer=cls.DEFAULT_DISCLAIMER
        )
