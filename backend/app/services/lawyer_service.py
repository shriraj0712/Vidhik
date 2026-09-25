"""
Vidhik Platform - Lawyer Module Business Logic Service
======================================================
Implements all core operations for the Lawyer Workspace:
- Dashboard Metrics Aggregations
- Client Roster & Case Association
- Case Lifecycle & Multi-Section Workspaces
- Document Cataloging & Association
- Court Hearing Calendar Management
- Case-specific Legal Notes
- Direct Statutory Section Linking (from Legal Search)
- Profile & Specialization Updates
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime
from psycopg2.extras import RealDictCursor

from app.schemas.lawyer import (
    DashboardMetricsResponse,
    ClientCreate, ClientUpdate, ClientResponse, ClientListResponse,
    CaseCreate, CaseUpdate, CaseSummaryResponse, CaseDetailResponse, CaseListResponse,
    HearingCreate, HearingUpdate, HearingResponse, HearingListResponse,
    DocumentCreate, DocumentResponse, DocumentListResponse,
    NoteCreate, NoteUpdate, NoteResponse,
    LawyerProfileResponse, LawyerProfileUpdate,
    CaseSectionLinkRequest, CaseSectionLinkResponse
)


class LawyerService:
    """
    Dedicated service handling relational SQL operations for lawyers.
    All operations are strictly parameterized to ensure safety and integrity.
    """

    # -------------------------------------------------------------
    # 1. DASHBOARD METRICS
    # -------------------------------------------------------------
    @staticmethod
    def get_dashboard_metrics(db: RealDictCursor, lawyer_id: int) -> DashboardMetricsResponse:
        today = date.today()

        # Total Clients
        db.execute("""
            SELECT COUNT(DISTINCT user_id) AS total_clients
            FROM cases
            WHERE assigned_lawyer_id = %s;
        """, (lawyer_id,))
        total_clients = db.fetchone()["total_clients"] or 0

        # Active Cases
        db.execute("""
            SELECT COUNT(*) AS active_cases
            FROM cases
            WHERE assigned_lawyer_id = %s AND status = 'active';
        """, (lawyer_id,))
        active_cases = db.fetchone()["active_cases"] or 0

        # Upcoming Hearings
        db.execute("""
            SELECT COUNT(*) AS upcoming_hearings
            FROM reminders
            WHERE lawyer_id = %s AND reminder_date >= %s AND status = 'scheduled';
        """, (lawyer_id, today))
        upcoming_hearings = db.fetchone()["upcoming_hearings"] or 0

        # Recent Documents Count
        db.execute("""
            SELECT COUNT(*) AS recent_docs
            FROM case_documents
            WHERE lawyer_id = %s;
        """, (lawyer_id,))
        recent_documents_count = db.fetchone()["recent_docs"] or 0

        # Recent Cases (5 latest)
        db.execute("""
            SELECT 
                c.case_id, c.user_id, c.case_title, c.case_number,
                c.case_type, c.court_name, c.status, c.filing_date,
                u.full_name AS client_name
            FROM cases c
            LEFT JOIN users u ON c.user_id = u.user_id
            WHERE c.assigned_lawyer_id = %s
            ORDER BY c.created_at DESC
            LIMIT 5;
        """, (lawyer_id,))
        recent_cases = db.fetchall()

        # Upcoming Hearings List (5 next)
        db.execute("""
            SELECT 
                r.reminder_id, r.case_id, r.title, r.reminder_date,
                r.reminder_time, r.court_name, r.priority, r.status,
                c.case_title, c.case_number
            FROM reminders r
            JOIN cases c ON r.case_id = c.case_id
            WHERE r.lawyer_id = %s AND r.reminder_date >= %s
            ORDER BY r.reminder_date ASC, r.reminder_time ASC
            LIMIT 5;
        """, (lawyer_id, today))
        upcoming_hearings_list = db.fetchall()

        # Recent Documents (5 latest)
        db.execute("""
            SELECT 
                d.document_id, d.case_id, d.document_name, d.document_type,
                d.file_path, d.file_size_bytes, d.created_at,
                c.case_title, c.case_number
            FROM case_documents d
            JOIN cases c ON d.case_id = c.case_id
            WHERE d.lawyer_id = %s
            ORDER BY d.created_at DESC
            LIMIT 5;
        """, (lawyer_id,))
        recent_documents = db.fetchall()

        # Recent Activity Feed (Case Updates)
        db.execute("""
            SELECT 
                cu.update_id, cu.case_id, cu.update_title, cu.update_description,
                cu.update_type, cu.update_date, c.case_title, c.case_number
            FROM case_updates cu
            JOIN cases c ON cu.case_id = c.case_id
            WHERE c.assigned_lawyer_id = %s
            ORDER BY cu.update_date DESC
            LIMIT 6;
        """, (lawyer_id,))
        recent_activity = db.fetchall()

        return DashboardMetricsResponse(
            total_clients=total_clients,
            active_cases=active_cases,
            upcoming_hearings=upcoming_hearings,
            recent_documents_count=recent_documents_count,
            recent_cases=[dict(r) for r in recent_cases],
            upcoming_hearings_list=[dict(r) for r in upcoming_hearings_list],
            recent_documents=[dict(r) for r in recent_documents],
            recent_activity=[dict(r) for r in recent_activity]
        )

    # -------------------------------------------------------------
    # 2. CLIENT MANAGEMENT
    # -------------------------------------------------------------
    @staticmethod
    def list_clients(db: RealDictCursor, lawyer_id: int, search: Optional[str] = None) -> ClientListResponse:
        params: List[Any] = [lawyer_id]
        search_filter = ""
        if search:
            search_filter = "AND (u.full_name ILIKE %s OR u.email ILIKE %s OR u.phone ILIKE %s)"
            pattern = f"%{search.strip()}%"
            params.extend([pattern, pattern, pattern])

        query = f"""
            SELECT 
                u.user_id, u.full_name, u.email, u.phone, u.role,
                u.is_active, u.created_at,
                COUNT(c.case_id) AS active_cases_count
            FROM users u
            LEFT JOIN cases c ON u.user_id = c.user_id AND c.assigned_lawyer_id = %s AND c.status = 'active'
            WHERE u.role = 'user' {search_filter}
            GROUP BY u.user_id, u.full_name, u.email, u.phone, u.role, u.is_active, u.created_at
            ORDER BY u.created_at DESC;
        """
        db.execute(query, tuple(params))
        rows = db.fetchall()
        return ClientListResponse(
            total=len(rows),
            clients=[ClientResponse(**r) for r in rows]
        )

    @staticmethod
    def get_client(db: RealDictCursor, client_id: int, lawyer_id: int) -> Optional[ClientResponse]:
        db.execute("""
            SELECT 
                u.user_id, u.full_name, u.email, u.phone, u.role,
                u.is_active, u.created_at,
                COUNT(c.case_id) AS active_cases_count
            FROM users u
            LEFT JOIN cases c ON u.user_id = c.user_id AND c.assigned_lawyer_id = %s AND c.status = 'active'
            WHERE u.user_id = %s AND u.role = 'user'
            GROUP BY u.user_id, u.full_name, u.email, u.phone, u.role, u.is_active, u.created_at;
        """, (lawyer_id, client_id))
        row = db.fetchone()
        if not row:
            return None

        # Fetch cases for this client
        db.execute("""
            SELECT 
                case_id, case_title, case_number, case_type,
                court_name, status, filing_date, created_at
            FROM cases
            WHERE user_id = %s AND assigned_lawyer_id = %s
            ORDER BY created_at DESC;
        """, (client_id, lawyer_id))
        cases = db.fetchall()

        client_dict = dict(row)
        client_dict["cases"] = [dict(c) for c in cases]
        return ClientResponse(**client_dict)

    @staticmethod
    def create_client(db: RealDictCursor, data: ClientCreate) -> ClientResponse:
        username = data.email.split("@")[0] + "_" + str(int(datetime.now().timestamp()))[-4:]
        db.execute("""
            INSERT INTO users (username, email, password_hash, full_name, phone, role, is_active, is_verified)
            VALUES (%s, %s, 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', %s, %s, 'user', TRUE, TRUE)
            RETURNING user_id, full_name, email, phone, role, is_active, created_at;
        """, (username, data.email.lower().strip(), data.full_name.strip(), data.phone))
        created = db.fetchone()
        db.connection.commit()
        return ClientResponse(**created, active_cases_count=0)

    @staticmethod
    def update_client(db: RealDictCursor, client_id: int, data: ClientUpdate) -> Optional[ClientResponse]:
        fields = []
        params = []
        if data.full_name is not None:
            fields.append("full_name = %s")
            params.append(data.full_name.strip())
        if data.phone is not None:
            fields.append("phone = %s")
            params.append(data.phone.strip())
        if data.email is not None:
            fields.append("email = %s")
            params.append(data.email.lower().strip())

        if not fields:
            return None

        fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(client_id)
        sql = f"UPDATE users SET {', '.join(fields)} WHERE user_id = %s RETURNING user_id, full_name, email, phone, role, is_active, created_at;"
        db.execute(sql, tuple(params))
        updated = db.fetchone()
        if updated:
            db.connection.commit()
            return ClientResponse(**updated, active_cases_count=0)
        return None

    # -------------------------------------------------------------
    # 3. CASE MANAGEMENT
    # -------------------------------------------------------------
    @staticmethod
    def list_cases(
        db: RealDictCursor,
        lawyer_id: int,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        case_type: Optional[str] = None
    ) -> CaseListResponse:
        conditions = ["c.assigned_lawyer_id = %s"]
        params: List[Any] = [lawyer_id]

        if status_filter:
            conditions.append("c.status = %s")
            params.append(status_filter.strip())

        if case_type:
            conditions.append("c.case_type ILIKE %s")
            params.append(f"%{case_type.strip()}%")

        if search:
            conditions.append("(c.case_title ILIKE %s OR c.case_number ILIKE %s OR u.full_name ILIKE %s OR c.court_name ILIKE %s)")
            pattern = f"%{search.strip()}%"
            params.extend([pattern, pattern, pattern, pattern])

        where_clause = " WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT 
                c.case_id, c.user_id, c.assigned_lawyer_id,
                c.case_title, c.case_number, c.case_type,
                c.court_name, c.opposite_party, c.status,
                c.filing_date, c.created_at, c.updated_at,
                u.full_name AS client_name, u.phone AS client_phone,
                l.full_name AS lawyer_name
            FROM cases c
            LEFT JOIN users u ON c.user_id = u.user_id
            LEFT JOIN lawyers l ON c.assigned_lawyer_id = l.lawyer_id
            {where_clause}
            ORDER BY c.updated_at DESC;
        """
        db.execute(query, tuple(params))
        rows = db.fetchall()
        return CaseListResponse(
            total=len(rows),
            cases=[CaseSummaryResponse(**r) for r in rows]
        )

    @staticmethod
    def get_case_detail(db: RealDictCursor, case_id: int, lawyer_id: int) -> Optional[CaseDetailResponse]:
        db.execute("""
            SELECT 
                c.case_id, c.user_id, c.assigned_lawyer_id,
                c.case_title, c.case_number, c.case_type,
                c.court_name, c.opposite_party, c.status,
                c.filing_date, c.incident_date, c.location,
                c.police_station, c.case_description,
                c.created_at, c.updated_at,
                u.full_name AS client_name, u.phone AS client_phone, u.email AS client_email,
                l.full_name AS lawyer_name
            FROM cases c
            LEFT JOIN users u ON c.user_id = u.user_id
            LEFT JOIN lawyers l ON c.assigned_lawyer_id = l.lawyer_id
            WHERE c.case_id = %s AND c.assigned_lawyer_id = %s;
        """, (case_id, lawyer_id))
        base = db.fetchone()
        if not base:
            return None

        # Fetch Documents
        db.execute("""
            SELECT document_id, case_id, document_name, document_type,
                   file_path, file_size_bytes, mime_type, upload_status, description, created_at
            FROM case_documents
            WHERE case_id = %s
            ORDER BY created_at DESC;
        """, (case_id,))
        documents = db.fetchall()

        # Fetch Hearings
        db.execute("""
            SELECT reminder_id, case_id, title, description,
                   reminder_date, reminder_time, court_name, judge_name,
                   status, priority, notes, created_at
            FROM reminders
            WHERE case_id = %s
            ORDER BY reminder_date ASC, reminder_time ASC;
        """, (case_id,))
        hearings = db.fetchall()

        # Fetch Notes
        db.execute("""
            SELECT note_id, case_id, lawyer_id, title, content, is_pinned, created_at, updated_at
            FROM case_notes
            WHERE case_id = %s
            ORDER BY is_pinned DESC, updated_at DESC;
        """, (case_id,))
        notes = db.fetchall()

        # Fetch Linked Legal Sections
        db.execute("""
            SELECT 
                cls.section_id, cls.relevance_score, cls.explanation, cls.created_at,
                s.section_number, s.section_title, s.full_text,
                l.law_name, l.law_slug
            FROM case_legal_sections cls
            JOIN sections s ON cls.section_id = s.section_id
            JOIN laws l ON s.law_id = l.law_id
            WHERE cls.case_id = %s
            ORDER BY cls.relevance_score DESC;
        """, (case_id,))
        legal_sections = db.fetchall()

        # Fetch Updates Timeline
        db.execute("""
            SELECT update_id, update_type, update_title, update_description, status, updated_by, update_date
            FROM case_updates
            WHERE case_id = %s
            ORDER BY update_date DESC;
        """, (case_id,))
        updates = db.fetchall()

        case_data = dict(base)
        case_data["documents"] = [dict(d) for d in documents]
        case_data["hearings"] = [dict(h) for h in hearings]
        case_data["notes"] = [dict(n) for n in notes]
        case_data["legal_sections"] = [dict(ls) for ls in legal_sections]
        case_data["updates"] = [dict(u) for u in updates]

        return CaseDetailResponse(**case_data)

    @staticmethod
    def create_case(db: RealDictCursor, lawyer_id: int, data: CaseCreate) -> CaseSummaryResponse:
        db.execute("""
            INSERT INTO cases (
                user_id, assigned_lawyer_id, case_title, case_number, case_type,
                court_name, opposite_party, status, filing_date, incident_date,
                location, police_station, case_description
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s
            ) RETURNING case_id, created_at, updated_at;
        """, (
            data.user_id, lawyer_id, data.case_title.strip(), data.case_number, data.case_type,
            data.court_name, data.opposite_party, data.status or 'active', data.filing_date, data.incident_date,
            data.location, data.police_station, data.case_description
        ))
        res = db.fetchone()
        case_id = res["case_id"]

        # Insert initial activity record
        db.execute("""
            INSERT INTO case_updates (case_id, update_type, update_title, update_description, status, updated_by)
            VALUES (%s, 'Creation', 'Case Initiated', %s, %s, 'Lawyer');
        """, (case_id, f"Case '{data.case_title}' opened in system.", data.status or 'active'))

        db.connection.commit()

        # Return full summary
        return LawyerService.list_cases(db, lawyer_id, search=data.case_title).cases[0]

    @staticmethod
    def update_case(db: RealDictCursor, case_id: int, lawyer_id: int, data: CaseUpdate) -> Optional[CaseDetailResponse]:
        fields = []
        params = []
        for key, val in data.model_dump(exclude_unset=True).items():
            if val is not None:
                fields.append(f"{key} = %s")
                params.append(val)

        if not fields:
            return LawyerService.get_case_detail(db, case_id, lawyer_id)

        fields.append("updated_at = CURRENT_TIMESTAMP")
        params.extend([case_id, lawyer_id])
        sql = f"UPDATE cases SET {', '.join(fields)} WHERE case_id = %s AND assigned_lawyer_id = %s RETURNING case_id;"
        db.execute(sql, tuple(params))
        if db.fetchone():
            db.connection.commit()
            return LawyerService.get_case_detail(db, case_id, lawyer_id)
        return None

    # -------------------------------------------------------------
    # 4. DOCUMENT MANAGEMENT
    # -------------------------------------------------------------
    @staticmethod
    def list_documents(db: RealDictCursor, lawyer_id: int, case_id: Optional[int] = None) -> DocumentListResponse:
        conditions = ["d.lawyer_id = %s"]
        params: List[Any] = [lawyer_id]

        if case_id:
            conditions.append("d.case_id = %s")
            params.append(case_id)

        where_clause = " WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT 
                d.document_id, d.case_id, d.client_id, d.lawyer_id,
                d.document_name, d.document_type, d.file_path,
                d.file_size_bytes, d.mime_type, d.upload_status,
                d.description, d.created_at,
                c.case_title, c.case_number,
                u.full_name AS client_name
            FROM case_documents d
            JOIN cases c ON d.case_id = c.case_id
            LEFT JOIN users u ON d.client_id = u.user_id
            {where_clause}
            ORDER BY d.created_at DESC;
        """
        db.execute(query, tuple(params))
        rows = db.fetchall()
        return DocumentListResponse(
            total=len(rows),
            documents=[DocumentResponse(**r) for r in rows]
        )

    @staticmethod
    def create_document(db: RealDictCursor, lawyer_id: int, data: DocumentCreate) -> DocumentResponse:
        # Resolve client_id from case if not explicitly provided
        client_id = data.client_id
        if not client_id:
            db.execute("SELECT user_id FROM cases WHERE case_id = %s;", (data.case_id,))
            crow = db.fetchone()
            if crow:
                client_id = crow["user_id"]

        path = data.file_path or f"/documents/cases/{data.case_id}/{data.document_name}"

        db.execute("""
            INSERT INTO case_documents (
                case_id, client_id, lawyer_id, document_name, document_type,
                file_path, file_size_bytes, mime_type, upload_status, description
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'uploaded', %s)
            RETURNING document_id, created_at;
        """, (
            data.case_id, client_id, lawyer_id, data.document_name.strip(),
            data.document_type, path, data.file_size_bytes or 1048576,
            data.mime_type or 'application/pdf', data.description
        ))
        res = db.fetchone()
        doc_id = res["document_id"]
        db.connection.commit()

        # Fetch and return full response
        docs = LawyerService.list_documents(db, lawyer_id, case_id=data.case_id).documents
        for d in docs:
            if d.document_id == doc_id:
                return d
        raise Exception("Failed to retrieve created document")

    @staticmethod
    def delete_document(db: RealDictCursor, document_id: int, lawyer_id: int) -> bool:
        db.execute("""
            DELETE FROM case_documents
            WHERE document_id = %s AND lawyer_id = %s
            RETURNING document_id;
        """, (document_id, lawyer_id))
        deleted = db.fetchone()
        if deleted:
            db.connection.commit()
            return True
        return False

    # -------------------------------------------------------------
    # 5. HEARING MANAGEMENT
    # -------------------------------------------------------------
    @staticmethod
    def list_hearings(db: RealDictCursor, lawyer_id: int) -> HearingListResponse:
        today = date.today()

        query = """
            SELECT 
                r.reminder_id, r.case_id, r.lawyer_id, r.title,
                r.description, r.reminder_type, r.reminder_date,
                r.reminder_time, r.court_name, r.judge_name,
                r.status, r.priority, r.notes, r.created_at,
                c.case_title, c.case_number
            FROM reminders r
            JOIN cases c ON r.case_id = c.case_id
            WHERE r.lawyer_id = %s
            ORDER BY r.reminder_date ASC, r.reminder_time ASC;
        """
        db.execute(query, (lawyer_id,))
        rows = db.fetchall()

        upcoming = []
        past = []
        for r in rows:
            hearing = HearingResponse(**r)
            if hearing.reminder_date >= today:
                upcoming.append(hearing)
            else:
                past.append(hearing)

        return HearingListResponse(
            total=len(rows),
            upcoming=upcoming,
            past=past
        )

    @staticmethod
    def create_hearing(db: RealDictCursor, lawyer_id: int, data: HearingCreate) -> HearingResponse:
        db.execute("SELECT user_id, court_name FROM cases WHERE case_id = %s;", (data.case_id,))
        c_row = db.fetchone()
        user_id = c_row["user_id"] if c_row else None
        court = data.court_name or (c_row["court_name"] if c_row else None)

        db.execute("""
            INSERT INTO reminders (
                case_id, user_id, lawyer_id, title, description, reminder_type,
                reminder_date, reminder_time, court_name, judge_name, status, priority, notes
            ) VALUES (
                %s, %s, %s, %s, %s, 'hearing',
                %s, %s, %s, %s, %s, %s, %s
            ) RETURNING reminder_id, created_at;
        """, (
            data.case_id, user_id, lawyer_id, data.title.strip(), data.description,
            data.reminder_date, data.reminder_time, court, data.judge_name,
            data.status or 'scheduled', data.priority or 'normal', data.notes
        ))
        res = db.fetchone()
        h_id = res["reminder_id"]
        db.connection.commit()

        # Retrieve hearing details
        hearings = LawyerService.list_hearings(db, lawyer_id)
        for h in (hearings.upcoming + hearings.past):
            if h.reminder_id == h_id:
                return h
        raise Exception("Failed to retrieve created hearing")

    @staticmethod
    def update_hearing(db: RealDictCursor, hearing_id: int, lawyer_id: int, data: HearingUpdate) -> Optional[HearingResponse]:
        fields = []
        params = []
        for key, val in data.model_dump(exclude_unset=True).items():
            if val is not None:
                fields.append(f"{key} = %s")
                params.append(val)

        if not fields:
            return None

        fields.append("updated_at = CURRENT_TIMESTAMP")
        params.extend([hearing_id, lawyer_id])
        sql = f"UPDATE reminders SET {', '.join(fields)} WHERE reminder_id = %s AND lawyer_id = %s RETURNING reminder_id;"
        db.execute(sql, tuple(params))
        if db.fetchone():
            db.connection.commit()
            hearings = LawyerService.list_hearings(db, lawyer_id)
            for h in (hearings.upcoming + hearings.past):
                if h.reminder_id == hearing_id:
                    return h
        return None

    # -------------------------------------------------------------
    # 6. CASE NOTES
    # -------------------------------------------------------------
    @staticmethod
    def list_notes(db: RealDictCursor, case_id: int, lawyer_id: int) -> List[NoteResponse]:
        db.execute("""
            SELECT 
                cn.note_id, cn.case_id, cn.lawyer_id, cn.title,
                cn.content, cn.is_pinned, cn.created_at, cn.updated_at,
                c.case_title
            FROM case_notes cn
            JOIN cases c ON cn.case_id = c.case_id
            WHERE cn.case_id = %s AND cn.lawyer_id = %s
            ORDER BY cn.is_pinned DESC, cn.updated_at DESC;
        """, (case_id, lawyer_id))
        rows = db.fetchall()
        return [NoteResponse(**r) for r in rows]

    @staticmethod
    def create_note(db: RealDictCursor, lawyer_id: int, data: NoteCreate) -> NoteResponse:
        db.execute("""
            INSERT INTO case_notes (case_id, lawyer_id, title, content, is_pinned)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING note_id, created_at, updated_at;
        """, (data.case_id, lawyer_id, data.title, data.content.strip(), data.is_pinned))
        res = db.fetchone()
        db.connection.commit()

        notes = LawyerService.list_notes(db, data.case_id, lawyer_id)
        for n in notes:
            if n.note_id == res["note_id"]:
                return n
        raise Exception("Failed to retrieve created note")

    @staticmethod
    def update_note(db: RealDictCursor, note_id: int, lawyer_id: int, data: NoteUpdate) -> Optional[NoteResponse]:
        fields = []
        params = []
        if data.title is not None:
            fields.append("title = %s")
            params.append(data.title.strip())
        if data.content is not None:
            fields.append("content = %s")
            params.append(data.content.strip())
        if data.is_pinned is not None:
            fields.append("is_pinned = %s")
            params.append(data.is_pinned)

        if not fields:
            return None

        fields.append("updated_at = CURRENT_TIMESTAMP")
        params.extend([note_id, lawyer_id])
        sql = f"UPDATE case_notes SET {', '.join(fields)} WHERE note_id = %s AND lawyer_id = %s RETURNING case_id;"
        db.execute(sql, tuple(params))
        row = db.fetchone()
        if row:
            db.connection.commit()
            notes = LawyerService.list_notes(db, row["case_id"], lawyer_id)
            for n in notes:
                if n.note_id == note_id:
                    return n
        return None

    @staticmethod
    def delete_note(db: RealDictCursor, note_id: int, lawyer_id: int) -> bool:
        db.execute("""
            DELETE FROM case_notes
            WHERE note_id = %s AND lawyer_id = %s
            RETURNING note_id;
        """, (note_id, lawyer_id))
        deleted = db.fetchone()
        if deleted:
            db.connection.commit()
            return True
        return False

    # -------------------------------------------------------------
    # 7. LEGAL RESEARCH SECTION ASSOCIATION
    # -------------------------------------------------------------
    @staticmethod
    def link_section_to_case(
        db: RealDictCursor,
        case_id: int,
        lawyer_id: int,
        data: CaseSectionLinkRequest
    ) -> CaseSectionLinkResponse:
        # Verify lawyer owns this case
        db.execute("SELECT case_id FROM cases WHERE case_id = %s AND assigned_lawyer_id = %s;", (case_id, lawyer_id))
        if not db.fetchone():
            raise Exception("Unauthorized: Case not found or not assigned to lawyer.")

        db.execute("""
            INSERT INTO case_legal_sections (case_id, section_id, relevance_score, explanation)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (case_id, section_id) 
            DO UPDATE SET relevance_score = EXCLUDED.relevance_score, explanation = EXCLUDED.explanation
            RETURNING created_at;
        """, (case_id, data.section_id, data.relevance_score, data.explanation))
        res = db.fetchone()
        db.connection.commit()

        # Fetch section and law details
        db.execute("""
            SELECT s.section_number, s.section_title, l.law_name
            FROM sections s
            JOIN laws l ON s.law_id = l.law_id
            WHERE s.section_id = %s;
        """, (data.section_id,))
        sec = db.fetchone()

        return CaseSectionLinkResponse(
            case_id=case_id,
            section_id=data.section_id,
            section_number=sec["section_number"],
            section_title=sec["section_title"],
            law_name=sec["law_name"],
            relevance_score=data.relevance_score,
            explanation=data.explanation,
            created_at=res["created_at"]
        )

    @staticmethod
    def unlink_section_from_case(db: RealDictCursor, case_id: int, section_id: int, lawyer_id: int) -> bool:
        db.execute("""
            DELETE FROM case_legal_sections cls
            USING cases c
            WHERE cls.case_id = c.case_id
              AND cls.case_id = %s
              AND cls.section_id = %s
              AND c.assigned_lawyer_id = %s
            RETURNING cls.section_id;
        """, (case_id, section_id, lawyer_id))
        deleted = db.fetchone()
        if deleted:
            db.connection.commit()
            return True
        return False

    # -------------------------------------------------------------
    # 8. LAWYER PROFILE
    # -------------------------------------------------------------
    @staticmethod
    def get_profile(db: RealDictCursor, lawyer_id: int) -> Optional[LawyerProfileResponse]:
        db.execute("""
            SELECT 
                l.lawyer_id, l.user_id, l.full_name, l.email, l.phone,
                l.bar_council_number, l.specialization, l.experience_years,
                l.bio, l.court_practice, l.office_address, l.city,
                l.state, l.pincode, l.is_verified, l.created_at
            FROM lawyers l
            WHERE l.lawyer_id = %s;
        """, (lawyer_id,))
        row = db.fetchone()
        if not row:
            return None

        # Fetch Specializations list
        db.execute("SELECT specialization FROM lawyer_specializations WHERE lawyer_id = %s;", (lawyer_id,))
        specs = [r["specialization"] for r in db.fetchall()]

        # Fetch Languages list
        db.execute("SELECT language FROM lawyer_languages WHERE lawyer_id = %s;", (lawyer_id,))
        langs = [r["language"] for r in db.fetchall()]

        # Fetch Locations list
        db.execute("SELECT city, state, district, pincode FROM lawyer_locations WHERE lawyer_id = %s;", (lawyer_id,))
        locs = [dict(r) for r in db.fetchall()]

        data = dict(row)
        data["specializations_list"] = specs
        data["languages_list"] = langs
        data["locations_list"] = locs

        return LawyerProfileResponse(**data)

    @staticmethod
    def update_profile(db: RealDictCursor, lawyer_id: int, data: LawyerProfileUpdate) -> Optional[LawyerProfileResponse]:
        fields = []
        params = []
        for key, val in data.model_dump(exclude_unset=True).items():
            if key not in ["specializations_list", "languages_list"] and val is not None:
                fields.append(f"{key} = %s")
                params.append(val)

        if fields:
            fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(lawyer_id)
            sql = f"UPDATE lawyers SET {', '.join(fields)} WHERE lawyer_id = %s;"
            db.execute(sql, tuple(params))

        # Update specializations if provided
        if data.specializations_list is not None:
            db.execute("DELETE FROM lawyer_specializations WHERE lawyer_id = %s;", (lawyer_id,))
            for spec in data.specializations_list:
                db.execute("INSERT INTO lawyer_specializations (lawyer_id, specialization) VALUES (%s, %s);", (lawyer_id, spec.strip()))

        # Update languages if provided
        if data.languages_list is not None:
            db.execute("DELETE FROM lawyer_languages WHERE lawyer_id = %s;", (lawyer_id,))
            for lang in data.languages_list:
                db.execute("INSERT INTO lawyer_languages (lawyer_id, language) VALUES (%s, %s);", (lawyer_id, lang.strip()))

        db.connection.commit()
        return LawyerService.get_profile(db, lawyer_id)
