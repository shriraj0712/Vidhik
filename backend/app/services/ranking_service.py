"""
Vidhik Platform - Deterministic Legal Search Ranking Service
============================================================
Dedicated service layer for ranking statutory section search candidates using
deterministic legal relevance evidence from query analysis, statutory section
headings, parent enactments, and contextual statutory text.

All ranking operations are strictly deterministic, in-memory, and read-only.
No stochastic heuristics, vector databases, embeddings, or LLMs are employed.
"""

import re
from typing import Optional, List, Dict, Any, Tuple
from app.schemas.query import LegalQueryAnalysis

# Stopwords excluded from significant token matching
STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "in", "for", "to", "on", "at",
    "by", "with", "is", "it", "as", "be", "this", "that", "under", "from",
    "vs", "versus", "etc", "what", "which", "where", "how", "who", "whom"
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


class LegalRankingService:
    """
    Deterministic Legal Relevance Ranking Engine for Indian Statutory Search.
    
    Ranks statutory candidates based on 9 strict priority tiers:
    1. Exact Section Number Match (e.g., query "155" matches section_number "155")
    2. Exact Legal Term Match on Section Title (e.g., title "Indemnity" for "indemnity")
    3. Exact Phrase Match on Section Title (e.g., "Breach of contract" for "contract")
    4. Normalized Legal Term Match on Section Title (e.g., "Co-operative Societies" for "cooperative society")
    5. Section Title Token Match (All / Partial significant query tokens in title)
    6. Law Name / Short Name Match (Query or legal term in parent statute name)
    7. Description Match (High-level statutory section summary match)
    8. Full-Text Whole Phrase Match (Exact phrase in statutory text body)
    9. Full-Text Multi-Token / Concept Match (Dispersed query tokens in full text)
    10. Fallback Partial Match
    """

    @classmethod
    def compute_rank_evidence(
        cls,
        candidate: Dict[str, Any],
        query: str,
        query_analysis: Optional[LegalQueryAnalysis] = None
    ) -> Tuple[int, int, int, int, int, int, str]:
        """
        Computes a deterministic ranking tuple for a statutory candidate.

        Tuple Structure (Ascending Sort Order):
        - Index 0 (int): Primary Evidence Tier (1 to 10, lower = higher relevance)
        - Index 1 (int): Sub-tier Exactness Penalty (0 = pure exact, 1+ = partial)
        - Index 2 (int): Title Length Penalty (shorter, focused title preferred)
        - Index 3 (int): Law Name Length Penalty (shorter, focused law name preferred)
        - Index 4 (int): Section Number Length Penalty
        - Index 5 (int): Stable Section ID (deterministic tie-breaker)
        - Index 6 (str): Internal Human-Readable Explanation of Decision

        :param candidate: Dictionary of statutory section candidate record
        :param query: Clean raw search query string
        :param query_analysis: Structured query analysis from LegalQueryService
        :return: Deterministic ranking tuple
        """
        clean_q = query.strip().lower()
        q_canonical = canonicalize(query)
        q_tokens = clean_tokens(query)
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
        short_name = (candidate.get("short_name") or "").strip().lower()
        description = (candidate.get("description") or "").strip().lower()
        full_text = (candidate.get("full_text") or "").strip().lower()
        sec_id = int(candidate.get("section_id") or 0)

        matched_terms = query_analysis.matched_terms if query_analysis else []
        matched_term_ens = [t.term_en.lower() for t in matched_terms if t.term_en]
        matched_term_canonicals = [canonicalize(t.term_en) for t in matched_terms if t.term_en]
        matched_term_mrs = [t.term_mr.lower() for t in matched_terms if t.term_mr]
        matched_term_his = [t.term_hi.lower() for t in matched_terms if t.term_hi]

        # -----------------------------------------------------------------
        # Tier 1: Exact Section Number Match (e.g. query is "155")
        # -----------------------------------------------------------------
        if sec_num and clean_q == sec_num:
            return (1, 0, len(sec_title), len(law_name), len(sec_num), sec_id, "exact_section_number")

        # -----------------------------------------------------------------
        # Tier 2: Exact Legal Term Match on Section Title
        # -----------------------------------------------------------------
        for term_en, term_canon in zip(matched_term_ens, matched_term_canonicals):
            if title_canonical == term_canon or sec_title_lower.rstrip(".:,;") == term_en:
                return (2, 0, len(sec_title), len(law_name), 0, sec_id, f"exact_legal_term_title('{term_en}')")

        # Multilingual Exact Match on Title
        for devanagari_term in matched_term_mrs + matched_term_his:
            if devanagari_term and (devanagari_term in sec_title_lower or canonicalize(devanagari_term) == title_canonical):
                return (2, 1, len(sec_title), len(law_name), 0, sec_id, f"multilingual_legal_term_title('{devanagari_term}')")

        # -----------------------------------------------------------------
        # Tier 3: Exact Phrase Match on Section Title
        # -----------------------------------------------------------------
        if clean_q and (re.search(r'\b' + re.escape(clean_q) + r'\b', sec_title_lower) or title_canonical == q_canonical):
            is_pure_title = (title_canonical == q_canonical)
            exactness = 0 if is_pure_title else 1
            return (3, exactness, len(sec_title), len(law_name), 0, sec_id, f"exact_phrase_title('{clean_q}')")

        # -----------------------------------------------------------------
        # Tier 4: Normalized Legal Term Match on Section Title
        # -----------------------------------------------------------------
        for term_en, term_canon in zip(matched_term_ens, matched_term_canonicals):
            term_stems = [stem_token(t) for t in clean_tokens(term_en)]
            if term_canon in title_canonical or (term_stems and all(st in title_stem_tokens for st in term_stems)):
                return (4, 0, len(sec_title), len(law_name), 0, sec_id, f"normalized_legal_term_title('{term_en}')")

        # -----------------------------------------------------------------
        # Tier 5: Section Title Token Match (All / Partial Query Tokens)
        # -----------------------------------------------------------------
        if q_sig_tokens and all(st in title_stem_tokens for st in q_stem_tokens):
            return (5, 0, len(sec_title), len(law_name), 0, sec_id, "all_query_tokens_in_title")
        elif q_sig_tokens and any(st in title_stem_tokens for st in q_stem_tokens):
            matched_count = sum(1 for st in q_stem_tokens if st in title_stem_tokens)
            missing_count = len(q_sig_tokens) - matched_count
            return (5, missing_count + 1, len(sec_title), len(law_name), 0, sec_id, "partial_query_tokens_in_title")

        # -----------------------------------------------------------------
        # Tier 6: Law Name / Short Name Match
        # -----------------------------------------------------------------
        if clean_q in law_name_lower or clean_q in short_name or any(tc in canonicalize(law_name) for tc in matched_term_canonicals):
            return (6, 0, len(sec_title), len(law_name), 0, sec_id, "law_name_phrase_match")
        elif q_sig_tokens and all(st in [stem_token(t) for t in clean_tokens(law_name)] for st in q_stem_tokens):
            return (6, 1, len(sec_title), len(law_name), 0, sec_id, "all_query_tokens_in_law_name")

        # -----------------------------------------------------------------
        # Tier 7: Description Match
        # -----------------------------------------------------------------
        if clean_q in description or (q_sig_tokens and all(st in [stem_token(t) for t in clean_tokens(description)] for st in q_stem_tokens)):
            return (7, 0, len(sec_title), len(law_name), 0, sec_id, "description_match")

        # -----------------------------------------------------------------
        # Tier 8: Full-Text Whole Phrase Match
        # -----------------------------------------------------------------
        if clean_q in full_text:
            return (8, 0, len(sec_title), len(law_name), 0, sec_id, "full_text_phrase_match")

        # -----------------------------------------------------------------
        # Tier 9: Full-Text Multi-Token / Concept Match
        # -----------------------------------------------------------------
        if q_sig_tokens and all(st in [stem_token(t) for t in clean_tokens(full_text)] for st in q_stem_tokens):
            return (9, 0, len(sec_title), len(law_name), 0, sec_id, "full_text_all_tokens_match")

        # -----------------------------------------------------------------
        # Tier 10: Fallback Generic Match
        # -----------------------------------------------------------------
        return (10, 0, len(sec_title), len(law_name), 0, sec_id, "full_text_partial_match")

    @classmethod
    def rank_candidates(
        cls,
        candidates: List[Dict[str, Any]],
        query: str,
        query_analysis: Optional[LegalQueryAnalysis] = None
    ) -> List[Dict[str, Any]]:
        """
        Ranks candidate records deterministically based on multi-tiered legal evidence.

        :param candidates: List of raw candidate section dictionaries from PostgreSQL
        :param query: Clean raw search query string
        :param query_analysis: Structured query analysis from LegalQueryService
        :return: Deterministically sorted list of candidate dictionaries
        """
        if not candidates:
            return []

        evaluated = []
        for cand in candidates:
            rank_tuple = cls.compute_rank_evidence(cand, query, query_analysis)
            cand_dict = dict(cand)
            cand_dict["_rank_tuple"] = rank_tuple
            cand_dict["_rank_explanation"] = rank_tuple[-1]
            evaluated.append(cand_dict)

        # Sort deterministically by the composite ranking tuple
        evaluated.sort(key=lambda x: x["_rank_tuple"])
        return evaluated
