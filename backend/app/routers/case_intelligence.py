"""
Vidhik Platform - Case Intelligence & Central Context API Router
================================================================
Exposes RESTful endpoints for the Case-Centric Legal Decision Support System:
- Complete Central Case Context
- Overall Case Description & Fact Extraction
- Database-Grounded Legal Analysis & Ranked Provisions
- Case-Specific Action Plan
- Document & Evidence Requirements Checklist
- Further Procedure Workflow
- Emotional State Analysis & Adaptive Guidance
- Database-Driven Matched Lawyer Recommendations
- Authority Recommendations
- Active Case Session Management & Switching
- Case Update Re-analysis
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg2.extras import RealDictCursor

from app.database import get_db
from app.services.auth_service import get_authenticated_user
from app.services.case_intelligence_service import CaseIntelligenceService
from app.schemas.case_intelligence import (
    CentralCaseContext,
    CaseSituationOverview,
    CaseLegalAnalysis,
    RankedLegalProvision,
    CaseActionPlan,
    CaseDocumentChecklist,
    CaseFurtherProcedure,
    CaseEmotionalAnalysis,
    CaseLawyerRecommendation,
    CaseAuthorityRecommendation,
    CaseCreateAndAnalyzeRequest,
    CaseUpdateAndReanalyzeRequest,
    ActiveCaseResponse
)

router = APIRouter(prefix="/api/cases", tags=["Case Intelligence & Context"])


# -------------------------------------------------------------
# 1. ACTIVE CASE PERSISTENCE & SWITCHING (FEATURE 8, 12)
# -------------------------------------------------------------
@router.get("/active", response_model=ActiveCaseResponse, summary="Get Current Active Case")
def get_active_case(
    current_user: dict = Depends(get_authenticated_user),
    db: RealDictCursor = Depends(get_db)
):
    """
    Returns the authenticated user's current active case and its complete context.
    If no active case is set, automatically falls back to their most recent case.
    """
    user_id = current_user["user_id"]
    active_case_id = CaseIntelligenceService.get_user_active_case(db, user_id)

    if not active_case_id:
        return ActiveCaseResponse(active_case_id=None, case=None, context=None)

    db.execute("""
        SELECT case_id, user_id, case_title, case_number, case_type,
               court_name, status, filing_date, incident_date, location,
               police_station, case_description, created_at, updated_at
        FROM cases WHERE case_id = %s AND user_id = %s;
    """, (active_case_id, user_id))
    case_row = db.fetchone()

    if not case_row:
        return ActiveCaseResponse(active_case_id=None, case=None, context=None)

    context = CaseIntelligenceService.get_case_context(db, active_case_id, user_id)
    return ActiveCaseResponse(
        active_case_id=active_case_id,
        case=dict(case_row),
        context=context
    )


@router.post("/{case_id}/set-active", summary="Set Active Case (Case Switching)")
def set_active_case(
    case_id: int,
    current_user: dict = Depends(get_authenticated_user),
    db: RealDictCursor = Depends(get_db)
):
    """
    Switches the user's active session to the specified case_id.
    Strictly verifies ownership: users can only activate their own cases.
    """
    user_id = current_user["user_id"]
    success = CaseIntelligenceService.set_user_active_case(db, user_id, case_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found or access denied."
        )
    return {
        "success": True,
        "message": f"Case {case_id} set as active current case.",
        "active_case_id": case_id
    }


# -------------------------------------------------------------
# 2. CREATE AND ANALYZE CASE (ONE-STEP ONBOARDING)
# -------------------------------------------------------------
@router.post("/create-and-analyze", response_model=CentralCaseContext, status_code=status.HTTP_201_CREATED, summary="Create and Analyze New Case")
def create_and_analyze_case(
    payload: CaseCreateAndAnalyzeRequest,
    current_user: dict = Depends(get_authenticated_user),
    db: RealDictCursor = Depends(get_db)
):
    """
    Registers a new legal case matter for the citizen and immediately runs
    the comprehensive Case Intelligence pipeline (understanding, legal ranking,
    actions, documents, procedure, emotions, lawyers, authorities).
    Sets the newly created case as the user's ACTIVE CASE.
    """
    user_id = current_user["user_id"]

    title = payload.title or payload.description[:60].strip() + ("..." if len(payload.description) > 60 else "")
    case_type = payload.case_type or "General Legal Matter"

    # Insert into cases table
    db.execute("""
        INSERT INTO cases (
            user_id, case_title, case_type, court_name,
            opposite_party, case_description, incident_date,
            location, police_station, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'active')
        RETURNING case_id;
    """, (
        user_id,
        title,
        case_type,
        payload.court_name,
        payload.opposite_party,
        payload.description,
        payload.incident_date,
        payload.location,
        payload.police_station
    ))
    row = db.fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="Failed to initialize legal case.")

    case_id = row["case_id"]

    # Generate sequential case number if not set
    case_number = f"CASE-{datetime.now().year}-{case_id:04d}"
    db.execute("UPDATE cases SET case_number = %s WHERE case_id = %s;", (case_number, case_id))

    # Set as active case
    CaseIntelligenceService.set_user_active_case(db, user_id, case_id)

    # Build and persist Central Case Context
    context = CaseIntelligenceService.build_and_save_context(
        db=db,
        case_id=case_id,
        user_id=user_id,
        title=title,
        description=payload.description,
        location=payload.location
    )

    return context


# -------------------------------------------------------------
# 3. COMPLETE CENTRAL CASE CONTEXT (FEATURE 10)
# -------------------------------------------------------------
@router.get("/{case_id}/context", response_model=CentralCaseContext, summary="Get Complete Central Case Context")
def get_complete_case_context(
    case_id: int,
    current_user: dict = Depends(get_authenticated_user),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves the complete Central Case Context.
    All modules draw from this centralized entity, ensuring zero duplicate overhead.
    Strictly isolated: returns 404 if case does not belong to user.
    """
    user_id = current_user["user_id"]
    context = CaseIntelligenceService.get_case_context(db, case_id, user_id)
    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found or access denied."
        )
    return context


