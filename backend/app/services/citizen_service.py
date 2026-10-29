"""
Vidhik Platform - Citizen / User Module Service Layer
======================================================
Provides business logic, parameterized SQL execution, and strict cross-user
authorization boundaries for the Citizen Workspace:
- Dashboard Metrics & KPI Aggregations
- Personal Case Management (Ownership Guarded)
- Document Uploads & Case Attachments
- Court Hearing Calendars
- Statutory Section Bookmarking
- Research Search History
- User Notifications
- Procedure Checklist Persistence
"""

import json
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
from psycopg2.extras import RealDictCursor

from datetime import datetime, date
from app.schemas.citizen import (
    CitizenProfileUpdate,
    CitizenCaseCreate,
    CitizenCaseCourtReferenceUpdate,
    CitizenDocumentUpload,
    BookmarkCreate
)
from app.core.cnr_validator import validate_cnr, normalize_cnr, get_official_ecourts_portal_url


class CitizenService:

    # --------------------------------------------------------------------------
    # 1. CITIZEN DASHBOARD
    # --------------------------------------------------------------------------
    @staticmethod
    def get_dashboard_metrics(db: RealDictCursor, user_id: int) -> dict:
        """
        Aggregates personalized dashboard statistics for the authenticated citizen.
        Queries live database tables for cases, documents, hearings, notifications,
        document analyses, and bookmarks.
        """
        # 1. Case counts
        db.execute("""
            SELECT
                COUNT(*) FILTER (WHERE status = 'active') AS active_cases,
                COUNT(*) AS total_cases
            FROM cases
            WHERE user_id = %s;
        """, (user_id,))
        case_stats = db.fetchone() or {"active_cases": 0, "total_cases": 0}

        # 2. Document count (uploaded by user or on user's cases)
        db.execute("""
            SELECT COUNT(DISTINCT cd.document_id) AS doc_count
            FROM case_documents cd
            JOIN cases c ON cd.case_id = c.case_id
            WHERE c.user_id = %s OR cd.client_id = %s;
        """, (user_id, user_id))
        doc_res = db.fetchone()
        doc_count = doc_res["doc_count"] if doc_res else 0

        # 3. Upcoming hearings
        db.execute("""
            SELECT COUNT(*) AS hearing_count
            FROM reminders
            WHERE user_id = %s AND reminder_date >= CURRENT_DATE AND status != 'completed';
        """, (user_id,))
        hearing_res = db.fetchone()
        upcoming_hearings_count = hearing_res["hearing_count"] if hearing_res else 0

        # 4. Unread notifications
        db.execute("""
            SELECT COUNT(*) AS unread
            FROM notifications
            WHERE user_id = %s AND is_read = FALSE;
        """, (user_id,))
        notif_res = db.fetchone()
        unread_notifications_count = notif_res["unread"] if notif_res else 0

        # 5. Recent document analyses count
        db.execute("""
            SELECT COUNT(*) AS analyses_count
            FROM legal_document_analyses
            WHERE user_id = %s;
        """, (user_id,))
        analyses_res = db.fetchone()
        recent_analyses_count = analyses_res["analyses_count"] if analyses_res else 0

        # 6. Bookmarked sections count
        db.execute("""
            SELECT COUNT(*) AS bookmark_count
            FROM user_saved_sections
            WHERE user_id = %s;
        """, (user_id,))
        bm_res = db.fetchone()
        saved_sections_count = bm_res["bookmark_count"] if bm_res else 0

        # 7. Tracked procedures count
        db.execute("""
            SELECT COUNT(*) AS proc_count
            FROM user_procedure_trackers
            WHERE user_id = %s;
        """, (user_id,))
        proc_res = db.fetchone()
        tracked_procedures_count = proc_res["proc_count"] if proc_res else 0

        # 8. Recent Cases (top 5)
        db.execute("""
            SELECT
                c.case_id, c.case_title, c.case_number, c.case_type,
                c.court_name, c.status, c.filing_date, c.updated_at,
                l.full_name AS assigned_lawyer_name
            FROM cases c
            LEFT JOIN lawyers l ON c.assigned_lawyer_id = l.lawyer_id
            WHERE c.user_id = %s
            ORDER BY c.updated_at DESC
            LIMIT 5;
        """, (user_id,))
        recent_cases = []
        for row in db.fetchall():
            c = dict(row)
            c["title"] = c.get("case_title")
            c["court"] = c.get("court_name")
            c["lawyer_name"] = c.get("assigned_lawyer_name")
            recent_cases.append(c)

        # 9. Upcoming Hearings (top 5)
        db.execute("""
            SELECT
                r.reminder_id, r.case_id, r.title, r.reminder_date,
                r.reminder_time, r.court_name, r.judge_name, r.priority,
                r.status, c.case_title
            FROM reminders r
            LEFT JOIN cases c ON r.case_id = c.case_id
            WHERE r.user_id = %s AND r.reminder_date >= CURRENT_DATE
            ORDER BY r.reminder_date ASC, r.reminder_time ASC
            LIMIT 5;
        """, (user_id,))
        upcoming_hearings = [dict(row) for row in db.fetchall()]

        # 10. Recent Documents (top 5)
        db.execute("""
            SELECT
                cd.document_id, cd.case_id, cd.document_name,
                cd.document_type, cd.file_size_bytes, cd.mime_type,
                cd.created_at, c.case_title
            FROM case_documents cd
            JOIN cases c ON cd.case_id = c.case_id
            WHERE c.user_id = %s OR cd.client_id = %s
            ORDER BY cd.created_at DESC
            LIMIT 5;
        """, (user_id, user_id))
        recent_documents = [dict(row) for row in db.fetchall()]

        # 11. Recent Document Analyses (top 5)
        db.execute("""
            SELECT
                analysis_id, document_name, document_type,
                summary, created_at
            FROM legal_document_analyses
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 5;
        """, (user_id,))
        recent_analyses = [dict(row) for row in db.fetchall()]

        # 12. Recent Notifications (top 5)
        db.execute("""
            SELECT
                notification_id, reminder_id, title,
                message, notification_type, is_read, created_at
            FROM notifications
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 5;
        """, (user_id,))
        recent_notifications = [dict(row) for row in db.fetchall()]

        metrics_data = {
            "active_cases": int(case_stats.get("active_cases") or 0),
            "total_cases": int(case_stats.get("total_cases") or 0),
            "total_documents": doc_count,
            "upcoming_hearings": upcoming_hearings_count,
            "saved_sections": saved_sections_count,
            "unread_notifications": unread_notifications_count,
            "recent_analyses": recent_analyses_count,
            "tracked_procedures": tracked_procedures_count,
        }

        return {
            "metrics": metrics_data,
            "active_cases": metrics_data["active_cases"],
            "total_cases": metrics_data["total_cases"],
            "documents_count": doc_count,
            "upcoming_hearings_count": upcoming_hearings_count,
            "unread_notifications_count": unread_notifications_count,
            "recent_analyses_count": recent_analyses_count,
            "saved_sections_count": saved_sections_count,
            "tracked_procedures_count": tracked_procedures_count,
            "recent_cases": recent_cases,
            "upcoming_hearings": upcoming_hearings,
            "recent_documents": recent_documents,
            "recent_analyses": recent_analyses,
            "notifications": recent_notifications
        }

    # --------------------------------------------------------------------------
    # 2. CITIZEN CASES
    # --------------------------------------------------------------------------
    @staticmethod
    def list_cases(
        db: RealDictCursor,
        user_id: int,
        search: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> List[dict]:
        """
        Lists all cases belonging to the authenticated citizen.
        Strictly scopes by cases.user_id = user_id.
        """
        query = """
            SELECT
                c.case_id, c.case_title, c.case_number, c.case_type,
                c.court_name, c.opposite_party, c.status, c.filing_date,
                c.incident_date, c.location, c.police_station, c.case_description,
                c.cnr_number, c.court_source, c.official_case_url,
                c.last_verified_at, c.external_status, c.external_next_hearing_date,
                c.assigned_lawyer_id, c.created_at, c.updated_at,
                l.full_name AS assigned_lawyer_name,
                l.phone AS assigned_lawyer_phone,
                l.email AS assigned_lawyer_email,
                (SELECT COUNT(*) FROM case_documents WHERE case_id = c.case_id) AS documents_count,
                (SELECT COUNT(*) FROM reminders WHERE case_id = c.case_id) AS hearings_count
            FROM cases c
            LEFT JOIN lawyers l ON c.assigned_lawyer_id = l.lawyer_id
            WHERE c.user_id = %s
        """
        params: List[Any] = [user_id]

        if status_filter:
            query += " AND c.status = %s"
            params.append(status_filter.strip().lower())

        if search:
            search_param = f"%{search.strip()}%"
            query += """ AND (
                c.case_title ILIKE %s OR
                c.case_number ILIKE %s OR
                c.court_name ILIKE %s OR
                c.opposite_party ILIKE %s OR
                c.cnr_number ILIKE %s
            )"""
            params.extend([search_param, search_param, search_param, search_param, search_param])

        query += " ORDER BY c.updated_at DESC;"
        db.execute(query, tuple(params))
        cases = []
        for row in db.fetchall():
            c = dict(row)
            c["title"] = c.get("case_title")
            c["court"] = c.get("court_name")
            c["description"] = c.get("case_description")
            c["lawyer_name"] = c.get("assigned_lawyer_name")
            cases.append(c)
        return cases

    @staticmethod
    def get_case_detail(db: RealDictCursor, user_id: int, case_id: int) -> Optional[dict]:
        """
        Retrieves detailed case workspace for a case owned by the citizen.
        CRITICAL AUTHORIZATION: Strictly verifies case.user_id == user_id.
        CONFIDENTIALITY: Lawyer-private case_notes are strictly excluded.
        """
        # Fetch base case
        db.execute("""
            SELECT
                c.case_id, c.case_title, c.case_number, c.case_type,
                c.court_name, c.opposite_party, c.status, c.filing_date,
                c.incident_date, c.location, c.police_station, c.case_description,
                c.cnr_number, c.court_source, c.official_case_url,
                c.last_verified_at, c.external_status, c.external_next_hearing_date,
                c.assigned_lawyer_id, c.created_at, c.updated_at,
                l.full_name AS assigned_lawyer_name,
                l.phone AS assigned_lawyer_phone,
                l.email AS assigned_lawyer_email,
                l.specialization AS assigned_lawyer_specialization
            FROM cases c
            LEFT JOIN lawyers l ON c.assigned_lawyer_id = l.lawyer_id
            WHERE c.case_id = %s AND c.user_id = %s;
        """, (case_id, user_id))
        case_row = db.fetchone()
        if not case_row:
            return None

        case_data = dict(case_row)
        case_data["title"] = case_data.get("case_title")
        case_data["court"] = case_data.get("court_name")
        case_data["description"] = case_data.get("case_description")
        case_data["lawyer_name"] = case_data.get("assigned_lawyer_name")
        if case_data.get("assigned_lawyer_id"):
            case_data["lawyer"] = {
                "lawyer_id": case_data.get("assigned_lawyer_id"),
                "full_name": case_data.get("assigned_lawyer_name"),
                "phone": case_data.get("assigned_lawyer_phone"),
                "email": case_data.get("assigned_lawyer_email"),
                "specialization": case_data.get("assigned_lawyer_specialization")
            }
        else:
            case_data["lawyer"] = None

        # 1. Documents
        db.execute("""
            SELECT document_id, case_id, document_name, document_type,
                   file_path, file_size_bytes, mime_type, upload_status,
                   description, created_at
            FROM case_documents
            WHERE case_id = %s
            ORDER BY created_at DESC;
        """, (case_id,))
        case_data["documents"] = [dict(d) for d in db.fetchall()]

        # 2. Hearings
        db.execute("""
            SELECT reminder_id, case_id, title, description,
                   reminder_type, reminder_date, reminder_time,
                   court_name, judge_name, status, priority, notes,
                   created_at
            FROM reminders
            WHERE case_id = %s
            ORDER BY reminder_date ASC, reminder_time ASC;
        """, (case_id,))
        case_data["hearings"] = [dict(h) for h in db.fetchall()]

        # 3. Procedural Timeline Updates
        db.execute("""
            SELECT update_id, case_id, update_type, update_title,
                   update_description, status, updated_by, update_date
            FROM case_updates
            WHERE case_id = %s
            ORDER BY update_date DESC, created_at DESC;
        """, (case_id,))
        case_data["updates"] = [dict(u) for u in db.fetchall()]

        # 4. Linked Statutory Provisions
        db.execute("""
            SELECT
                cls.section_id, cls.relevance_score, cls.explanation,
                s.section_number, s.section_title,
                l.law_id, l.law_name
            FROM case_legal_sections cls
            JOIN sections s ON cls.section_id = s.section_id
            JOIN laws l ON s.law_id = l.law_id
            WHERE cls.case_id = %s
            ORDER BY cls.relevance_score DESC;
        """, (case_id,))
        case_data["legal_sections"] = [dict(sec) for sec in db.fetchall()]

        # 5. Official Court Reference Block
        court_ref = {
            "cnr_number": case_row.get("cnr_number"),
            "court_source": case_row.get("court_source") or "eCourts India",
            "official_case_url": case_row.get("official_case_url") or (get_official_ecourts_portal_url() if case_row.get("cnr_number") else None),
            "last_verified_at": case_row.get("last_verified_at"),
            "external_status": case_row.get("external_status"),
            "external_next_hearing_date": case_row.get("external_next_hearing_date"),
            "is_verified": case_row.get("last_verified_at") is not None,
            "portal_url": get_official_ecourts_portal_url()
        }
        case_data["court_reference"] = court_ref

        # NOTE: case_notes are intentionally NOT queried or returned.
        return case_data

    @staticmethod
    def create_case(
        db: RealDictCursor,
        user_id: int,
        payload: Optional[CitizenCaseCreate] = None,
        data: Optional[CitizenCaseCreate] = None
    ) -> dict:
        """
        Allows an authenticated citizen to submit/register a new legal case matter.
        """
        payload = payload or data
        if not payload:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing case data.")
        title = (payload.case_title or payload.title or "").strip()
        court = (payload.court_name or payload.court or "").strip() or None
        desc = (payload.case_description or payload.description or "").strip() or None
        ctype = (payload.case_type or "General Legal Matter").strip()
        opp = (payload.opposite_party or "").strip() or None
        loc = (payload.location or "").strip() or None
        ps = (payload.police_station or "").strip() or None

        validated_cnr = None
        if payload.cnr_number and str(payload.cnr_number).strip():
            is_valid, normalized, err = validate_cnr(payload.cnr_number)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=err or "Invalid CNR Number format."
                )
            validated_cnr = normalized

        official_url = payload.official_case_url or (get_official_ecourts_portal_url() if validated_cnr else None)
        court_src = payload.court_source or "eCourts India"

        db.execute("""
            INSERT INTO cases (
                user_id, case_title, case_type, court_name,
                opposite_party, case_description, incident_date,
                location, police_station, status,
                cnr_number, court_source, official_case_url,
                external_status, external_next_hearing_date
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'active', %s, %s, %s, %s, %s)
            RETURNING *;
        """, (
            user_id,
            title,
            ctype,
            court,
            opp,
            desc,
            payload.incident_date,
            loc,
            ps,
            validated_cnr,
            court_src,
            official_url,
            payload.external_status,
            payload.external_next_hearing_date
        ))
        row = db.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create legal case."
            )
        new_case = dict(row)
        new_case["title"] = new_case.get("case_title")
        new_case["court"] = new_case.get("court_name")
        new_case["description"] = new_case.get("case_description")
        case_id = new_case["case_id"]

        # Insert procedural registration update
        activity_msg = 'Legal matter was registered directly by the citizen.'
        if validated_cnr:
            activity_msg += f" Linked with eCourts CNR: {validated_cnr}."

        db.execute("""
            INSERT INTO case_updates (
                case_id, update_type, update_title,
                update_description, status, updated_by
            ) VALUES (
                %s, 'Registration', 'Matter Registered via Citizen Portal',
                %s, 'active', 'Citizen'
            );
        """, (case_id, activity_msg))

        # If an official next hearing date is provided, create initial hearing reminder
        if payload.external_next_hearing_date:
            db.execute("""
                INSERT INTO reminders (
                    case_id, user_id, title, description, reminder_type,
                    reminder_date, reminder_time, court_name, status, priority, notes
                ) VALUES (
                    %s, %s, %s, %s, 'hearing',
                    %s, '10:30:00', %s, 'scheduled', 'high', 'Initial scheduled court hearing.'
                );
            """, (
                case_id, user_id,
                f"Court Hearing: {title}",
                f"Scheduled court appearance for matter '{title}'.",
                payload.external_next_hearing_date,
                court
            ))

        # Create confirmation notification for citizen
        db.execute("""
            INSERT INTO notifications (
                user_id, title, message, notification_type
            ) VALUES (
                %s, 'Legal Matter Registered',
                %s, 'case_update'
            );
        """, (user_id, f"Your matter '{title}' has been recorded in your portal."))

        db.connection.commit()
        return new_case

    @staticmethod
    def update_court_reference(
        db: RealDictCursor,
        user_id: int,
        case_id: int,
        payload: Optional[CitizenCaseCourtReferenceUpdate] = None,
        data: Optional[CitizenCaseCourtReferenceUpdate] = None
    ) -> dict:
        """
        Allows an authenticated citizen to record user-verified official court reference information
        (CNR, official stage, next hearing date) for their personal case.
        Strictly enforces cases.user_id = user_id ownership boundary.
        """
        payload = payload or data
        if not payload:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing court reference data.")
        db.execute("""
            SELECT case_id, user_id, case_title, court_name, cnr_number
            FROM cases
            WHERE case_id = %s AND user_id = %s;
        """, (case_id, user_id))
        c_row = db.fetchone()
        if not c_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case #{case_id} not found or unauthorized."
            )

        validated_cnr = c_row.get("cnr_number")
        if payload.cnr_number is not None:
            if str(payload.cnr_number).strip():
                is_valid, normalized, err = validate_cnr(payload.cnr_number)
                if not is_valid:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=err or "Invalid CNR Number format."
                    )
                validated_cnr = normalized
            else:
                validated_cnr = None

        now = datetime.now()
        official_url = payload.official_case_url or (get_official_ecourts_portal_url() if validated_cnr else None)
        court_src = payload.court_source or "eCourts India"

        # Update official reference columns
        db.execute("""
            UPDATE cases
            SET cnr_number = %s,
                court_source = %s,
                official_case_url = %s,
                last_verified_at = %s,
                external_status = %s,
                external_next_hearing_date = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE case_id = %s AND user_id = %s
            RETURNING case_id;
        """, (
            validated_cnr, court_src, official_url, now,
            payload.external_status, payload.external_next_hearing_date,
            case_id, user_id
        ))

        # Record procedural update
        desc = f"Verified on official eCourts portal: CNR {validated_cnr or 'N/A'}"
        if payload.external_status:
            desc += f", Stage: {payload.external_status}"
        if payload.external_next_hearing_date:
            desc += f", Next Hearing: {payload.external_next_hearing_date}"

        db.execute("""
            INSERT INTO case_updates (
                case_id, update_type, update_title, update_description, status, updated_by
            ) VALUES (
                %s, 'Court Reference Update', 'Official Court Reference Verified', %s, 'active', 'Citizen'
            );
        """, (case_id, desc))

        # Synchronize hearing reminder if requested
        case_name = c_row.get("case_title") or c_row.get("title") or "Legal Matter"
        if payload.sync_hearing_reminder and payload.external_next_hearing_date:
            db.execute("""
                SELECT reminder_id FROM reminders
                WHERE case_id = %s AND reminder_date = %s AND reminder_type = 'hearing';
            """, (case_id, payload.external_next_hearing_date))
            existing_hearing = db.fetchone()

            if not existing_hearing:
                db.execute("""
                    INSERT INTO reminders (
                        case_id, user_id, title, description, reminder_type,
                        reminder_date, reminder_time, court_name, status, priority, notes
                    ) VALUES (
                        %s, %s, %s, %s, 'hearing',
                        %s, '10:30:00', %s, 'scheduled', 'high', 'Synchronized from verified eCourts record.'
                    );
                """, (
                    case_id, user_id,
                    f"Official Hearing: {payload.external_status or 'Court Listing'}",
                    f"Scheduled hearing on official record for matter '{case_name}'.",
                    payload.external_next_hearing_date,
                    c_row.get("court_name")
                ))

        # Notification to citizen
        db.execute("""
            INSERT INTO notifications (
                user_id, title, message, notification_type
            ) VALUES (
                %s, 'Court Reference Verified',
                %s, 'case_update'
            );
        """, (
            user_id,
            f"Official court reference for '{case_name}' has been updated with CNR {validated_cnr or 'N/A'}."
        ))

        db.connection.commit()

        updated_detail = CitizenService.get_case_detail(db, user_id, case_id)
        if not updated_detail:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated case.")
        return updated_detail

    # --------------------------------------------------------------------------
    # 3. CITIZEN DOCUMENTS
    # --------------------------------------------------------------------------
    @staticmethod
    def list_documents(
        db: RealDictCursor,
        user_id: int,
        case_id: Optional[int] = None
    ) -> List[dict]:
        """
        Lists documents belonging to the authenticated citizen or attached
        to their personal cases.
        """
        query = """
            SELECT
                cd.document_id, cd.case_id, cd.document_name,
                cd.document_type, cd.file_path, cd.file_size_bytes,
                cd.mime_type, cd.upload_status, cd.description,
                cd.created_at, c.case_title
            FROM case_documents cd
            JOIN cases c ON cd.case_id = c.case_id
            WHERE (c.user_id = %s OR cd.client_id = %s)
        """
        params: List[Any] = [user_id, user_id]

        if case_id:
            query += " AND cd.case_id = %s"
            params.append(case_id)

        query += " ORDER BY cd.created_at DESC;"
        db.execute(query, tuple(params))
        return [dict(row) for row in db.fetchall()]

    @staticmethod
    def upload_document(
        db: RealDictCursor,
        user_id: int,
        payload: CitizenDocumentUpload
    ) -> dict:
        """
        Uploads/catalogs a document to a case owned by the citizen.
        CRITICAL AUTHORIZATION: Validates case belongs to authenticated citizen.
        """
        db.execute("SELECT case_id, case_title FROM cases WHERE case_id = %s AND user_id = %s;", (payload.case_id, user_id))
        case = db.fetchone()
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or unauthorized to upload to this matter."
            )

        fake_path = payload.file_path or f"/documents/cases/{payload.case_id}/{payload.document_name}"

        db.execute("""
            INSERT INTO case_documents (
                case_id, client_id, document_name, document_type,
                file_path, file_size_bytes, mime_type, upload_status, description
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, 'uploaded', %s
            )
            RETURNING *;
        """, (
            payload.case_id,
            user_id,
            payload.document_name.strip(),
            payload.document_type.strip(),
            fake_path,
            payload.file_size_bytes or 0,
            payload.mime_type or "application/pdf",
            payload.description
        ))
        new_doc = db.fetchone()
        if not new_doc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload document."
            )

        # Log case update
        db.execute("""
            INSERT INTO case_updates (
                case_id, update_type, update_title,
                update_description, status, updated_by
            ) VALUES (
                %s, 'Document Upload', %s,
                %s, 'active', 'Citizen'
            );
        """, (
            payload.case_id,
            f"Document Uploaded: {payload.document_name}",
            f"Citizen attached document '{payload.document_name}' ({payload.document_type})."
        ))

        db.connection.commit()
        return dict(new_doc)

    # --------------------------------------------------------------------------
    # 4. CITIZEN HEARINGS
    # --------------------------------------------------------------------------
    @staticmethod
    def list_hearings(db: RealDictCursor, user_id: int) -> List[dict]:
        """
        Retrieves court hearings and reminders scheduled for the citizen.
        """
        db.execute("""
            SELECT
                r.reminder_id, r.case_id, r.title, r.description,
                r.reminder_type, r.reminder_date, r.reminder_time,
                r.court_name, r.judge_name, r.status, r.priority,
                r.notes, r.created_at, c.case_title
            FROM reminders r
            JOIN cases c ON r.case_id = c.case_id
            WHERE r.user_id = %s
            ORDER BY r.reminder_date ASC, r.reminder_time ASC;
        """, (user_id,))
        return [dict(row) for row in db.fetchall()]

    # --------------------------------------------------------------------------
    # 5. CITIZEN PROFILE
    # --------------------------------------------------------------------------
    @staticmethod
    def get_profile(db: RealDictCursor, user_id: int) -> dict:
        """
        Retrieves citizen user and profile details.
        """
        db.execute("""
            SELECT
                u.user_id, u.username, u.email, u.full_name, u.phone, u.role, u.created_at,
                up.date_of_birth, up.address, up.city, up.state, up.pincode,
                COALESCE(up.preferred_language, 'en') AS preferred_language,
                up.profile_image_url, up.occupation,
                up.emergency_contact, up.updated_at
            FROM users u
            LEFT JOIN user_profiles up ON u.user_id = up.user_id
            WHERE u.user_id = %s;
        """, (user_id,))
        row = db.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found.")
        return dict(row)

    @staticmethod
    def update_profile(db: RealDictCursor, user_id: int, payload: CitizenProfileUpdate) -> dict:
        """
        Updates personal profile information for the authenticated citizen.
        """
        # 1. Update users table if full_name or phone changed
        if payload.full_name or payload.phone is not None:
            user_updates = []
            user_params: List[Any] = []
            if payload.full_name:
                user_updates.append("full_name = %s")
                user_params.append(payload.full_name.strip())
            if payload.phone is not None:
                user_updates.append("phone = %s")
                user_params.append(payload.phone.strip() if payload.phone else None)
            user_updates.append("updated_at = CURRENT_TIMESTAMP")
            user_params.append(user_id)
            db.execute(f"UPDATE users SET {', '.join(user_updates)} WHERE user_id = %s;", tuple(user_params))

        # 2. Update user_profiles
        db.execute("""
            INSERT INTO user_profiles (
                user_id, date_of_birth, address, city, state, pincode,
                preferred_language, occupation, emergency_contact, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
            )
            ON CONFLICT (user_id) DO UPDATE SET
                date_of_birth = COALESCE(EXCLUDED.date_of_birth, user_profiles.date_of_birth),
                address = COALESCE(EXCLUDED.address, user_profiles.address),
                city = COALESCE(EXCLUDED.city, user_profiles.city),
                state = COALESCE(EXCLUDED.state, user_profiles.state),
                pincode = COALESCE(EXCLUDED.pincode, user_profiles.pincode),
                preferred_language = COALESCE(EXCLUDED.preferred_language, user_profiles.preferred_language),
                occupation = COALESCE(EXCLUDED.occupation, user_profiles.occupation),
                emergency_contact = COALESCE(EXCLUDED.emergency_contact, user_profiles.emergency_contact),
                updated_at = CURRENT_TIMESTAMP;
        """, (
            user_id,
            payload.date_of_birth,
            payload.address.strip() if payload.address else None,
            payload.city.strip() if payload.city else None,
            payload.state.strip() if payload.state else None,
            payload.pincode.strip() if payload.pincode else None,
            payload.preferred_language or "en",
            payload.occupation.strip() if payload.occupation else None,
            payload.emergency_contact.strip() if payload.emergency_contact else None
        ))

        db.connection.commit()
        return CitizenService.get_profile(db, user_id)

    # --------------------------------------------------------------------------
    # 6. BOOKMARKS (SAVED SECTIONS)
    # --------------------------------------------------------------------------
    @staticmethod
    def list_bookmarks(db: RealDictCursor, user_id: int) -> List[dict]:
        """
        Lists all statutory provisions bookmarked by the authenticated citizen.
        Joined with sections and laws tables.
        """
        db.execute("""
            SELECT
                b.bookmark_id, b.user_id, b.section_id,
                s.section_number, s.section_title,
                l.law_id, l.law_name,
                b.notes, b.tag, b.created_at
            FROM user_saved_sections b
            JOIN sections s ON b.section_id = s.section_id
            JOIN laws l ON s.law_id = l.law_id
            WHERE b.user_id = %s
            ORDER BY b.created_at DESC;
        """, (user_id,))
        return [dict(row) for row in db.fetchall()]

    @staticmethod
    def create_bookmark(db: RealDictCursor, user_id: int, payload: BookmarkCreate) -> dict:
        """
        Adds a statutory section to citizen bookmarks. Idempotent upsert.
        """
        # Validate section exists
        db.execute("SELECT section_id FROM sections WHERE section_id = %s;", (payload.section_id,))
        if not db.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Section with ID {payload.section_id} does not exist in the legal corpus."
            )

        db.execute("""
            INSERT INTO user_saved_sections (user_id, section_id, notes, tag)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, section_id) DO UPDATE SET
                notes = COALESCE(EXCLUDED.notes, user_saved_sections.notes),
                tag = COALESCE(EXCLUDED.tag, user_saved_sections.tag)
            RETURNING *;
        """, (user_id, payload.section_id, payload.notes, payload.tag or "General"))
        row = db.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save statutory bookmark."
            )

        # Fetch joined details
        db.execute("""
            SELECT
                b.bookmark_id, b.user_id, b.section_id,
                s.section_number, s.section_title,
                l.law_id, l.law_name,
                b.notes, b.tag, b.created_at
            FROM user_saved_sections b
            JOIN sections s ON b.section_id = s.section_id
            JOIN laws l ON s.law_id = l.law_id
            WHERE b.bookmark_id = %s;
        """, (row["bookmark_id"],))
        fetched = db.fetchone()
        if not fetched:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve bookmarked section details."
            )
        result = dict(fetched)
        db.connection.commit()
        return result

    @staticmethod
    def delete_bookmark(db: RealDictCursor, user_id: int, section_id: int) -> bool:
        """
        Removes a bookmarked section for the authenticated citizen.
        """
        db.execute("""
            DELETE FROM user_saved_sections
            WHERE user_id = %s AND section_id = %s
            RETURNING bookmark_id;
        """, (user_id, section_id))
        deleted = db.fetchone() is not None
        if deleted:
            db.connection.commit()
        return deleted

    # --------------------------------------------------------------------------
    # 7. SEARCH HISTORY
    # --------------------------------------------------------------------------
    @staticmethod
    def list_search_history(db: RealDictCursor, user_id: int, limit: int = 20) -> List[dict]:
        """
        Retrieves the authenticated citizen's recent legal research queries.
        """
        db.execute("""
            SELECT search_id, query_text, filters, results_count, searched_at
            FROM user_search_history
            WHERE user_id = %s
            ORDER BY searched_at DESC
            LIMIT %s;
        """, (user_id, limit))
        return [dict(row) for row in db.fetchall()]

    @staticmethod
    def record_search(
        db: RealDictCursor,
        user_id: int,
        query_text: str,
        filters: Optional[dict] = None,
        results_count: int = 0
    ) -> dict:
        """
        Logs a search query to the citizen's search history.
        """
        clean_query = query_text.strip()
        if not clean_query:
            return {}

        filter_json = json.dumps(filters or {})
        db.execute("""
            INSERT INTO user_search_history (user_id, query_text, filters, results_count)
            VALUES (%s, %s, %s::jsonb, %s)
            RETURNING *;
        """, (user_id, clean_query, filter_json, results_count))
        row = db.fetchone()
        result = dict(row) if row else {}
        db.connection.commit()
        return result

    @staticmethod
    def clear_search_history(db: RealDictCursor, user_id: int) -> bool:
        """
        Clears all search history for the citizen.
        """
        db.execute("DELETE FROM user_search_history WHERE user_id = %s;", (user_id,))
        db.connection.commit()
        return True

    # --------------------------------------------------------------------------
    # 8. CITIZEN NOTIFICATIONS
    # --------------------------------------------------------------------------
    @staticmethod
    def list_notifications(db: RealDictCursor, user_id: int) -> dict:
        """
        Retrieves all notifications for the citizen with unread count.
        """
        db.execute("""
            SELECT
                notification_id, reminder_id, title,
                message, notification_type, is_read, sent_at, created_at
            FROM notifications
            WHERE user_id = %s
            ORDER BY created_at DESC;
        """, (user_id,))
        rows = [dict(r) for r in db.fetchall()]
        unread = sum(1 for r in rows if not r["is_read"])
        return {
            "unread_count": unread,
            "total": len(rows),
            "notifications": rows
        }

    @staticmethod
    def mark_notification_read(db: RealDictCursor, user_id: int, notification_id: int) -> dict:
        """
        Marks an individual notification as read.
        CRITICAL AUTHORIZATION: Strictly verifies notification belongs to user_id.
        """
        db.execute("""
            UPDATE notifications
            SET is_read = TRUE
            WHERE notification_id = %s AND user_id = %s
            RETURNING *;
        """, (notification_id, user_id))
        row = db.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found or unauthorized."
            )
        db.connection.commit()
        return dict(row)

    @staticmethod
    def mark_all_read(db: RealDictCursor, user_id: int) -> int:
        """
        Marks all notifications as read for the authenticated citizen.
        """
        db.execute("""
            UPDATE notifications
            SET is_read = TRUE
            WHERE user_id = %s AND is_read = FALSE
            RETURNING notification_id;
        """, (user_id,))
        count = len(db.fetchall())
        db.connection.commit()
        return count

    # --------------------------------------------------------------------------
    # 9. PROCEDURE TRACKERS & CHECKLISTS
    # --------------------------------------------------------------------------
    @staticmethod
    def list_procedures(db: RealDictCursor, user_id: int) -> List[dict]:
        """
        Lists all procedures tracked by the citizen with checklist progress.
        """
        db.execute("""
            SELECT
                upt.tracker_id, upt.procedure_id, lp.procedure_name, lp.category,
                upt.status, upt.completed_documents, upt.notes, upt.updated_at,
                (SELECT COUNT(*) FROM procedure_required_documents WHERE procedure_id = upt.procedure_id) AS total_documents_count
            FROM user_procedure_trackers upt
            JOIN legal_procedures lp ON upt.procedure_id = lp.procedure_id
            WHERE upt.user_id = %s
            ORDER BY upt.updated_at DESC;
        """, (user_id,))
        rows = []
        for r in db.fetchall():
            d = dict(r)
            completed_docs = d.get("completed_documents") or []
            if isinstance(completed_docs, str):
                try:
                    completed_docs = json.loads(completed_docs)
                except Exception:
                    completed_docs = []
            d["completed_documents"] = completed_docs
            d["completed_documents_count"] = len(completed_docs)
            rows.append(d)
        return rows

    @staticmethod
    def toggle_procedure_doc(
        db: RealDictCursor,
        user_id: int,
        procedure_id: int,
        document_name: str,
        completed: Optional[bool] = None
    ) -> dict:
        """
        Persists checking or unchecking a document in a procedure's checklist.
        Creates a tracker record if one does not already exist.
        """
        # Validate procedure exists
        db.execute("SELECT procedure_id, procedure_name, category FROM legal_procedures WHERE procedure_id = %s;", (procedure_id,))
        proc = db.fetchone()
        if not proc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Procedure with ID {procedure_id} not found."
            )

        # Get existing tracker
        db.execute("""
            SELECT tracker_id, completed_documents
            FROM user_procedure_trackers
            WHERE user_id = %s AND procedure_id = %s;
        """, (user_id, procedure_id))
        tracker = db.fetchone()

        clean_doc = document_name.strip()

        if tracker:
            raw_docs = tracker["completed_documents"] or []
            if isinstance(raw_docs, str):
                try:
                    raw_docs = json.loads(raw_docs)
                except Exception:
                    raw_docs = []
            completed_list = list(raw_docs)

            if completed is None:
                # Toggle behavior
                if clean_doc in completed_list:
                    completed_list.remove(clean_doc)
                else:
                    completed_list.append(clean_doc)
            elif completed:
                if clean_doc not in completed_list:
                    completed_list.append(clean_doc)
            else:
                if clean_doc in completed_list:
                    completed_list.remove(clean_doc)

            db.execute("""
                UPDATE user_procedure_trackers
                SET completed_documents = %s::jsonb, updated_at = CURRENT_TIMESTAMP
                WHERE tracker_id = %s
                RETURNING *;
            """, (json.dumps(completed_list), tracker["tracker_id"]))
            updated = db.fetchone()
        else:
            if completed is None or completed:
                completed_list = [clean_doc]
            else:
                completed_list = []
            db.execute("""
                INSERT INTO user_procedure_trackers (
                    user_id, procedure_id, status, completed_documents
                ) VALUES (
                    %s, %s, 'in_progress', %s::jsonb
                )
                RETURNING *;
            """, (user_id, procedure_id, json.dumps(completed_list)))
            updated = db.fetchone()

        db.connection.commit()

        if not updated:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update procedure tracker."
            )

        # Count total documents for procedure
        db.execute("SELECT COUNT(*) AS total FROM procedure_required_documents WHERE procedure_id = %s;", (procedure_id,))
        count_row = db.fetchone()
        total_count = count_row["total"] if count_row else 0

        return {
            "tracker_id": updated["tracker_id"],
            "procedure_id": procedure_id,
            "procedure_name": proc["procedure_name"],
            "category": proc["category"],
            "status": updated["status"],
            "completed_documents": completed_list,
            "total_documents_count": total_count,
            "completed_documents_count": len(completed_list),
            "notes": updated.get("notes"),
            "updated_at": updated["updated_at"]
        }
