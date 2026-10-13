"""
Vidhik Platform - Legal Context Builder
=======================================
Transforms retrieved statutory candidates into structured, deduplicated,
and budget-constrained legal context blocks for grounded LLM inference.

Guarantees:
- Zero fabrication: Uses ground-truth text from the PostgreSQL database.
- Integrity: Retains exact statutory wording, parent statute, and page coordinates.
- Deduplication: Eliminates identical section provisions across duplicate candidate hits.
- Budget Control: Restricts total context size to prevent prompt overflow.
"""

from typing import List, Dict, Any, Tuple, Optional, Set
from app.schemas.rag import LegalSourceCitation, RetrievedSectionContext


class LegalContextBuilder:
    """
    Assembles authoritative legal context from ranked statutory candidate records.
    """

    DEFAULT_MAX_CONTEXT_CHARS = 10000
    DEFAULT_SECTION_TEXT_CAP = 3000

    @classmethod
    def build_context(
        cls,
        ranked_candidates: List[Dict[str, Any]],
        max_sections: int = 5,
        max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS
    ) -> Tuple[List[RetrievedSectionContext], List[LegalSourceCitation], str]:
        """
        Builds structured section objects, source citations, and formatted LLM context text.

        :param ranked_candidates: Deterministically ranked candidate dictionaries from PostgreSQL
        :param max_sections: Maximum number of provisions to package (1-20)
        :param max_context_chars: Maximum character budget for the statutory prompt context
        :return: Tuple of (retrieved_sections, source_citations, prompt_context_string)
        """
        retrieved_sections: List[RetrievedSectionContext] = []
        source_citations: List[LegalSourceCitation] = []
        prompt_blocks: List[str] = []

        seen_provisions: Set[Tuple[int, str]] = set()
        accumulated_chars = 0
        rank_counter = 1

        for cand in ranked_candidates:
            if len(retrieved_sections) >= max_sections:
                break

            law_id = int(cand.get("law_id") or 0)
            sec_num = str(cand.get("section_number") or "").strip()
            provision_key = (law_id, sec_num.lower())

            # 1. Deduplicate by parent Law ID and Section Number
            if provision_key in seen_provisions:
                continue
            seen_provisions.add(provision_key)

            # 2. Extract statutory text (prioritizing full_text, falling back to description)
            raw_text = (cand.get("full_text") or cand.get("description") or "").strip()
            if not raw_text:
                continue

            # 3. Cap excessively long individual provisions to prevent budget exhaustion
            is_truncated = False
            if len(raw_text) > cls.DEFAULT_SECTION_TEXT_CAP:
                is_truncated = True
                trimmed_text = (
                    raw_text[: cls.DEFAULT_SECTION_TEXT_CAP].rsplit(" ", 1)[0]
                    + "\n\n[NOTICE: This provision is lengthy and has been excerpted to preserve context budget. "
                    "Do not interpret this excerpt as the exhaustive statutory provision. Refer to the complete primary source document.]"
                )
            else:
                trimmed_text = raw_text

            # 4. Check global context budget
            formatted_entry_len = len(trimmed_text) + 200
            if accumulated_chars + formatted_entry_len > max_context_chars and retrieved_sections:
                # If budget exceeded and we already have at least one top-ranked section, stop
                break

            # 5. Extract metadata fields
            law_name = str(cand.get("law_name") or "Unknown Act").strip()
            raw_sec_id = cand.get("section_id")
            try:
                sec_id = int(raw_sec_id) if raw_sec_id is not None else 0
            except (ValueError, TypeError):
                sec_id = abs(hash(str(raw_sec_id))) % 1000000
            sec_title = (cand.get("section_title") or "").strip() or None
            sec_uid = (cand.get("section_uid") or "").strip() or None
            source_pdf = (cand.get("source_pdf") or "").strip() or None
            page_start = cand.get("source_page_start") or cand.get("page_start")
            page_end = cand.get("source_page_end") or cand.get("page_end")
            jurisdiction = (cand.get("jurisdiction") or "India").strip()
            relevance_exp = cand.get("_rank_explanation")

            # 6. Build Citation Model
            citation = LegalSourceCitation(
                law_id=law_id,
                law_name=law_name,
                section_id=sec_id,
                section_number=sec_num,
                section_title=sec_title,
                section_uid=sec_uid,
                source_pdf=source_pdf,
                source_page_start=int(page_start) if page_start is not None else None,
                source_page_end=int(page_end) if page_end is not None else None,
                jurisdiction=jurisdiction
            )
            source_citations.append(citation)

            # 7. Build RetrievedSectionContext Model
            section_ctx = RetrievedSectionContext(
                law_id=law_id,
                law_name=law_name,
                section_id=sec_id,
                section_number=sec_num,
                section_title=sec_title,
                section_text=trimmed_text,
                relevance_rank=rank_counter,
                relevance_explanation=relevance_exp,
                is_truncated=is_truncated,
                source=citation
            )
            retrieved_sections.append(section_ctx)

            # 8. Build Prompt Block for LLM Context
            page_str = ""
            if page_start is not None:
                page_str = f" (Pages {page_start}-{page_end})" if page_end and page_end != page_start else f" (Page {page_start})"

            pdf_info = f" [Source: {source_pdf}{page_str}]" if source_pdf else ""
            title_info = f" — {sec_title}" if sec_title else ""
            status_line = "\nStatus: [EXCERPTED PROVISION - DO NOT ASSUME EXHAUSTIVE]" if is_truncated else ""

            is_constitution = "constitution" in law_name.lower() or sec_num.lower().startswith("article")
            clean_num = sec_num.replace("Article", "").strip() if is_constitution else sec_num.replace("Section", "").strip()
            provision_label = f"Article {clean_num}" if is_constitution else f"Section {clean_num}"

            block = (
                f"[STATUTORY PROVISION #{rank_counter}{' (EXCERPTED)' if is_truncated else ''}]\n"
                f"Act: {law_name} ({jurisdiction})\n"
                f"Section: {provision_label}{title_info}{pdf_info}{status_line}\n"
                f"Text:\n{trimmed_text}"
            )
            prompt_blocks.append(block)

            accumulated_chars += len(block)
            rank_counter += 1

        prompt_context_string = "\n\n" + ("\n\n".join(prompt_blocks)) if prompt_blocks else ""

        return retrieved_sections, source_citations, prompt_context_string
