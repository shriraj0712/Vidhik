"""
Vidhik Platform - Advanced Legal Knowledge Base Router (Phase 17)
=================================================================
FastAPI route controllers exposing authoritative BNS, BNSS, BSA endpoints,
offences, punishments, procedures, evidence rules, predecessor correlations,
and verified Supreme Court landmark judgments.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from psycopg2.extras import RealDictCursor

from app.database import get_db
from app.services.knowledge_service import LegalKnowledgeService
from app.schemas.knowledge_base import (
    KnowledgeOverviewResponse,
    OffenceResponse,
    PunishmentResponse,
    ProcedureResponse,
    EvidenceProvisionResponse,
    PredecessorMappingResponse,
    JudgmentResponse,
    SectionFullContextResponse,
    ActMetadataResponse
)

router = APIRouter(prefix="/api/knowledge", tags=["Advanced Legal Knowledge Base (Phase 17)"])



@router.get("/overview", response_model=KnowledgeOverviewResponse)
def get_knowledge_overview(db: RealDictCursor = Depends(get_db)):
    """Returns overview statistics of the Phase 17 Advanced Legal Knowledge Base."""
    return LegalKnowledgeService.get_overview(cursor=db)


@router.get("/offences", response_model=List[OffenceResponse])
def list_offences(
    law_id: Optional[int] = Query(None, description="Filter by parent Act ID"),
    section_id: Optional[int] = Query(None, description="Filter by statutory section ID"),
    q: Optional[str] = Query(None, description="Search keyword matching offence name or description"),
    db: RealDictCursor = Depends(get_db)
):
    """Lists structured criminal offences with cognizable/bailable classifications."""
    return LegalKnowledgeService.get_offences(law_id=law_id, section_id=section_id, query=q, cursor=db)


@router.get("/punishments", response_model=List[PunishmentResponse])
def list_punishments(
    offence_id: Optional[int] = Query(None, description="Filter by offence ID"),
    section_id: Optional[int] = Query(None, description="Filter by section ID"),
    q: Optional[str] = Query(None, description="Search keyword in punishment description or fine"),
    db: RealDictCursor = Depends(get_db)
):
    """Lists statutory punishments, including community service and alternative sentences."""
    return LegalKnowledgeService.get_punishments(offence_id=offence_id, section_id=section_id, query=q, cursor=db)


@router.get("/procedures", response_model=List[ProcedureResponse])
def list_procedures(
    category: Optional[str] = Query(None, description="Filter by category (e.g. FIR, Arrest, Bail, Search & Seizure)"),
    q: Optional[str] = Query(None, description="Search keyword in title or statutory steps"),
    db: RealDictCursor = Depends(get_db)
):
    """Lists procedural workflows under the Bharatiya Nagarik Suraksha Sanhita, 2023."""
    return LegalKnowledgeService.get_procedures(category=category, query=q, cursor=db)


@router.get("/evidence", response_model=List[EvidenceProvisionResponse])
def list_evidence_provisions(
    provision_type: Optional[str] = Query(None, description="Filter by type (e.g. Electronic, Documentary, Witness)"),
    q: Optional[str] = Query(None, description="Search keyword in rule statement"),
    db: RealDictCursor = Depends(get_db)
):
    """Lists evidence rules and digital admissibility criteria under the Bharatiya Sakshya Adhiniyam, 2023."""
    return LegalKnowledgeService.get_evidence_provisions(provision_type=provision_type, query=q, cursor=db)


@router.get("/predecessors", response_model=List[PredecessorMappingResponse])
def list_predecessor_mappings(
    new_section: Optional[str] = Query(None, description="Filter by new BNS/BNSS/BSA section number"),
    old_law: Optional[str] = Query(None, description="Filter by old law (IPC, CrPC, Indian Evidence Act)"),
    old_section: Optional[str] = Query(None, description="Filter by old section number"),
    q: Optional[str] = Query(None, description="General search in mapping summaries"),
    db: RealDictCursor = Depends(get_db)
):
    """Lists exact comparative predecessor correspondences (IPC → BNS, CrPC → BNSS, IEA → BSA)."""
    return LegalKnowledgeService.get_predecessor_mappings(
        new_section_number=new_section,
        old_law_name=old_law,
        old_section_number=old_section,
        query=q,
        cursor=db
    )


@router.get("/judgments", response_model=List[JudgmentResponse])
def list_judgments(
    section_number: Optional[str] = Query(None, description="Filter by cited statutory section number"),
    court: Optional[str] = Query(None, description="Filter by court (default: Supreme Court of India)"),
    q: Optional[str] = Query(None, description="Search in case title, citation, or headnotes"),
    db: RealDictCursor = Depends(get_db)
):
    """Lists verified landmark judicial decisions interpreting relevant criminal law provisions."""
    return LegalKnowledgeService.get_judgments(section_number=section_number, query=q, cursor=db)


@router.get("/sections/{section_number}/context", response_model=SectionFullContextResponse)
def get_section_context(
    section_number: str,
    law: str = Query("BNS", description="Statutory code: BNS, BNSS, or BSA"),
    db: RealDictCursor = Depends(get_db)
):
    """
    Returns the comprehensive legal intelligence graph for a statutory section:
    Combines statutory text, offence details, punishments, procedures, evidence rules,
    predecessor mappings, and controlling judicial interpretations in a single unified response.
    """
    return LegalKnowledgeService.get_section_full_context(section_number=section_number, law_code=law, cursor=db)


@router.get("/acts", response_model=List[ActMetadataResponse])
def list_acts(db: RealDictCursor = Depends(get_db)):
    """Lists metadata for all 24 Bare Acts in the Phase 17 corpus."""
    return LegalKnowledgeService.get_acts(cursor=db)


@router.get("/acts/{act_id}")
def get_act_details(act_id: str, db: RealDictCursor = Depends(get_db)):
    """Returns statutory provisions and metadata for a specific Bare Act."""
    act_data = LegalKnowledgeService.get_act_by_id(act_id, cursor=db)
    if not act_data:
        raise HTTPException(status_code=404, detail=f"Bare Act '{act_id}' not found in knowledge base")
    return act_data


@router.get("/search")
def search_knowledge(
    q: str = Query(..., description="Search query across 24 Bare Acts"),
    act: Optional[str] = Query(None, description="Optional Act filter (e.g. BNS, POCSO, NI Act, etc.)"),
    limit: int = Query(20, ge=1, le=100),
    db: RealDictCursor = Depends(get_db)
):
    """Multi-statute search across all 24 Bare Acts."""
    results = LegalKnowledgeService.search_knowledge_base(query=q, act_filter=act, limit=limit, cursor=db)
    return {
        "query": q,
        "total_results": len(results),
        "results": results
    }

