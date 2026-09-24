"""
Vidhik Platform - Section Schemas
=================================
Pydantic schemas for serializing and validating sections API responses.
"""

from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SectionSummaryResponse(BaseModel):
    """Compact summary schema for section listing."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    section_id: int
    law_id: int
    section_number: str
    section_title: Optional[str] = None
    section_uid: Optional[str] = None
    chapter_number: Optional[str] = None
    chapter_title: Optional[str] = None
    source_pdf: Optional[str] = None
    source_page_start: Optional[int] = None
    source_page_end: Optional[int] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    manual_review_required: Optional[bool] = False
    is_omitted: Optional[bool] = False


class SectionResponse(BaseModel):
    """Full detailed section record schema."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    section_id: int
    law_id: int
    section_number: str
    section_title: Optional[str] = None
    section_uid: Optional[str] = None
    full_text: Optional[str] = None
    section_text: Optional[str] = None
    description: Optional[str] = None
    chapter: Optional[str] = None
    chapter_number: Optional[str] = None
    chapter_title: Optional[str] = None
    part: Optional[str] = None
    part_number: Optional[str] = None
    part_title: Optional[str] = None
    source_url: Optional[str] = None
    source_pdf: Optional[str] = None
    source_page_start: Optional[int] = None
    source_page_end: Optional[int] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    jurisdiction: Optional[str] = None
    is_omitted: Optional[bool] = None
    omission_note: Optional[str] = None
    is_definition_section: Optional[bool] = None
    subsections_count: Optional[int] = None
    clauses_count: Optional[int] = None
    subclauses_count: Optional[int] = None
    has_proviso: Optional[bool] = None
    has_explanation: Optional[bool] = None
    has_illustration: Optional[bool] = None
    has_schedule_ref: Optional[bool] = None
    extraction_status: Optional[str] = None
    manual_review_required: Optional[bool] = None
    parser_notes: Optional[Any] = None
    text_sha256: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SectionListResponse(BaseModel):
    """Paginated list response schema for sections."""
    total: int
    limit: int
    offset: int
    sections: List[SectionSummaryResponse]