# -------------------------------------------------------------
# 4. MODULAR ENDPOINTS FOR CASE CONTEXT CONSUMPTION (FEATURE 11)
# -------------------------------------------------------------
@router.get("/{case_id}/situation-overview", response_model=CaseSituationOverview, summary="Get Situation Overview (Feature 1)")
def get_situation_overview(
    case_id: int,
    current_user: dict = Depends(get_authenticated_user),
    db: RealDictCursor = Depends(get_db)
):
    """Returns the cautious plain-language case situation summary, extracted facts, issues, and uncertain facts."""
    context = get_complete_case_context(case_id, current_user, db)
    return CaseSituationOverview(
        situation_summary=context.situation_summary,
        explicit_facts=context.explicit_facts,
        extracted_facts=context.extracted_facts,
        identified_issues=context.identified_issues,
        uncertain_facts=context.uncertain_facts,
        missing_information=context.missing_information,
        case_category=context.case_category,
        legal_domain=context.legal_domain,
        jurisdiction=context.jurisdiction,
        urgency=context.urgency
    )


@router.get("/{case_id}/legal-analysis", response_model=CaseLegalAnalysis, summary="Get Legal Analysis & Ranked Provisions (Feature 2, 3)")
def get_legal_analysis(
    case_id: int,
    current_user: dict = Depends(get_authenticated_user),
    db: RealDictCursor = Depends(get_db)
):
    """Returns database-grounded statutory provisions, deterministic ranking, and simple explanations."""
    context = get_complete_case_context(case_id, current_user, db)
    return CaseLegalAnalysis(
        case_id=case_id,
        case_category=context.case_category,
        legal_domain=context.legal_domain,
        ranked_provisions=context.ranked_provisions,
        total_provisions_found=len(context.ranked_provisions)
    )


@router.get("/{case_id}/legal-ranking", response_model=List[RankedLegalProvision], summary="Get Ranked Legal Provisions (Feature 2, 3)")
def get_legal_ranking(
    case_id: int,
    current_user: dict = Depends(get_authenticated_user),
    db: RealDictCursor = Depends(get_db)
):
    """Returns ranked legal provisions for the active case."""
    context = get_complete_case_context(case_id, current_user, db)
    return context.ranked_provisions


@router.get("/{case_id}/action-plan", response_model=CaseActionPlan, summary="Get Recommended Actions (Feature 4)")
def get_action_plan(
    case_id: int,
    current_user: dict = Depends(get_authenticated_user),
    db: RealDictCursor = Depends(get_db)
):
    """Returns case-specific immediate actions, next steps, and optional steps."""
    context = get_complete_case_context(case_id, current_user, db)
    raw = context.recommended_actions or {}
    return CaseActionPlan(
        case_id=case_id,
        immediate_actions=raw.get("immediate_actions", []),
        recommended_next_steps=raw.get("recommended_next_steps", []),
        optional_supporting_actions=raw.get("optional_supporting_actions", [])
    )


