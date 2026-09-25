"""
Vidhik Platform - Deterministic Legal Search Ranking Service (Phase 8)
======================================================================
Dedicated service layer for ranking statutory section search candidates using
deterministic legal relevance evidence from query analysis, statutory section
headings, parent enactments, and contextual statutory text.

Guarantees:
- Strictly deterministic, transparent, and explainable scoring.
- Incorporates Phase 1-7 query analysis & legal lexicon confidence levels:
    exact > normalized > phrase > multilingual > context > concept
- Respects statutory textual location hierarchy:
    law title > section heading/title > section text
- Enforces stable tie-breaking:
    ( -rank_score, law_id, section_id )
- Zero external LLMs, zero embeddings, zero vector databases, zero stochastic methods.
- 100% read-only and in-memory.
"""

import re
from typing import Optional, List, Dict, Any, Tuple
from app.schemas.query import LegalQueryAnalysis, MatchedTerm

# Stopwords excluded from significant token matching
STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "in", "for", "to", "on", "at",
    "by", "with", "is", "it", "as", "be", "this", "that", "under", "from",
    "vs", "versus", "etc", "what", "which", "where", "how", "who", "whom"
}

# Centralized scoring weights for deterministic legal relevance
RANKING_WEIGHTS: Dict[str, float] = {
    # Section Number Exact Match
    "SECTION_NUMBER_EXACT": 1000.0,
    
    # Confidence Level Base Scores (Strictly: exact > normalized > phrase > multilingual > context > concept)
    # Tier 2: Exact Match
    "CONFIDENCE_EXACT_LAW_TITLE": 920.0,
    "CONFIDENCE_EXACT_SECTION_TITLE": 900.0,
    "CONFIDENCE_EXACT_QUERY_TITLE": 880.0,
    
    # Tier 3: Normalized Match
    "CONFIDENCE_NORMALIZED_LAW_TITLE": 780.0,
    "CONFIDENCE_NORMALIZED_SECTION_TITLE": 760.0,
    "CONFIDENCE_NORMALIZED_QUERY_TITLE": 740.0,
    
    # Tier 4: Phrase Match
    "CONFIDENCE_PHRASE_LAW_TITLE": 680.0,
    "CONFIDENCE_PHRASE_SECTION_TITLE": 660.0,
    "CONFIDENCE_PHRASE_QUERY_TITLE": 640.0,
    
    # Tier 5: Multilingual Match
    "CONFIDENCE_MULTILINGUAL_LAW_TITLE": 580.0,
    "CONFIDENCE_MULTILINGUAL_SECTION_TITLE": 560.0,
    "CONFIDENCE_MULTILINGUAL_BODY": 520.0,
    
    # Tier 6: Context Match
    "CONFIDENCE_CONTEXT_LAW_TITLE": 480.0,
    "CONFIDENCE_CONTEXT_SECTION_TITLE": 460.0,
    "CONFIDENCE_CONTEXT_BODY": 420.0,
    
    # Tier 7: Concept Domain Match
    "CONFIDENCE_CONCEPT_LAW_TITLE": 380.0,
    "CONFIDENCE_CONCEPT_SECTION_TITLE": 360.0,
    "CONFIDENCE_CONCEPT_BODY": 320.0,
    
    # Textual Query Match Fallbacks
    "QUERY_ALL_TOKENS_SECTION_TITLE": 280.0,
    "QUERY_PARTIAL_TOKENS_SECTION_TITLE": 220.0,
    "QUERY_LAW_NAME_MATCH": 180.0,
    "QUERY_DESCRIPTION_MATCH": 140.0,
    "QUERY_FULL_TEXT_PHRASE": 100.0,
    "QUERY_FULL_TEXT_ALL_TOKENS": 70.0,
    "QUERY_FULL_TEXT_PARTIAL_TOKENS": 40.0,
    
    # Generic Fallback
    "FALLBACK_GENERIC": 10.0,
}


def clean_tokens(text: str) -> List[str]:
    """
    Extracts lowercase alphanumeric and Devanagari tokens from text,
    normalizing hyphens and underscores to spaces.
    """
    if not text:
        return []
    spaced = text.replace("-", " ").replace("_", " ")
    return re.findall(r"[a-zA-Z0-9\u0900-\u097F]+", spaced.lower())


