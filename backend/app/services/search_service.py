"""
Vidhik Platform - Legal Search Service
======================================
Dedicated service layer for executing read-only, parameterized multi-field
legal text searches across statutory laws and provisions with deterministic
relevance ranking and query understanding integration.
"""

from typing import Optional, List, Any
from psycopg2.extras import RealDictCursor

from app.schemas.search import SearchResponse, SearchResultItem
from app.services.query_service import LegalQueryService, STOPWORDS
from app.services.ranking_service import LegalRankingService


class LegalSearchService:
    """
    Service encapsulating business logic, SQL query generation, snippet
    extraction, query understanding, and deterministic relevance ranking
    for Indian statutory legal search.
    """

    @staticmethod
    def extract_snippet(
        full_text: Optional[str],
        description: Optional[str],
        section_title: Optional[str],
        law_name: Optional[str],
        query: str,
        max_length: int = 240
    ) -> Optional[str]:
        """
        Extracts a readable contextual snippet around the search query match
        without altering, fabricating, or modifying statutory legal text.

        :param full_text: Complete text of the statutory section
        :param description: High-level section description or summary
        :param section_title: Title or heading of the section
        :param law_name: Title/name of the parent statutory act
        :param query: Raw search query string
        :param max_length: Maximum character length for fallback snippets
        :return: Extracted snippet string with contextual ellipsis, or None
        """
        clean_q = query.strip()
        if not clean_q:
            return None

        candidates = [
            (full_text, True),
            (description, True),
            (section_title, False),
            (law_name, False),
        ]

        q_lower = clean_q.lower()

        # 1. Look for direct match in candidate texts (prioritizing full_text, description)
        for text, _ in candidates:
            if text and q_lower in text.lower():
                text_clean = " ".join(text.split())
                idx = text_clean.lower().find(q_lower)
                if idx != -1:
                    start = max(0, idx - 60)
                    end = min(len(text_clean), idx + len(clean_q) + 160)

                    # Align to nearest word boundary
                    if start > 0:
                        space_idx = text_clean.find(" ", start)
                        if space_idx != -1 and space_idx < idx:
                            start = space_idx + 1
                    if end < len(text_clean):
                        space_idx = text_clean.rfind(" ", idx + len(clean_q), end)
                        if space_idx != -1:
                            end = space_idx

                    snippet = text_clean[start:end].strip()
                    if start > 0:
                        snippet = "... " + snippet
                    if end < len(text_clean):
                        snippet = snippet + " ..."
                    return snippet

        # 2. Fallback: if match was on metadata (e.g. section_number), return primary text excerpt
        for text, _ in candidates:
            if text:
                text_clean = " ".join(text.split())
                if len(text_clean) <= max_length:
                    return text_clean
                end = max_length
                space_idx = text_clean.rfind(" ", 0, end)
                if space_idx != -1 and space_idx > 50:
                    end = space_idx
                return text_clean[:end].strip() + " ..."

        return None

    @classmethod
    def search(
        cls,
        db: RealDictCursor,
        query: str,
        limit: int = 10,
        offset: int = 0,
        law_id: Optional[int] = None,
        jurisdiction: Optional[str] = None
    ) -> SearchResponse:
        """
        Executes a safe, parameterized multi-field ILIKE candidate search against
        `laws` and `sections`, integrating LegalQueryService for query analysis
        and LegalRankingService for deterministic relevance ranking.

        :param db: RealDictCursor database cursor dependency
        :param query: Required search query string
        :param limit: Maximum number of records to return (1-50)
        :param offset: Number of records to skip
        :param law_id: Optional filter by parent Law ID
        :param jurisdiction: Optional filter by jurisdiction name
        :return: SearchResponse containing pagination metadata and deterministically ranked results
        """
        clean_q = query.strip()
        if not clean_q:
            return SearchResponse(
                query=query,
                total=0,
                limit=limit,
                offset=offset,
                results=[]
            )

        # 1. Query Understanding & Statutory Terminology Analysis
        query_analysis = LegalQueryService.analyze_query(db, clean_q)

        # 2. Candidate Retrieval Conditions
        search_phrases = [clean_q]
        for t in query_analysis.matched_terms:
            if t.term_en and t.term_en.lower() != clean_q.lower():
                search_phrases.append(t.term_en)

        conditions: List[str] = []
        params: List[Any] = []

        # Phrase-based multi-field matching
        for sp in search_phrases:
            search_param = f"%{sp}%"
            conditions.append(
                "(l.law_name ILIKE %s OR l.short_name ILIKE %s OR s.section_number ILIKE %s OR s.section_title ILIKE %s OR s.description ILIKE %s OR s.full_text ILIKE %s)"
            )
            params.extend([search_param] * 6)

        # Multi-token conjunctive fallback for multi-word queries
        q_tokens = LegalQueryService.clean_tokens(clean_q)
        q_sig = [t for t in q_tokens if t not in STOPWORDS]
        if len(q_sig) > 1:
            tok_conditions = []
            for tok in q_sig:
                tp = f"%{tok}%"
                tok_conditions.append(
                    "(l.law_name ILIKE %s OR l.short_name ILIKE %s OR s.section_title ILIKE %s OR s.description ILIKE %s OR s.full_text ILIKE %s)"
                )
                params.extend([tp] * 5)
            conditions.append("(" + " AND ".join(tok_conditions) + ")")

        # Combine text match conditions
        base_match_clause = "(" + " OR ".join(conditions) + ")"
        filter_conditions = [base_match_clause]

        # Optional law_id filter
        if law_id is not None:
            filter_conditions.append("s.law_id = %s")
            params.append(law_id)

        # Optional jurisdiction filter
        if jurisdiction and jurisdiction.strip():
            filter_conditions.append("(s.jurisdiction ILIKE %s OR l.jurisdiction ILIKE %s)")
            jur_param = f"%{jurisdiction.strip()}%"
            params.extend([jur_param, jur_param])

        where_clause = " WHERE " + " AND ".join(filter_conditions)

        # 3. Total Matching Count Query
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM sections s
            JOIN laws l ON s.law_id = l.law_id
            {where_clause};
        """
        db.execute(count_sql, tuple(params))
        count_result = db.fetchone()
        total_count = count_result["total"] if count_result else 0

        if total_count == 0:
            return SearchResponse(
                query=query,
                total=0,
                limit=limit,
                offset=offset,
                results=[]
            )

        # 4. Candidate Retrieval for In-Memory Deterministic Ranking
        candidate_pool_limit = max(limit + offset, 250)
        candidate_sql = f"""
            SELECT 
                s.section_id,
                s.law_id,
                l.law_name,
                l.short_name,
                s.section_number,
                s.section_title,
                s.description,
                s.full_text,
                COALESCE(s.jurisdiction, l.jurisdiction) AS jurisdiction,
                COALESCE(s.source_pdf, l.source_pdf) AS source_pdf,
                s.source_page_start,
                s.source_page_end,
                COALESCE(s.manual_review_required, l.manual_review_required, false) AS manual_review_required
            FROM sections s
            JOIN laws l ON s.law_id = l.law_id
            {where_clause}
            ORDER BY s.section_id ASC
            LIMIT %s;
        """
        data_params = tuple(params + [candidate_pool_limit])
        db.execute(candidate_sql, data_params)
        candidates = [dict(c) for c in db.fetchall()]

        # 5. Deterministic Relevance Ranking
        ranked_candidates = LegalRankingService.rank_candidates(
            candidates=candidates,
            query=clean_q,
            query_analysis=query_analysis
        )

        # 6. Pagination Slice
        paginated_candidates = ranked_candidates[offset : offset + limit]

        # 7. Response Item Serialization & Snippet Generation
        results: List[SearchResultItem] = []
        for row in paginated_candidates:
            snippet = cls.extract_snippet(
                full_text=row.get("full_text"),
                description=row.get("description"),
                section_title=row.get("section_title"),
                law_name=row.get("law_name"),
                query=clean_q
            )
            results.append(
                SearchResultItem(
                    law_id=row["law_id"],
                    law_name=row["law_name"],
                    section_id=row["section_id"],
                    section_number=row["section_number"],
                    section_title=row.get("section_title"),
                    snippet=snippet,
                    jurisdiction=row.get("jurisdiction"),
                    source_pdf=row.get("source_pdf"),
                    source_page_start=row.get("source_page_start"),
                    source_page_end=row.get("source_page_end"),
                    manual_review_required=row.get("manual_review_required", False)
                )
            )

        return SearchResponse(
            query=query,
            total=total_count,
            limit=limit,
            offset=offset,
            results=results
        )