@router.get("/{case_id}/documents", response_model=CaseDocumentChecklist, summary="Get Document & Evidence Checklist (Feature 5)")
def get_document_checklist(
    case_id: int,
    current_user: dict = Depends(get_authenticated_user),
    db: RealDictCursor = Depends(get_db)
):
    """Returns case-specific required, important, and supporting documents checklist."""
    context = get_complete_case_context(case_id, current_user, db)
    raw = context.required_documents or {}
    return CaseDocumentChecklist(
        case_id=case_id,
        required_documents=raw.get("required_documents", []),
        important_documents=raw.get("important_documents", []),
        supporting_documents=raw.get("supporting_documents", [])
    )


@router.get("/{case_id}/procedure", response_model=CaseFurtherProcedure, summary="Get Further Procedure (Feature 6)")
def get_procedure(
    case_id: int,
    current_user: dict = Depends(get_authenticated_user),
    db: RealDictCursor = Depends(get_db)
):
    """Returns the likely procedural pathway and timeline grounded in applicable statutes."""
    context = get_complete_case_context(case_id, current_user, db)
    raw = context.further_procedure or {}
    return CaseFurtherProcedure(
        case_id=case_id,
        legal_domain=context.legal_domain,
        procedural_pathway=raw.get("procedural_pathway", []),
        overall_timeline=raw.get("overall_timeline"),
        statutory_source=raw.get("statutory_source")
    )


@router.get("/{case_id}/emotional-analysis", response_model=CaseEmotionalAnalysis, summary="Get Emotional State Analysis (Feature 7)")
def get_emotional_analysis(
    case_id: int,
    current_user: dict = Depends(get_authenticated_user),
    db: RealDictCursor = Depends(get_db)
):
    """Returns detected emotional indicators and adaptive communication instructions."""
    context = get_complete_case_context(case_id, current_user, db)
    raw = context.emotional_indicators or {}
    return CaseEmotionalAnalysis(
        case_id=case_id,
        detected_indicators=raw.get("detected_indicators", ["Neutral/Calm"]),
        primary_tone=raw.get("primary_tone", "Neutral/Calm"),
        urgency_level=raw.get("urgency_level", "Medium"),
        communication_adaptation=raw.get("communication_adaptation", "Balanced factual legal guidance."),
        safety_indicators_present=raw.get("safety_indicators_present", False),
        immediate_safety_notice=raw.get("immediate_safety_notice")
    )


@router.get("/{case_id}/lawyer-recommendation", response_model=CaseLawyerRecommendation, summary="Get Matched Lawyers (Feature 14)")
def get_lawyer_recommendation(
    case_id: int,
    current_user: dict = Depends(get_authenticated_user),
    db: RealDictCursor = Depends(get_db)
):
    """Returns real lawyers matched from the database with match scores and explicit match reasons."""
    context = get_complete_case_context(case_id, current_user, db)
    return CaseLawyerRecommendation(
        case_id=case_id,
        case_category=context.case_category,
        legal_domain=context.legal_domain,
        required_expertise=[context.legal_domain, context.case_category],
        jurisdiction=context.jurisdiction,
        recommended_lawyers=context.recommended_lawyers,
        total_lawyers_matched=len(context.recommended_lawyers)
    )


@router.get("/{case_id}/authority-recommendation", response_model=CaseAuthorityRecommendation, summary="Get Authority Recommendations")
def get_authority_recommendation(
    case_id: int,
    current_user: dict = Depends(get_authenticated_user),
    db: RealDictCursor = Depends(get_db)
):
    """Returns recommended judicial, administrative, and consumer authorities for the case."""
    context = get_complete_case_context(case_id, current_user, db)
    return CaseAuthorityRecommendation(
        case_id=case_id,
        primary_authorities=context.recommended_authorities,
        precedent_decisions=[],
        source_status="SOURCE_VERIFIED"
    )


# -------------------------------------------------------------
# 5. CASE UPDATE & RE-ANALYSIS (FEATURE 17)
# -------------------------------------------------------------
@router.post("/{case_id}/update-and-reanalyze", response_model=CentralCaseContext, summary="Update Case with New Facts & Re-evaluate (Feature 17)")
def update_and_reanalyze(
    case_id: int,
    payload: CaseUpdateAndReanalyzeRequest,
    current_user: dict = Depends(get_authenticated_user),
    db: RealDictCursor = Depends(get_db)
):
    """
    Incorporates newly provided facts into the active case and re-evaluates all affected modules:
    legal provisions, ranking, authorities, lawyers, action plan, documents, and procedure.
    Increments analysis version and preserves case history.
    """
    user_id = current_user["user_id"]
    try:
        updated_context = CaseIntelligenceService.update_and_reanalyze_case(
            db=db,
            case_id=case_id,
            user_id=user_id,
            additional_information=payload.additional_information,
            updated_location=payload.updated_location
        )
        return updated_context
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