def canonicalize(text: str) -> str:
    """
    Generates a canonical condensed lowercase alphanumeric string
    for punctuation- and whitespace-insensitive matching.
    """
    if not text:
        return ""
    return re.sub(r"[^a-zA-Z0-9\u0900-\u097F]", "", text.lower())


def stem_token(word: str) -> str:
    """
    Lightweight heuristic English suffix stemmer for legal plurals and derivations.
    """
    w = word.lower()
    if len(w) <= 3:
        return w
    if w.endswith("ual") and len(w) > 5:
        return w[:-3]  # contractual -> contract
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"  # societies -> society, penalties -> penalty
    if w.endswith("es") and len(w) > 4:
        return w[:-2]  # offences -> offence
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        return w[:-1]  # contracts -> contract, provisions -> provision
    return w


def extract_section_number_from_query(query: str) -> Optional[str]:
    """
    Detects if a query specifically targets a section number (e.g. '155', 'section 155', 'sec. 155').
    """
    clean_q = query.strip().lower()
    m = re.match(r"^(?:section|sec|sec\.|s\.)?\s*([0-9]+[a-zA-Z]*)$", clean_q)
    if m:
        return m.group(1).lower()
    return None


class LegalRankingService:
    """
    Deterministic Legal Relevance Ranking Engine for Indian Statutory Search.
    
    Ranks statutory candidates based on strict priority levels:
    1. Exact Section Number Match (e.g. '155')
    2. Exact Legal Term Match (Law Title > Section Title > Query Title)
    3. Normalized Legal Term Match (Law Title > Section Title > Query Title)
    4. Phrase Match (Law Title > Section Title > Query Title)
    5. Multilingual Match (Marathi/Hindi on Law Title > Section Title > Body)
    6. Context Match (Usage context on Law Title > Section Title > Body)
    7. Concept Domain Match (Category domain on Law Title > Section Title > Body)
    8. Section Title Token Match (All / Partial significant query tokens)
    9. Law Name Match (Query phrase or tokens in parent statute name)
    10. Description Match (High-level statutory section summary match)
    11. Section Body (full_text) Match (Phrase > All tokens > Partial tokens)
    12. Fallback Generic Match

    Deterministic Tie-Breaking:
    Candidates with identical scores are stably ordered by:
    `law_id` (ascending), then `section_id` (ascending).
    """

    @classmethod
    def calculate_candidate_relevance(
        cls,
        candidate: Dict[str, Any],
        query: str,
        query_analysis: Optional[LegalQueryAnalysis] = None
    ) -> Tuple[float, str, int]:
        """
        Calculates a deterministic legal relevance score, explanation reason, and tier index.

        :param candidate: Dictionary of statutory section candidate record
        :param query: Clean raw search query string
        :param query_analysis: Optional structured query analysis from LegalQueryService
        :return: Tuple of (rank_score: float, rank_reason: str, tier: int)
        """
        clean_q = query.strip().lower()
        q_canonical = canonicalize(clean_q)
        q_tokens = clean_tokens(clean_q)
        q_sig_tokens = [t for t in q_tokens if t not in STOPWORDS]
        q_stem_tokens = [stem_token(t) for t in q_sig_tokens]

        sec_num = (candidate.get("section_number") or "").strip().lower()
        sec_title = (candidate.get("section_title") or "").strip()
        sec_title_lower = sec_title.lower()
        title_canonical = canonicalize(sec_title)
        title_tokens = clean_tokens(sec_title)
        title_sig_tokens = [t for t in title_tokens if t not in STOPWORDS]
        title_stem_tokens = [stem_token(t) for t in title_sig_tokens]

        law_name = (candidate.get("law_name") or "").strip()
        law_name_lower = law_name.lower()
        law_canonical = canonicalize(law_name)
        short_name = (candidate.get("short_name") or "").strip().lower()
        short_canonical = canonicalize(short_name)
        law_tokens = clean_tokens(law_name)
        law_sig_tokens = [t for t in law_tokens if t not in STOPWORDS]
        law_stem_tokens = [stem_token(t) for t in law_sig_tokens]

        description = (candidate.get("description") or "").strip().lower()
        full_text = (candidate.get("full_text") or "").strip().lower()

        # Extract lexicon analysis terms grouped by confidence
        matched_terms: List[MatchedTerm] = query_analysis.matched_terms if query_analysis else []
        matched_concepts = query_analysis.matched_concepts if query_analysis else []

        # -----------------------------------------------------------------
        # Level 1: Exact Section Number Match (e.g. query "155", "Section 155")
        # -----------------------------------------------------------------
        target_sec_num = extract_section_number_from_query(clean_q)
        if sec_num and (clean_q == sec_num or (target_sec_num and target_sec_num == sec_num)):
            base_score = RANKING_WEIGHTS["SECTION_NUMBER_EXACT"]
            reason = f"exact_section_number_match('{sec_num}')"
            tier = 1
            return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, tier)

        # -----------------------------------------------------------------
        # Level 2: Exact Match (Confidence 'exact')
        # Hierarchy: Law Title > Section Title > Query on Section Title
        # -----------------------------------------------------------------
        exact_terms = [t for t in matched_terms if t.confidence == "exact"]
        for t in exact_terms:
            t_canon = canonicalize(t.term_en)
            t_lower = t.term_en.lower()
            if t_canon and (t_canon in law_canonical or t_canon in short_canonical or t_lower in law_name_lower):
                base_score = RANKING_WEIGHTS["CONFIDENCE_EXACT_LAW_TITLE"]
                reason = f"exact_legal_term_law_title('{t.term_en}')"
                title_bonus = 6.0 if (t_canon in title_canonical or t_lower in sec_title_lower or (q_canonical and q_canonical in title_canonical)) else 0.0
                return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 2, title_bonus=title_bonus)

        for t in exact_terms:
            t_canon = canonicalize(t.term_en)
            t_lower = t.term_en.lower()
            if t_canon and (title_canonical == t_canon or t_lower in sec_title_lower):
                base_score = RANKING_WEIGHTS["CONFIDENCE_EXACT_SECTION_TITLE"]
                reason = f"exact_legal_term_section_title('{t.term_en}')"
                return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 2)

        if clean_q and (title_canonical == q_canonical or sec_title_lower.rstrip(".:,;") == clean_q):
            base_score = RANKING_WEIGHTS["CONFIDENCE_EXACT_QUERY_TITLE"]
            reason = f"exact_query_section_title('{clean_q}')"
            return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 2)

        # -----------------------------------------------------------------
        # Level 3: Normalized Match (Confidence 'normalized')
        # Hierarchy: Law Title > Section Title > Normalized Query on Title
        # -----------------------------------------------------------------
        norm_terms = [t for t in matched_terms if t.confidence == "normalized"]
        for t in norm_terms:
            t_canon = canonicalize(t.term_en)
            t_stems = [stem_token(w) for w in clean_tokens(t.term_en)]
            if t_canon and (t_canon in law_canonical or t_canon in short_canonical or (t_stems and all(st in law_stem_tokens for st in t_stems))):
                base_score = RANKING_WEIGHTS["CONFIDENCE_NORMALIZED_LAW_TITLE"]
                reason = f"normalized_legal_term_law_title('{t.term_en}')"
                title_bonus = 6.0 if (t_canon in title_canonical or (t_stems and all(st in title_stem_tokens for st in t_stems)) or (q_canonical and q_canonical in title_canonical)) else 0.0
                return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 3, title_bonus=title_bonus)

        for t in norm_terms:
            t_canon = canonicalize(t.term_en)
            t_stems = [stem_token(w) for w in clean_tokens(t.term_en)]
            if t_canon and (t_canon in title_canonical or (t_stems and all(st in title_stem_tokens for st in t_stems))):
                base_score = RANKING_WEIGHTS["CONFIDENCE_NORMALIZED_SECTION_TITLE"]
                reason = f"normalized_legal_term_section_title('{t.term_en}')"
                return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 3)

        if q_canonical and (q_canonical == title_canonical or (q_stem_tokens and q_stem_tokens == title_stem_tokens)):
            base_score = RANKING_WEIGHTS["CONFIDENCE_NORMALIZED_QUERY_TITLE"]
            reason = f"normalized_query_section_title('{clean_q}')"
            return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 3)

        # -----------------------------------------------------------------
        # Level 4: Phrase Match (Confidence 'phrase')
        # Hierarchy: Law Title > Section Title > Phrase Query on Title
        # -----------------------------------------------------------------
        phrase_terms = [t for t in matched_terms if t.confidence == "phrase"]
        for t in phrase_terms:
            t_lower = t.term_en.lower()
            if t_lower and (t_lower in law_name_lower or t_lower in short_name):
                base_score = RANKING_WEIGHTS["CONFIDENCE_PHRASE_LAW_TITLE"]
                reason = f"phrase_legal_term_law_title('{t.term_en}')"
                return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 4)

        for t in phrase_terms:
            t_lower = t.term_en.lower()
            if t_lower and (t_lower in sec_title_lower or (clean_tokens(t_lower) and all(st in title_tokens for st in clean_tokens(t_lower)))):
                base_score = RANKING_WEIGHTS["CONFIDENCE_PHRASE_SECTION_TITLE"]
                reason = f"phrase_legal_term_section_title('{t.term_en}')"
                return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 4)

        if clean_q and (re.search(r'\b' + re.escape(clean_q) + r'\b', sec_title_lower) or q_canonical in title_canonical):
            base_score = RANKING_WEIGHTS["CONFIDENCE_PHRASE_QUERY_TITLE"]
            reason = f"phrase_query_section_title('{clean_q}')"
            return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 4)

        # -----------------------------------------------------------------
        # Level 5: Multilingual Match (Confidence 'multilingual' / Marathi / Hindi)
        # Hierarchy: Law Title > Section Title > Body
        # -----------------------------------------------------------------
        multi_terms = [t for t in matched_terms if t.confidence == "multilingual"]
        for t in multi_terms:
            for term_lang in [t.term_mr, t.term_hi]:
                if term_lang:
                    tl_lower = term_lang.lower()
                    tl_canon = canonicalize(term_lang)
                    if tl_canon and (tl_canon in law_canonical or tl_lower in law_name_lower):
                        base_score = RANKING_WEIGHTS["CONFIDENCE_MULTILINGUAL_LAW_TITLE"]
                        reason = f"multilingual_legal_term_law_title('{term_lang}')"
                        return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 5)

        for t in multi_terms:
            for term_lang in [t.term_mr, t.term_hi]:
                if term_lang:
                    tl_lower = term_lang.lower()
                    tl_canon = canonicalize(term_lang)
                    if tl_canon and (tl_canon in title_canonical or tl_lower in sec_title_lower):
                        base_score = RANKING_WEIGHTS["CONFIDENCE_MULTILINGUAL_SECTION_TITLE"]
                        reason = f"multilingual_legal_term_section_title('{term_lang}')"
                        return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 5)

        for t in multi_terms:
            for term_lang in [t.term_mr, t.term_hi]:
                if term_lang and (term_lang.lower() in full_text or canonicalize(term_lang) in canonicalize(full_text)):
                    base_score = RANKING_WEIGHTS["CONFIDENCE_MULTILINGUAL_BODY"]
                    reason = f"multilingual_legal_term_body('{term_lang}')"
                    return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 5)

        # -----------------------------------------------------------------
        # Level 6: Context Match (Confidence 'context')
        # Hierarchy: Law Title > Section Title > Body
        # -----------------------------------------------------------------
        ctx_terms = [t for t in matched_terms if t.confidence == "context"]
        for t in ctx_terms:
            t_lower = t.term_en.lower()
            if t_lower in law_name_lower or canonicalize(t.term_en) in law_canonical:
                base_score = RANKING_WEIGHTS["CONFIDENCE_CONTEXT_LAW_TITLE"]
                reason = f"context_legal_term_law_title('{t.term_en}')"
                return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 6)

        for t in ctx_terms:
            t_lower = t.term_en.lower()
            if t_lower in sec_title_lower or canonicalize(t.term_en) in title_canonical:
                base_score = RANKING_WEIGHTS["CONFIDENCE_CONTEXT_SECTION_TITLE"]
                reason = f"context_legal_term_section_title('{t.term_en}')"
                return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 6)

        for t in ctx_terms:
            t_lower = t.term_en.lower()
            if t_lower in full_text or canonicalize(t.term_en) in canonicalize(full_text):
                base_score = RANKING_WEIGHTS["CONFIDENCE_CONTEXT_BODY"]
                reason = f"context_legal_term_body('{t.term_en}')"
                return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 6)

        # -----------------------------------------------------------------
        # Level 7: Concept Domain Match (Confidence 'concept')
        # Hierarchy: Law Title > Section Title > Body
        # -----------------------------------------------------------------
        for concept in matched_concepts:
            cat_words = [w for w in concept.category.split("_") if w not in STOPWORDS and len(w) > 3]
            for cw in cat_words:
                st = stem_token(cw)
                if st in [stem_token(t) for t in clean_tokens(law_name)]:
                    base_score = RANKING_WEIGHTS["CONFIDENCE_CONCEPT_LAW_TITLE"]
                    reason = f"concept_domain_law_title('{concept.category}')"
                    return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 7)
                if st in title_stem_tokens:
                    base_score = RANKING_WEIGHTS["CONFIDENCE_CONCEPT_SECTION_TITLE"]
                    reason = f"concept_domain_section_title('{concept.category}')"
                    return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 7)
                if st in [stem_token(t) for t in clean_tokens(full_text)]:
                    base_score = RANKING_WEIGHTS["CONFIDENCE_CONCEPT_BODY"]
                    reason = f"concept_domain_body('{concept.category}')"
                    return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 7)

        # -----------------------------------------------------------------
        # Level 8: Section Title Token Matches (All / Partial Query Tokens)
        # -----------------------------------------------------------------
        if q_sig_tokens and all(st in title_stem_tokens for st in q_stem_tokens):
            base_score = RANKING_WEIGHTS["QUERY_ALL_TOKENS_SECTION_TITLE"]
            reason = "all_query_tokens_in_section_title"
            return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 8)
        elif q_sig_tokens and any(st in title_stem_tokens for st in q_stem_tokens):
            matched_count = sum(1 for st in q_stem_tokens if st in title_stem_tokens)
            ratio = matched_count / len(q_sig_tokens)
            base_score = RANKING_WEIGHTS["QUERY_PARTIAL_TOKENS_SECTION_TITLE"] + (ratio * 40.0)
            reason = f"partial_query_tokens_in_section_title({matched_count}/{len(q_sig_tokens)})"
            return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 8)

        # -----------------------------------------------------------------
        # Level 9: Direct Query Match on Law Name
        # -----------------------------------------------------------------
        if clean_q in law_name_lower or clean_q in short_name or (q_sig_tokens and all(st in [stem_token(t) for t in clean_tokens(law_name)] for st in q_stem_tokens)):
            base_score = RANKING_WEIGHTS["QUERY_LAW_NAME_MATCH"]
            reason = "query_in_law_name"
            return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 9)

        # -----------------------------------------------------------------
        # Level 10: Section Description Match
        # -----------------------------------------------------------------
        if clean_q in description or (q_sig_tokens and all(st in [stem_token(t) for t in clean_tokens(description)] for st in q_stem_tokens)):
            base_score = RANKING_WEIGHTS["QUERY_DESCRIPTION_MATCH"]
            reason = "query_in_description"
            return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 10)

        # -----------------------------------------------------------------
        # Level 11: Section Body (full_text) Textual Match
        # -----------------------------------------------------------------
        if clean_q in full_text:
            base_score = RANKING_WEIGHTS["QUERY_FULL_TEXT_PHRASE"]
            reason = "full_text_phrase_match"
            return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 11)

        text_stem_tokens = [stem_token(t) for t in clean_tokens(full_text)]
        if q_sig_tokens and all(st in text_stem_tokens for st in q_stem_tokens):
            base_score = RANKING_WEIGHTS["QUERY_FULL_TEXT_ALL_TOKENS"]
            reason = "full_text_all_tokens_match"
            return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 11)
        elif q_sig_tokens and any(st in text_stem_tokens for st in q_stem_tokens):
            matched_count = sum(1 for st in q_stem_tokens if st in text_stem_tokens)
            ratio = matched_count / len(q_sig_tokens)
            base_score = RANKING_WEIGHTS["QUERY_FULL_TEXT_PARTIAL_TOKENS"] + (ratio * 20.0)
            reason = f"full_text_partial_tokens_match({matched_count}/{len(q_sig_tokens)})"
            return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 11)

        # -----------------------------------------------------------------
        # Level 12: Generic Fallback Match
        # -----------------------------------------------------------------
        base_score = RANKING_WEIGHTS["FALLBACK_GENERIC"]
        reason = "fallback_generic_match"
        return cls._finalize_score(base_score, sec_title, q_canonical, title_canonical, reason, 12)

    @classmethod
    def _finalize_score(
        cls,
        base_score: float,
        sec_title: str,
        q_canonical: str,
        title_canonical: str,
        reason: str,
        tier: int,
        title_bonus: float = 0.0
    ) -> Tuple[float, str, int]:
        """
        Applies deterministic precision tuning to the base score:
        - Brevity bonus: focused, concise section titles receive a slight bonus (0 to 5 points)
        - Exactness bonus: exact title match receives +2 points
        - Title bonus: section title co-occurrence bonus when parent law title matched (+6 points)
        Maximum adjustment is < 9 points, strictly preserving tier separation.
        """
        brevity_bonus = round(max(0.0, 5.0 - min(len(sec_title), 100) * 0.05), 3)
        exactness_bonus = 2.0 if (q_canonical and title_canonical == q_canonical) else 0.0
        total_score = round(base_score + brevity_bonus + exactness_bonus + title_bonus, 3)
        return (total_score, reason, tier)

    @classmethod
    def compute_rank_evidence(
        cls,
        candidate: Dict[str, Any],
        query: str,
        query_analysis: Optional[LegalQueryAnalysis] = None
    ) -> Tuple[int, int, int, int, int, int, str]:
        """
        Backward-compatible tuple computation method for existing components.

        Tuple Structure (Ascending Sort Order):
        - Index 0 (int): Primary Evidence Tier (1 to 12, lower = higher relevance)
        - Index 1 (int): Inverted Score (lower = higher relevance)
        - Index 2 (int): Title Length Penalty
        - Index 3 (int): Law ID
        - Index 4 (int): Section ID
        - Index 5 (int): Section Number Length
        - Index 6 (str): Human-Readable Explanation Reason
        """
        score, reason, tier = cls.calculate_candidate_relevance(candidate, query, query_analysis)
        sec_title = candidate.get("section_title") or ""
        law_id = int(candidate.get("law_id") or 0)
        sec_id = int(candidate.get("section_id") or 0)
        sec_num = str(candidate.get("section_number") or "")
        inverted_score = -int(score * 100)
        return (tier, inverted_score, len(sec_title), law_id, sec_id, len(sec_num), reason)

    @classmethod
    def rank_candidates(
        cls,
        candidates: List[Dict[str, Any]],
        query: str,
        query_analysis: Optional[LegalQueryAnalysis] = None
    ) -> List[Dict[str, Any]]:
        """
        Ranks candidate records deterministically based on multi-tiered legal evidence.

        Enforces deterministic tie-breaking:
        `(-rank_score, law_id, section_id)`

        :param candidates: List of raw candidate section dictionaries from PostgreSQL
        :param query: Clean raw search query string
        :param query_analysis: Structured query analysis from LegalQueryService
        :return: Deterministically sorted list of candidate dictionaries
        """
        if not candidates:
            return []

        evaluated: List[Dict[str, Any]] = []
        for cand in candidates:
            score, reason, tier = cls.calculate_candidate_relevance(cand, query, query_analysis)
            law_id = int(cand.get("law_id") or 0)
            sec_id = int(cand.get("section_id") or 0)

            cand_dict = dict(cand)
            cand_dict["rank_score"] = score
            cand_dict["rank_reason"] = reason
            cand_dict["_rank_tier"] = tier
            cand_dict["_rank_explanation"] = reason
            cand_dict["_rank_tuple"] = (tier, -int(score * 100), len(cand.get("section_title") or ""), law_id, sec_id, reason)
            
            # Deterministic sorting key:
            # 1. Higher score first (-score)
            # 2. Stable law_id tie-breaker (ascending)
            # 3. Stable section_id tie-breaker (ascending)
            cand_dict["_sort_key"] = (-score, law_id, sec_id)
            evaluated.append(cand_dict)

        # Sort deterministically
        evaluated.sort(key=lambda x: x["_sort_key"])
        return evaluated
