"""
Vidhik Platform - Security Audit Logging Service
=================================================
Records and queries security-sensitive events including authentication,
role assignments, credential updates, and administrative actions.
Never writes passwords, hashes, JWT secrets, or raw reset tokens to logs.
"""

import logging
from typing import Optional, List, Dict, Any
from psycopg2.extras import RealDictCursor

logger = logging.getLogger("vidhik.security.audit")


class AuditService:
    """Service for non-blocking, parameterized security audit logging."""

    @staticmethod
    def log_event(
        db: Optional[RealDictCursor],
        action: str,
        user_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        description: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Inserts a structured security event into the `audit_logs` table.
        Strictly sanitizes inputs and fails safely without interrupting user requests.
        """
        if not db:
            logger.info(f"[AUDIT] Action: {action} | User: {user_id} | Desc: {description}")
            return True

        try:
            # Mask potential IP formatting issues for INET column
            safe_ip = ip_address
            if safe_ip and ":" in safe_ip and len(safe_ip.split(":")) > 2:
                # IPv6 normalization or None if non-standard
                safe_ip = safe_ip.split("%")[0]
            elif safe_ip and safe_ip in ("localhost", "testclient"):
                safe_ip = "127.0.0.1"

            query = """
                INSERT INTO audit_logs (
                    user_id, action, entity_type, entity_id, description, ip_address, user_agent
                ) VALUES (%s, %s, %s, %s, %s, %s, %s);
            """
            db.execute(query, (
                user_id,
                action[:100],
                entity_type[:100] if entity_type else None,
                entity_id,
                description,
                safe_ip,
                user_agent[:500] if user_agent else None
            ))
            # Commit the audit entry immediately if connection is in manual transaction mode
            if hasattr(db, "connection") and db.connection and not db.connection.autocommit:
                db.connection.commit()
            return True
        except Exception as e:
            logger.warning(f"Failed to record audit log: {e}")
            try:
                if hasattr(db, "connection") and db.connection:
                    db.connection.rollback()
            except Exception:
                pass
            return False

    @staticmethod
    def list_logs(
        db: RealDictCursor,
        limit: int = 50,
        offset: int = 0,
        action: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Retrieves paginated audit logs for administrative inspection.
        """
        conditions = []
        params: List[Any] = []

        if action:
            conditions.append("action = %s")
            params.append(action)
        if user_id:
            conditions.append("user_id = %s")
            params.append(user_id)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        # Count total
        count_sql = f"SELECT COUNT(*) AS total FROM audit_logs {where_clause};"
        db.execute(count_sql, tuple(params))
        count_row = db.fetchone()
        total = count_row["total"] if count_row else 0

        # Query entries
        data_sql = f"""
            SELECT 
                audit_id, user_id, action, entity_type, entity_id,
                description, HOST(ip_address) AS ip_address, user_agent, created_at
            FROM audit_logs
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s;
        """
        params.extend([limit, offset])
        db.execute(data_sql, tuple(params))
        rows = db.fetchall() or []

        return {
            "total": total,
            "logs": rows
        }
