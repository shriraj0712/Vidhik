"""
Vidhik Platform - Legal RAG Service
===================================
End-to-end orchestration service for Phase 9 Grounded Legal Retrieval & QA.

Architecture & Flow:
1. Reuses existing LegalSearchService.retrieve_ranked_candidates():
   - Executes query understanding & multilingual terminology expansion via LegalQueryService
   - Performs parameterized candidate retrieval across statutory provisions
   - Executes 10-tier deterministic relevance ranking via LegalRankingService
2. Deduplicated Statutory Context & Source Packaging (LegalContextBuilder)
3. Grounded Synthesis via Modular LLM Provider (BaseLLMProvider)
4. Robust error handling and strict state separation between retrieved context and synthesis status
"""

import os
import re
import logging
import uuid
from typing import Optional, List, Dict, Any, Tuple
from psycopg2.extras import RealDictCursor

from app.schemas.rag import (
    RAGQueryRequest,
    RAGResponse,
    RetrievalMetadata,
    RetrievedSectionContext,
    LegalSourceCitation
)
from app.services.search_service import LegalSearchService
from app.services.context_builder import LegalContextBuilder
from app.services.llm_provider import (
    BaseLLMProvider,
    LLMProviderConfigurationError,
    LLMProviderError,
    get_llm_provider,
)

logger = logging.getLogger("vidhik.rag_service")


class GroundingValidationError(ValueError):
    """Generated text is empty, uncited, or cites a provision not retrieved."""


def _validate_generated_citations(
    answer: str,
    retrieved_sections: List[RetrievedSectionContext],
) -> set:
    """Require explicit citations and reject article/section numbers outside context."""
    if not isinstance(answer, str) or not answer.strip():
        raise GroundingValidationError("empty_output")

    allowed = set()
    for section in retrieved_sections:
        match = re.search(r"\b(Article|Section)\s+([0-9]+[a-z]?)\b", section.section_number, re.I)
        if match:
            allowed.add((match.group(1).lower(), match.group(2).lower()))
        else:
            kind = "article" if "constitution" in section.law_name.lower() else "section"
            number = re.search(r"([0-9]+[a-z]?)", section.section_number, re.I)
            if number:
                allowed.add((kind, number.group(1).lower()))

    normalized_answer = answer.translate(str.maketrans("०१२३४५६७८९", "0123456789"))
    citation_matches = re.finditer(
        r"\b(Articles?|Sections?|अनुच्छेद|कलम|धारा)\s+"
        r"([0-9]+[a-z]?(?:(?:\s*(?:,|and|to|-)\s*)[0-9]+[a-z]?)*)",
        normalized_answer,
        re.I,
    )
    cited = []
    for match in citation_matches:
        kind = match.group(1).lower().rstrip("s")
        translated_kind = {"अनुच्छेद": "article", "कलम": "section", "धारा": "section"}.get(kind, kind)
        numbers = re.findall(r"[0-9]+[a-z]?", match.group(2), re.I)
        if re.search(r"\b(?:to|-)\b", match.group(2), re.I) and len(numbers) == 2 and numbers[0].isdigit() and numbers[1].isdigit():
            first, last = map(int, numbers)
            numbers = [str(number) for number in range(first, min(last, first + 25) + 1)]
        cited.extend((translated_kind, number.lower()) for number in numbers)
    if not cited:
        raise GroundingValidationError("missing_citation")
    if any(citation not in allowed for citation in cited):
        raise GroundingValidationError("citation_not_retrieved")
    return set(cited)


def _validate_fundamental_rights_overview(answer: str, cited: set) -> None:
    """Require all six categories and their retrieved representative citations."""
    normalized = answer.lower()
    if re.search(
        r"\b(?:comprehensive|exhaustive)\b"
        r"|\b(?:complete|full)\s+(?:list|overview|coverage|account|summary)\b"
        r"|\b(?:all|every)\s+(?:the\s+)?(?:fundamental\s+)?rights\b",
        normalized,
    ):
        raise GroundingValidationError("non_exhaustive_claim")

    category_requirements = (
        ("equality", {("article", "14")}),
        ("freedom", {("article", "19")}),
        ("exploitation", {("article", "23"), ("article", "24")}),
        ("religion", {("article", "25")}),
        ("cultural and educational", {("article", "29"), ("article", "30")}),
        ("remedies", {("article", "32")}),
    )
    for label, citation_options in category_requirements:
        if label not in normalized:
            raise GroundingValidationError("fundamental_rights_category_omitted")
        required_citations = citation_options
        if label == "exploitation":
            if not cited.intersection(required_citations):
                raise GroundingValidationError("fundamental_rights_category_uncited")
        elif not required_citations.issubset(cited):
            raise GroundingValidationError("fundamental_rights_category_uncited")


