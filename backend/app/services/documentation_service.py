"""
Vidhik Platform - Documentation Support Service
================================================
Business logic for querying legal procedures, assembling statutory document
checklists, and joining requirements with authentic provisions from the
Vidhik legal database.

All database operations are read-only and strictly parameterized.
"""

from typing import Optional, List, Dict, Any
from psycopg2.extras import RealDictCursor

from app.schemas.documentation import (
    DocumentRequirement,
    ProcedureSummary,
    ProcedureDetail,
    ChecklistResponse,
    CategoryResponse,
    ProcedureListResponse
)


class DocumentationService:
    """Service layer for Documentation Support and procedural checklists."""

    @staticmethod
    def get_categories(db: RealDictCursor) -> List[CategoryResponse]:
        """
        Retrieves all distinct legal procedure categories represented in the database
        along with procedure counts.
        """
        query = """
            SELECT 
                category,
                COUNT(procedure_id) AS procedures_count
            FROM legal_procedures
            GROUP BY category
            ORDER BY category ASC;
        """
        db.execute(query)
        rows = db.fetchall()
        return [CategoryResponse(**row) for row in rows]

    @staticmethod
    def list_procedures(
        db: RealDictCursor,
        search: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> ProcedureListResponse:
        """
        Retrieves a filtered and searchable list of legal procedures with
        statutory references and document count rollups.
        """
        conditions = []
        params = []

        if search and search.strip():
            clean_search = f"%{search.strip()}%"
            conditions.append("""
                (lp.procedure_name ILIKE %s 
                 OR lp.description ILIKE %s 
                 OR lp.authority_type ILIKE %s
                 OR l.law_name ILIKE %s)
            """)
            params.extend([clean_search, clean_search, clean_search, clean_search])

        if category and category.strip() and category.strip().lower() != "all":
            conditions.append("lp.category ILIKE %s")
            params.append(category.strip())

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

        # Fetch distinct categories for quick-filtering
        db.execute("SELECT DISTINCT category FROM legal_procedures ORDER BY category ASC;")
        cat_rows = db.fetchall()
        categories = [r["category"] for r in cat_rows]

        # Total count query
        count_sql = f"""
            SELECT COUNT(DISTINCT lp.procedure_id) AS total
            FROM legal_procedures lp
            LEFT JOIN laws l ON lp.governing_law_id = l.law_id
            {where_clause};
        """
        db.execute(count_sql, tuple(params))
        total_row = db.fetchone()
        total_count = total_row["total"] if total_row else 0

        # Main data query with document aggregates
        data_sql = f"""
            SELECT 
                lp.procedure_id,
                lp.procedure_name,
                lp.procedure_slug,
                lp.category,
                lp.description,
                lp.jurisdiction,
                lp.authority_type,
                lp.estimated_processing_days,
                lp.official_portal_url,
                lp.governing_law_id,
                l.law_name AS governing_law_name,
                lp.governing_section_id,
                s.section_number AS governing_section_number,
                s.section_title AS governing_section_title,
                COUNT(prd.doc_req_id) AS total_documents_count,
                COUNT(CASE WHEN prd.is_mandatory = TRUE THEN 1 END) AS mandatory_documents_count,
                COUNT(CASE WHEN prd.is_mandatory = FALSE THEN 1 END) AS supporting_documents_count
            FROM legal_procedures lp
            LEFT JOIN laws l ON lp.governing_law_id = l.law_id
            LEFT JOIN sections s ON lp.governing_section_id = s.section_id
            LEFT JOIN procedure_required_documents prd ON lp.procedure_id = prd.procedure_id
            {where_clause}
            GROUP BY 
                lp.procedure_id, lp.procedure_name, lp.procedure_slug,
                lp.category, lp.description, lp.jurisdiction, lp.authority_type,
                lp.estimated_processing_days, lp.official_portal_url,
                lp.governing_law_id, l.law_name, lp.governing_section_id,
                s.section_number, s.section_title
            ORDER BY lp.procedure_id ASC
            LIMIT %s OFFSET %s;
        """
        db.execute(data_sql, tuple(params + [limit, offset]))
        rows = db.fetchall()

        procedures = [ProcedureSummary(**row) for row in rows]

        return ProcedureListResponse(
            total=total_count,
            procedures=procedures,
            categories=categories
        )

    @staticmethod
    def get_procedure_by_id(db: RealDictCursor, procedure_id: int) -> Optional[ProcedureDetail]:
        """
        Retrieves complete procedure information including joined governing law,
        section, and all document requirements partitioned into mandatory and supporting.
        """
        proc_sql = """
            SELECT 
                lp.procedure_id,
                lp.procedure_name,
                lp.procedure_slug,
                lp.category,
                lp.description,
                lp.jurisdiction,
                lp.authority_type,
                lp.estimated_processing_days,
                lp.official_portal_url,
                lp.governing_law_id,
                l.law_name AS governing_law_name,
                lp.governing_section_id,
                s.section_number AS governing_section_number,
                s.section_title AS governing_section_title
            FROM legal_procedures lp
            LEFT JOIN laws l ON lp.governing_law_id = l.law_id
            LEFT JOIN sections s ON lp.governing_section_id = s.section_id
            WHERE lp.procedure_id = %s;
        """
        db.execute(proc_sql, (procedure_id,))
        proc_row = db.fetchone()
        if not proc_row:
            return None

        # Fetch all document requirements joined with statutory reference details
        doc_sql = """
            SELECT 
                prd.doc_req_id,
                prd.procedure_id,
                prd.document_name,
                prd.document_type,
                prd.is_mandatory,
                prd.purpose,
                prd.preparation_guidance,
                prd.statutory_reference_id,
                prd.order_index,
                s.section_number,
                s.section_title,
                l.law_id,
                l.law_name
            FROM procedure_required_documents prd
            LEFT JOIN sections s ON prd.statutory_reference_id = s.section_id
            LEFT JOIN laws l ON s.law_id = l.law_id
            WHERE prd.procedure_id = %s
            ORDER BY prd.is_mandatory DESC, prd.order_index ASC, prd.doc_req_id ASC;
        """
        db.execute(doc_sql, (procedure_id,))
        doc_rows = db.fetchall()

        all_docs = [DocumentRequirement(**r) for r in doc_rows]
        mandatory_docs = [d for d in all_docs if d.is_mandatory]
        supporting_docs = [d for d in all_docs if not d.is_mandatory]

        proc_data = dict(proc_row)
        proc_data["total_documents_count"] = len(all_docs)
        proc_data["mandatory_documents_count"] = len(mandatory_docs)
        proc_data["supporting_documents_count"] = len(supporting_docs)
        proc_data["all_documents"] = all_docs
        proc_data["mandatory_documents"] = mandatory_docs
        proc_data["supporting_documents"] = supporting_docs

        return ProcedureDetail(**proc_data)

    @staticmethod
    def get_procedure_checklist(db: RealDictCursor, procedure_id: int) -> Optional[ChecklistResponse]:
        """
        Retrieves dedicated structured checklist with statutory citations
        separated into mandatory and supporting items.
        """
        proc = DocumentationService.get_procedure_by_id(db, procedure_id)
        if not proc:
            return None

        return ChecklistResponse(
            procedure_id=proc.procedure_id,
            procedure_name=proc.procedure_name,
            category=proc.category,
            jurisdiction=proc.jurisdiction,
            authority_type=proc.authority_type,
            governing_law_name=proc.governing_law_name,
            governing_section_number=proc.governing_section_number,
            total_count=proc.total_documents_count,
            mandatory_count=proc.mandatory_documents_count,
            supporting_count=proc.supporting_documents_count,
            mandatory_documents=proc.mandatory_documents,
            supporting_documents=proc.supporting_documents
        )
