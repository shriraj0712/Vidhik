"""
Vidhik Platform - Legal Query Understanding Schemas
===================================================
Pydantic data models for structured query analysis, terminology matching,
multilingual synonym resolution, and legal concept extraction.
"""

from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class MatchedTerm(BaseModel):
    """
    Representation of a legal terminology match detected in the statutory lexicon.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    term_id: str = Field(description="Unique identifier of the statutory lexicon term")
    term_en: str = Field(description="English statutory terminology")
    term_mr: Optional[str] = Field(default=None, description="Marathi statutory legal equivalent")
    term_hi: Optional[str] = Field(default=None, description="Hindi statutory legal equivalent")
    category: Optional[str] = Field(default=None, description="Legal domain classification / category")
    grammatical_type: Optional[str] = Field(default=None, description="Grammatical classification (e.g., noun, phrase)")
    context_usage: Optional[str] = Field(default=None, description="Statutory definition or usage context")
    match_types: List[str] = Field(default_factory=list, description="List of match rules triggered for this term")
    confidence: Optional[str] = Field(default=None, description="Confidence classification: exact, normalized, phrase, multilingual, context, concept")


class MatchedConcept(BaseModel):
    """
    Representation of a matched legal concept domain.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    category: str = Field(description="Legal domain concept category name")
    matched_terms: List[str] = Field(default_factory=list, description="List of term IDs associated with this concept")


class MatchedSynonym(BaseModel):
    """
    Representation of resolved multilingual synonyms and aliases for a matched legal term.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    term_id: str = Field(description="Lexicon term identifier")
    term_en: str = Field(description="Primary English legal term")
    synonyms_mr: List[str] = Field(default_factory=list, description="Marathi synonym and alias forms")
    synonyms_hi: List[str] = Field(default_factory=list, description="Hindi synonym and alias forms")


class LegalQueryAnalysis(BaseModel):
    """
    Structured internal representation returned by LegalQueryService.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    original_query: str = Field(description="Exact raw query string supplied by the user")
    normalized_query: str = Field(description="Cleaned, whitespace-normalized query string")
    matched_terms: List[MatchedTerm] = Field(default_factory=list, description="List of matched statutory lexicon terms")
    matched_concepts: List[MatchedConcept] = Field(default_factory=list, description="Grouped legal concept domains")
    matched_synonyms: List[MatchedSynonym] = Field(default_factory=list, description="Multilingual synonym and alias sets")