SYSTEM_LEGAL_INSTRUCTION = """You are VIDHIK AI, an authoritative, high-precision legal research intelligence assistant for Indian Statutory Law.

YOUR CORE MANDATES:
1. STRICT STATUTORY GROUNDING: Base your legal explanations exclusively on the provided [STATUTORY PROVISIONS] retrieved from the official database.
2. EXPLICIT CITATIONS: For every legal principle, duty, penalty, or rule you mention, explicitly cite the exact Act name and Section number (e.g. "Under Section 73 of the Indian Contract Act, 1872...").
3. ZERO HALLUCINATION: Never fabricate, assume, or extrapolate legal provisions, case laws, sections, penalties, or statutory dates that are not explicitly present in the provided text.
4. INSUFFICIENT CONTEXT: If the retrieved provisions do not directly answer the user's specific scenario or question, explicitly acknowledge this limitation. Do not attempt to guess.
5. PROFESSIONAL CLARITY: Present legal provisions clearly, breaking down elements, conditions, and penalties where applicable.
6. MANDATORY DISCLAIMER: Maintain neutrality; provide research guidance rather than definitive personal legal representation.
7. TRUNCATED / EXCERPTED PROVISIONS: If a retrieved statutory provision is marked as '(EXCERPTED)' or contains a truncation disclaimer, you MUST NOT treat it as the complete statutory provision. If your answer depends on details that may fall outside the excerpt, explicitly state that the provision has been excerpted and refer to the complete primary statute.
"""


