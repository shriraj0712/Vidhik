"""
Vidhik Platform - Law Model
===========================
Data model representing records from the PostgreSQL `laws` table.
"""

from typing import Optional, Any
from datetime import datetime, date
from dataclasses import dataclass, field


@dataclass
class LawModel:
    law_id: int
    law_name: str
    short_name: Optional[str] = None
    law_type: Optional[str] = None
    description: Optional[str] = None
    jurisdiction: str = "India"
    enactment_date: Optional[date] = None
    effective_date: Optional[date] = None
    source_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    law_slug: Optional[str] = None
    year: Optional[int] = None
    source_pdf: Optional[str] = None
    total_pages: Optional[int] = None
    enactment_start_page: Optional[int] = None
    total_sections_extracted: Optional[int] = None
    is_diglot: Optional[bool] = None
    extraction_status: Optional[str] = None
    manual_review_required: Optional[bool] = None
    parser_notes: Optional[Any] = None
