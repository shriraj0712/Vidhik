"""
Vidhik Platform - Section Model
===============================
Data model representing records from the PostgreSQL `sections` table.
"""

from typing import Optional, Any
from datetime import datetime
from dataclasses import dataclass


@dataclass
class SectionModel:
    section_id: int
    law_id: int
    section_number: str
    section_title: Optional[str] = None
    description: Optional[str] = None
    full_text: Optional[str] = None
    chapter: Optional[str] = None
    part: Optional[str] = None
    source_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    section_uid: Optional[str] = None
    chapter_number: Optional[str] = None
    chapter_title: Optional[str] = None
    part_number: Optional[str] = None
    part_title: Optional[str] = None
    source_pdf: Optional[str] = None
    source_page_start: Optional[int] = None
    source_page_end: Optional[int] = None
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