class LegalRAGService:
    """
    Orchestrates grounded legal question answering by fusing existing deterministic
    statutory search infrastructure with modular LLM synthesis.
    """

    @classmethod
    def query(
        cls,
        db: RealDictCursor,
        request: RAGQueryRequest,
        provider: Optional[BaseLLMProvider] = None
    ) -> RAGResponse:
        """
        Executes an end-to-end grounded legal query.

        :param db: RealDictCursor database cursor dependency
        :param request: Validated RAGQueryRequest
        :param provider: Optional LLM provider instance (defaults to get_llm_provider())
        :return: Grounded RAGResponse containing answer, citations, and telemetry
        """
        clean_q = request.query.strip()
        lang = (request.language or "en").lower().strip()
        if lang not in ("en", "mr", "hi"):
            lang = "en"
        is_broad_fundamental_rights_query = bool(
            re.search(r"\b(?:fundamental|constitutional)\s+rights?\b", clean_q, re.I)
        )
        requested_sections = request.max_sections or 8
        context_section_limit = max(requested_sections, 8) if is_broad_fundamental_rights_query else requested_sections

        # -------------------------------------------------------------
        # STEP 1: Candidate Retrieval & Ranking via Existing Search Infrastructure
        # (Reuses LegalSearchService.retrieve_ranked_candidates which encapsulates
        # LegalQueryService multilingual matching, search SQL, and LegalRankingService)
        # -------------------------------------------------------------
        candidate_pool_limit = max(context_section_limit * 5, 50)
        ranked_candidates, total_candidates, query_analysis = LegalSearchService.retrieve_ranked_candidates(
            db=db,
            query=clean_q,
            limit=candidate_pool_limit,
            offset=0,
            law_id=request.law_id,
            jurisdiction=request.jurisdiction
        )

        matched_term_ids = [t.term_id for t in query_analysis.matched_terms]
        concept_categories = [c.category for c in query_analysis.matched_concepts]
        multilingual_synonyms: List[str] = []
        for s in query_analysis.matched_synonyms:
            multilingual_synonyms.extend(s.synonyms_mr + s.synonyms_hi)

        # -------------------------------------------------------------
        # STEP 2: Handle No-Result / Zero Database Matches
        # -------------------------------------------------------------
        if total_candidates == 0:
            no_match_text = {
                "en": (
                    "No relevant statutory provisions were found in the Vidhik legal database for your query. "
                    "To ensure strict legal accuracy and prevent hallucination, no hypothetical or speculative legal rules have been generated."
                ),
                "mr": (
                    "आपल्या प्रश्नाशी संबंधित कोणतीही वैधानिक कलमे विधिक डेटाबेसमध्ये आढळली नाहीत. "
                    "कायदेशीर अचूकता राखण्यासाठी आणि कल्पित माहिती टाळण्यासाठी, कोणतेही संभाव्य उत्तर तयार करण्यात आलेले नाही."
                ),
                "hi": (
                    "आपके प्रश्न से संबंधित कोई भी वैधानिक प्रावधान विधिक डेटाबेस में नहीं मिले। "
                    "कानूनी सटीकता बनाए रखने और भ्रामक जानकारी से बचने के लिए, कोई काल्पनिक उत्तर उत्पन्न नहीं किया गया है।"
                )
            }.get(lang, "No relevant statutory provisions were found in the database.")

            return RAGResponse(
                query=clean_q,
                language=lang,
                answer=no_match_text,
                confidence="no_context",
                is_grounded=False,
                sources=[],
                retrieved_sections=[],
                retrieval_metadata=RetrievalMetadata(
                    total_candidates_found=0,
                    sections_used=0,
                    query_terms_matched=matched_term_ids,
                    concept_categories=concept_categories,
                    multilingual_synonyms_applied=multilingual_synonyms,
                    retrieval_strategy="deterministic_lexicon_ranked"
                )
            )

        # -------------------------------------------------------------
        # STEP 3: Build Structured Statutory Context & Source Citations
        # -------------------------------------------------------------
        retrieved_sections, source_citations, prompt_context_str = LegalContextBuilder.build_context(
            ranked_candidates=ranked_candidates,
            max_sections=context_section_limit,
            max_context_chars=6000
        )

        if not retrieved_sections or not prompt_context_str.strip():
            return RAGResponse(
                query=clean_q,
                language=lang,
                answer="Statutory sections were located in the index, but their text content was insufficient to construct verified legal context.",
                confidence="insufficient_context",
                is_grounded=False,
                sources=source_citations,
                retrieved_sections=retrieved_sections,
                retrieval_metadata=RetrievalMetadata(
                    total_candidates_found=total_candidates,
                    sections_used=0,
                    query_terms_matched=matched_term_ids,
                    concept_categories=concept_categories,
                    multilingual_synonyms_applied=multilingual_synonyms,
                    retrieval_strategy="deterministic_lexicon_ranked"
                )
            )

        # -------------------------------------------------------------
        # STEP 4: Execute Grounded Generation via LLM Provider
        # -------------------------------------------------------------
        language_instruction = {
            "en": "Generate the answer in clear, professional English.",
            "mr": "कृपया खालील कायदेशीर संदर्भाचा आधार घेऊन उत्तर स्पष्ट मराठीत द्या. कलमे आणि कायदे अचूक नमूद करा.",
            "hi": "कृपया निम्नलिखित कानूनी संदर्भ के आधार पर उत्तर स्पष्ट हिंदी में दें। धाराओं और अधिनियमों का सटीक उल्लेख करें।"
        }.get(lang, "Generate the answer in English.")

        doc_context_str = ""
        if request.document_text and request.document_text.strip():
            doc_title = request.document_title or "Uploaded Legal Document / Notice / Evidence"
            doc_context_str = (
                f"\n=== USER UPLOADED DOCUMENT CONTEXT ({doc_title}) ===\n"
                f"{request.document_text.strip()[:6000]}\n"
                f"[End of Uploaded Document Context]\n\n"
            )

        user_prompt = (
            f"LEGAL QUESTION:\n{clean_q}\n\n"
            f"LANGUAGE INSTRUCTION:\n{language_instruction}\n\n"
            f"{doc_context_str}"
            f"=== RETRIEVED STATUTORY PROVISIONS ===\n"
            f"{prompt_context_str}\n\n"
            f"=== INSTRUCTIONS ===\n"
            f"Synthesize a factual, grounded explanation addressing the legal question above based strictly on these statutory provisions and any uploaded document context.\n"
            f"Structure your response logically:\n"
            f"1. Direct Answer First: Give a clear, straightforward answer to the user's situation.\n"
            f"2. Applicable Law & Sections: Explicitly cite the governing Act and Section / Article numbers.\n"
            f"3. Plain Legal Explanation: Break down the legal rights, remedies, procedures, or offences in plain language.\n"
            f"4. Important Conditions & Safeguards: Mention key exceptions, prerequisites, or procedural conditions.\n"
            f"5. Actionable Next Steps: Provide practical guidance on what the person should do.\n"
            f"For a general question about Fundamental Rights, explain the six categories: equality, freedom, protection against exploitation, freedom of religion, cultural and educational rights, and constitutional remedies. Cite only retrieved Articles that support each category; use Articles 23 and 24 for exploitation, and Articles 29 and 30 for cultural and educational rights when retrieved; state when retrieved support is insufficient. Treat these as representative provisions and state that the overview is not exhaustive; do not imply every right, limitation, or exception is covered.\n"
            f"Never hallucinate or fabricate sections, articles, penalties, or procedures."
        )

        synthesis_succeeded = True
        correlation_id = uuid.uuid4().hex
        active_provider: Optional[BaseLLMProvider] = None
        try:
            # Provider construction can fail on missing/invalid deployment config;
            # treat it as synthesis failure so retrieved authorities remain usable.
            active_provider = provider or get_llm_provider()
            generated_answer = active_provider.generate(
                prompt=user_prompt,
                system_instruction=SYSTEM_LEGAL_INSTRUCTION,
                temperature=request.temperature or 0.1
            )
            generated_citations = _validate_generated_citations(generated_answer, retrieved_sections)
            if is_broad_fundamental_rights_query:
                _validate_fundamental_rights_overview(generated_answer, generated_citations)
        except Exception as e:
            failure_category = (
                e.failure_category if isinstance(e, (LLMProviderError, LLMProviderConfigurationError)) else (
                    "grounding_validation" if isinstance(e, GroundingValidationError) else "provider_error"
                )
            )
            http_status = e.http_status if isinstance(e, LLMProviderError) else None
            logger.error(
                "LLM synthesis failed (provider=%s, failure_category=%s, error_type=%s, http_status=%s, correlation_id=%s).",
                active_provider.provider_name if active_provider else "unavailable",
                failure_category,
                type(e).__name__,
                http_status,
                correlation_id
            )
            synthesis_succeeded = False
            
            # Safe generic user-facing message (no raw exception or stack trace leakage)
            fail_text = {
                "en": (
                    "Authoritative statutory provisions were successfully retrieved from the Vidhik legal database; "
                    "however, automated AI synthesis could not be completed at this time. "
                    "The authoritative statutory provisions and official citations are provided below for direct legal review."
                ),
                "mr": (
                    "विधिक डेटाबेसमधून संबंधित कायदेशीर कलमे यशस्वीरीत्या शोधली गेली आहेत; तथापि, एआय संश्लेषण प्रक्रिया सध्या पूर्ण होऊ शकली नाही. "
                    "खाली दिलेली अधिकृत कलमे आणि संदर्भ थेट अभ्यासासाठी उपलब्ध आहेत."
                ),
                "hi": (
                    "विधिक डेटाबेस से संबंधित कानूनी प्रावधान सफलतापूर्वक प्राप्त किए गए हैं; हालांकि, एआई संश्लेषण वर्तमान में पूरा नहीं हो सका। "
                    "प्रत्यक्ष समीक्षा के लिए प्रामाणिक धाराएं और संदर्भ नीचे दिए गए हैं।"
                )
            }.get(lang, "Authoritative statutory provisions were retrieved, but automated synthesis failed.")
            source_lines = [
                f"- {section.law_name}, {section.section_number}"
                + (f" — {section.section_title}" if section.section_title else "")
                for section in retrieved_sections
            ]
            generated_answer = fail_text + (
                "\n\nRetrieved authoritative provisions:\n" + "\n".join(source_lines)
                if source_lines else "\n\nNo authoritative provision text was available to cite."
            )

        # -------------------------------------------------------------
        # STEP 5: Final Response Packaging
        # Strict distinction between retrieved context found and synthesis status
        # -------------------------------------------------------------
        if synthesis_succeeded:
            top_tier = ranked_candidates[0].get("_rank_tuple", (10,))[0] if ranked_candidates else 10
            confidence = "grounded_high" if top_tier <= 5 else "grounded_medium"
            is_grounded = True
        else:
            # AI synthesis failed: is_grounded must NOT be true, but retrieved sources remain intact
            confidence = "synthesis_failed"
            is_grounded = False

        return RAGResponse(
            query=clean_q,
            language=lang,
            answer=generated_answer,
            confidence=confidence,
            is_grounded=is_grounded,
            sources=source_citations,
            retrieved_sections=retrieved_sections,
            retrieval_metadata=RetrievalMetadata(
                total_candidates_found=total_candidates,
                sections_used=len(retrieved_sections),
                query_terms_matched=matched_term_ids,
                concept_categories=concept_categories,
                multilingual_synonyms_applied=multilingual_synonyms,
                retrieval_strategy="deterministic_lexicon_ranked"
            )
        )
