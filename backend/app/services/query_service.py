"""
Vidhik Platform - Legal Query Understanding Service
===================================================
Dedicated service layer for high-precision legal query normalization,
statutory terminology detection, multilingual synonym resolution, and
legal concept domain matching using the PostgreSQL `legal_lexicon` dataset.

All database queries are read-only and strictly parameterized.
"""

import re
from typing import Optional, List, Set, Dict, Any, Tuple
try:
    from psycopg2.extras import RealDictCursor
except ImportError:
    RealDictCursor = Any  # type: ignore

from app.schemas.query import (
    LegalQueryAnalysis,
    MatchedTerm,
    MatchedConcept,
    MatchedSynonym
)

# Common English and grammatical stopwords excluded from key token overlap
STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "of", "in", "for", "to", "on", "at",
    "by", "with", "is", "it", "as", "be", "this", "that", "under", "from",
    "vs", "versus", "etc", "what", "which", "where", "how", "who", "whom"
}

# Generic words that must NOT independently trigger a context or terminology match
GENERIC_CONTEXT_WORDS: Set[str] = {
    "land", "property", "contract", "contracts", "dispute", "disputes",
    "law", "laws", "act", "acts", "court", "courts", "order", "orders",
    "person", "persons", "right", "rights", "officer", "officers",
    "state", "central", "government", "public", "proceedings", "proceeding",
    "action", "actions", "rule", "rules", "power", "powers",
    "section", "sections", "subordinate", "higher", "case", "cases",
    "matter", "matters", "authority", "authorities", "legal", "statutory",
    "provision", "provisions", "defined", "definition", "definitions"
}

# Confidence priority hierarchy (lower index = higher priority)
CONFIDENCE_PRIORITY: Dict[str, int] = {
    "exact": 1,
    "normalized": 2,
    "phrase": 3,
    "multilingual": 4,
    "context": 5,
    "concept": 6
}


class LegalLexiconCandidate:
    """
    Helper structure caching precomputed normalized and tokenized representations
    for a statutory legal lexicon entry.
    """

    def __init__(self, row: Dict[str, Any]):
        self.row = row
        self.term_id: str = row["term_id"]
        self.term_en: str = (row.get("term_en") or "").strip()
        self.term_mr: str = (row.get("term_mr") or "").strip()
        self.term_hi: str = (row.get("term_hi") or "").strip()
        self.category: str = (row.get("category") or "").strip()
        self.context_usage: str = (row.get("context_usage") or "").strip()
        self.grammatical_type: Optional[str] = row.get("grammatical_type")
        self.aliases_mr: List[str] = [a.strip() for a in (row.get("aliases_mr") or []) if a and a.strip()]
        self.aliases_hi: List[str] = [a.strip() for a in (row.get("aliases_hi") or []) if a and a.strip()]

        # English tokenization and canonical forms
        self.en_tokens = LegalQueryService.clean_tokens(self.term_en)
        self.en_sig_tokens = [t for t in self.en_tokens if t not in STOPWORDS]
        self.en_stem_tokens = [LegalQueryService.stem_token(t) for t in self.en_sig_tokens]
        self.en_canonical = LegalQueryService.canonicalize(self.term_en)
        self.id_canonical = LegalQueryService.canonicalize(self.term_id)

        # Devanagari canonical forms
        self.mr_canonical = LegalQueryService.canonicalize(self.term_mr)
        self.hi_canonical = LegalQueryService.canonicalize(self.term_hi)
        self.mr_aliases_canonical = [LegalQueryService.canonicalize(a) for a in self.aliases_mr]
        self.hi_aliases_canonical = [LegalQueryService.canonicalize(a) for a in self.aliases_hi]


