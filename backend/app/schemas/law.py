"""
Vidhik Platform - Law Schemas
=============================
Pydantic schemas for serializing and validating laws API responses.
"""

from typing import Optional, List, Any
from datetime import datetime, date
from pydantic import BaseModel, ConfigDict


class LawSummaryResponse(BaseModel):
    """Compact summary schema for law listing."""
    model_config = ConfigDict(from_attributes=True)

    law_id: int
    law_name: str
    law_slug: Optional[str] = None
    short_name: Optional[str] = None
    year: Optional[int] = None
    law_type: Optional[str] = None
    jurisdiction: str
    total_sections_extracted: Optional[int] = None
    is_diglot: Optional[bool] = None


class LawResponse(BaseModel):
    """Full law record schema."""
    model_config = ConfigDict(from_attributes=True)

    law_id: int
    law_name: str
    law_slug: Optional[str] = None
    short_name: Optional[str] = None
    year: Optional[int] = None
    law_type: Optional[str] = None
    description: Optional[str] = None
    jurisdiction: str
    enactment_date: Optional[date] = None
    effective_date: Optional[date] = None
    source_url: Optional[str] = None
    source_pdf: Optional[str] = None
    total_pages: Optional[int] = None
    enactment_start_page: Optional[int] = None
    total_sections_extracted: Optional[int] = None
    is_diglot: Optional[bool] = None
    extraction_status: Optional[str] = None
    manual_review_required: Optional[bool] = None
    parser_notes: Optional[Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class LawListResponse(BaseModel):
    """Paginated list response schema."""
    total: int
    limit: int
    offset: int
    laws: List[LawSummaryResponse]
