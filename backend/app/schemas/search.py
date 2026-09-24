"""
Vidhik Platform - Search Schemas
================================
Pydantic schemas for serializing and validating Legal Search API responses.
"""

from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class SearchResultItem(BaseModel):
    """
    Schema representing an individual legal search result matching a statutory section.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    law_id: int = Field(description="Unique identifier of the parent statutory law")
    law_name: str = Field(description="Official title/name of the statute")
    section_id: int = Field(description="Unique identifier of the matching section")
    section_number: str = Field(description="Section number or identifier")
    section_title: Optional[str] = Field(default=None, description="Title or heading of the section")
    snippet: Optional[str] = Field(default=None, description="Contextual excerpt containing the matching query text")
    jurisdiction: Optional[str] = Field(default=None, description="Jurisdiction of the law/section")
    source_pdf: Optional[str] = Field(default=None, description="Filename or path of authoritative source PDF")
    source_page_start: Optional[int] = Field(default=None, description="Starting page in source document")
    source_page_end: Optional[int] = Field(default=None, description="Ending page in source document")
    manual_review_required: Optional[bool] = Field(default=False, description="Flag indicating if OCR/extraction requires review")


class SearchResponse(BaseModel):
    """
    Paginated response schema for legal search queries.
    """
    query: str = Field(description="The original search query executed")
    total: int = Field(description="Total count of matching records across the dataset")
    limit: int = Field(description="Maximum number of results requested")
    offset: int = Field(description="Offset of the results pagination")
    results: List[SearchResultItem] = Field(description="List of matching legal sections and snippets")