class LegalQueryService:
    """
    Service responsible for high-precision query understanding, legal lexicon detection,
    and statutory terminology expansion across Indian legal contexts.
    """

    @staticmethod
    def normalize(query: str) -> str:
        """
        Normalizes a raw user query by trimming leading/trailing whitespace
        and collapsing repeated internal spaces into a single space.

        :param query: Raw search query string
        :return: Cleaned, normalized query string
        """
        if not query:
            return ""
        return " ".join(query.strip().split())

    @staticmethod
    def clean_tokens(text: str) -> List[str]:
        """
        Extracts lowercase alphanumeric and Devanagari tokens from text,
        replacing hyphens and underscores with spaces to handle compound legal phrases.

        :param text: Input string to tokenize
        :return: List of clean lowercase tokens
        """
        if not text:
            return []
        spaced = text.replace("-", " ").replace("_", " ")
        return re.findall(r"[a-zA-Z0-9\u0900-\u097F]+", spaced.lower())

    @staticmethod
    def stem_token(word: str) -> str:
        """
        Applies lightweight heuristic suffix normalization for common English legal terms.

        :param word: Single token string
        :return: Stemmed / normalized root form
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

    @staticmethod
    def canonicalize(text: str) -> str:
        """
        Extracts a canonical alphanumeric representation stripping all whitespace,
        punctuation, and hyphens for robust normalization matching.

        :param text: Input string
        :return: Condensed canonical lowercase string
        """
        if not text:
            return ""
        return re.sub(r"[^a-zA-Z0-9\u0900-\u097F]", "", text.lower())

    @classmethod
    def analyze_query(cls, db: RealDictCursor, query: str) -> LegalQueryAnalysis:
        """
        Analyzes a search query against the statutory `legal_lexicon` table using
        a multi-tiered, precision-first matching hierarchy.

        Match Priority Hierarchy:
        1. EXACT TERM MATCH (`exact`):
           Direct case-insensitive equality against English term or term_id.
        2. NORMALIZED TERM MATCH (`normalized`):
           Equality after stripping hyphens, repeated whitespace, punctuation, or applying suffix stems.
        3. MULTILINGUAL EXACT / PHRASE MATCH (`multilingual`):
           Exact or whole-phrase matching against Marathi / Hindi terms and registered aliases.
        4. WHOLE PHRASE MATCH (`phrase`):
           Complete statutory phrase containment surrounded by token boundaries within multi-word queries.
        5. CONTEXT MATCH (`context`):
           Multi-keyword distinctive statutory context match; generic words are explicitly disqualified.
        6. CONCEPT DOMAIN (`concept`):
           Category domain identification without treating generic words as terminology matches.

        :param db: RealDictCursor database cursor dependency
        :param query: Raw user search query string
        :return: LegalQueryAnalysis containing normalization, matched terms, concepts, and synonyms
        """
        original_query = query or ""
        normalized_query = cls.normalize(original_query)
        q_tokens = cls.clean_tokens(normalized_query)
        q_sig_tokens = [t for t in q_tokens if t not in STOPWORDS]
        q_stem_tokens = [cls.stem_token(t) for t in q_sig_tokens]
        q_canonical = cls.canonicalize(normalized_query)
        q_lower = normalized_query.lower()

        q_phrase_joined = " ".join(q_sig_tokens)
        q_stem_joined = " ".join(q_stem_tokens)

        # Retrieve authoritative legal lexicon entries via read-only parameterized query
        db.execute("""
            SELECT 
                lexicon_id,
                term_id,
                category,
                term_en,
                term_mr,
                term_hi,
                grammatical_type,
                context_usage,
                official_source,
                verification_status,
                aliases_mr,
                aliases_hi
            FROM legal_lexicon
            ORDER BY lexicon_id ASC;
        """)
        all_lexicon = db.fetchall()

        matched_terms: List[MatchedTerm] = []
        matched_concepts_map: Dict[str, List[str]] = {}
        matched_synonyms: List[MatchedSynonym] = []
        identified_categories: Set[str] = set()

        for row in all_lexicon:
            cand = LegalLexiconCandidate(row)
            term_matches: List[Tuple[str, str]] = []

            # -------------------------------------------------------------
            # 1. EXACT TERM MATCH (English term_en or term_id)
            # -------------------------------------------------------------
            if q_lower == cand.term_en.lower() or q_lower == cand.term_id.lower():
                term_matches.append(("exact", f"exact_term('{cand.term_en}')"))

            # -------------------------------------------------------------
            # 2. NORMALIZED TERM MATCH (Hyphen / Space / Stem Normalization)
            # -------------------------------------------------------------
            elif q_canonical and (q_canonical == cand.en_canonical or q_canonical == cand.id_canonical):
                term_matches.append(("normalized", f"normalized_term('{cand.term_en}')"))
            elif q_stem_tokens and q_stem_tokens == cand.en_stem_tokens:
                term_matches.append(("normalized", f"normalized_stem_term('{cand.term_en}')"))

            # -------------------------------------------------------------
            # 3. MULTILINGUAL EXACT / ALIAS / PHRASE MATCH (Marathi & Hindi)
            # -------------------------------------------------------------
            if cand.term_mr:
                if q_lower == cand.term_mr.lower() or q_canonical == cand.mr_canonical:
                    term_matches.append(("multilingual", f"multilingual_exact(mr:'{cand.term_mr}')"))
                elif len(cand.term_mr) > 2 and cand.term_mr in normalized_query:
                    term_matches.append(("multilingual", f"multilingual_phrase(mr:'{cand.term_mr}')"))

            for a, a_canon in zip(cand.aliases_mr, cand.mr_aliases_canonical):
                if q_lower == a.lower() or q_canonical == a_canon:
                    term_matches.append(("multilingual", f"multilingual_alias_exact(mr:'{a}')"))
                elif len(a) > 2 and a in normalized_query:
                    term_matches.append(("multilingual", f"multilingual_alias_phrase(mr:'{a}')"))

            if cand.term_hi:
                if q_lower == cand.term_hi.lower() or q_canonical == cand.hi_canonical:
                    term_matches.append(("multilingual", f"multilingual_exact(hi:'{cand.term_hi}')"))
                elif len(cand.term_hi) > 2 and cand.term_hi in normalized_query:
                    term_matches.append(("multilingual", f"multilingual_phrase(hi:'{cand.term_hi}')"))

            for a, a_canon in zip(cand.aliases_hi, cand.hi_aliases_canonical):
                if q_lower == a.lower() or q_canonical == a_canon:
                    term_matches.append(("multilingual", f"multilingual_alias_exact(hi:'{a}')"))
                elif len(a) > 2 and a in normalized_query:
                    term_matches.append(("multilingual", f"multilingual_alias_phrase(hi:'{a}')"))

            # -------------------------------------------------------------
            # 4. WHOLE PHRASE MATCH (English within larger query)
            # -------------------------------------------------------------
            if not term_matches and cand.en_sig_tokens:
                if len(cand.en_sig_tokens) > 1:
                    term_phrase_joined = " ".join(cand.en_sig_tokens)
                    term_stem_joined = " ".join(cand.en_stem_tokens)
                    if (re.search(r'\b' + re.escape(term_phrase_joined) + r'\b', q_phrase_joined) or
                            re.search(r'\b' + re.escape(term_stem_joined) + r'\b', q_stem_joined)):
                        term_matches.append(("phrase", f"whole_phrase_containment('{cand.term_en}')"))
                elif len(cand.en_sig_tokens) == 1:
                    # Single-word term: only matches if distinct standalone token in a multi-word query
                    single_term = cand.en_sig_tokens[0]
                    single_stem = cand.en_stem_tokens[0]
                    if len(q_sig_tokens) > 1:
                        if (re.search(r'\b' + re.escape(single_term) + r'\b', q_phrase_joined) or
                                re.search(r'\b' + re.escape(single_stem) + r'\b', q_stem_joined)):
                            term_matches.append(("phrase", f"single_term_containment('{cand.term_en}')"))

            # -------------------------------------------------------------
            # 5. CONTEXT MATCH (Statutory Context Usage)
            # -------------------------------------------------------------
            if not term_matches and cand.context_usage:
                ctx_tokens = cls.clean_tokens(cand.context_usage)
                ctx_sig_tokens = [
                    t for t in ctx_tokens
                    if t not in STOPWORDS and t not in GENERIC_CONTEXT_WORDS and len(t) > 3
                ]
                # Requires at least 2 distinct non-generic keywords to match
                matched_ctx = [
                    qt for qt in q_sig_tokens
                    if qt not in GENERIC_CONTEXT_WORDS and qt in ctx_sig_tokens
                ]
                if len(matched_ctx) >= 2:
                    term_matches.append(("context", f"context_phrase_match({','.join(matched_ctx)})"))

            # If any matching criteria triggered for this term, record it
            if term_matches:
                best_match = min(term_matches, key=lambda m: CONFIDENCE_PRIORITY.get(m[0], 99))
                match_types = [m[1] for m in term_matches]

                matched_terms.append(
                    MatchedTerm(
                        term_id=cand.term_id,
                        term_en=cand.term_en,
                        term_mr=cand.term_mr if cand.term_mr else None,
                        term_hi=cand.term_hi if cand.term_hi else None,
                        category=cand.category if cand.category else None,
                        grammatical_type=cand.grammatical_type,
                        context_usage=cand.context_usage if cand.context_usage else None,
                        match_types=match_types,
                        confidence=best_match[0]
                    )
                )

                # Concept aggregation for matched terms
                if cand.category:
                    if cand.category not in matched_concepts_map:
                        matched_concepts_map[cand.category] = []
                    matched_concepts_map[cand.category].append(cand.term_id)

                # Multilingual synonyms list aggregation
                all_mr = ([cand.term_mr] if cand.term_mr else []) + [
                    a for a in cand.aliases_mr if a != cand.term_mr
                ]
                all_hi = ([cand.term_hi] if cand.term_hi else []) + [
                    a for a in cand.aliases_hi if a != cand.term_hi
                ]
                matched_synonyms.append(
                    MatchedSynonym(
                        term_id=cand.term_id,
                        term_en=cand.term_en,
                        synonyms_mr=all_mr,
                        synonyms_hi=all_hi
                    )
                )

            # -------------------------------------------------------------
            # 6. CONCEPT / CATEGORY DOMAIN IDENTIFICATION
            # -------------------------------------------------------------
            if cand.category and cand.category not in identified_categories:
                cat_words = [
                    w for w in cand.category.split("_")
                    if w not in STOPWORDS and len(w) > 3
                ]
                for qw in q_sig_tokens:
                    stemmed_qw = cls.stem_token(qw)
                    for cw in cat_words:
                        stemmed_cw = cls.stem_token(cw)
                        if stemmed_qw == stemmed_cw:
                            identified_categories.add(cand.category)

        # Include identified category domains with empty term lists if no specific terms were matched
        for cat in identified_categories:
            if cat not in matched_concepts_map:
                matched_concepts_map[cat] = []

        matched_concepts = [
            MatchedConcept(category=cat, matched_terms=terms)
            for cat, terms in matched_concepts_map.items()
        ]

        return LegalQueryAnalysis(
            original_query=original_query,
            normalized_query=normalized_query,
            matched_terms=matched_terms,
            matched_concepts=matched_concepts,
            matched_synonyms=matched_synonyms
        )
