"""
Vidhik Platform - Advanced Legal Knowledge Base Service (Phase 17)
==================================================================
Service layer managing authoritative BNS, BNSS, BSA legal intelligence,
offences, punishments, procedural workflows, evidence rules,
predecessor correlations, and verified landmark judicial interpretations.

Integrates with PostgreSQL with resilient fallback to verified statutory
knowledge graphs to ensure zero downtime.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
try:
    from psycopg2.extras import RealDictCursor
except ImportError:
    RealDictCursor = Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
KB_DATA_DIR = BASE_DIR / "data" / "knowledge_base"


class LegalKnowledgeService:
    """
    Authoritative knowledge engine for Bharatiya Nyaya Sanhita,
    Bharatiya Nagarik Suraksha Sanhita, and Bharatiya Sakshya Adhiniyam.
    """

    _bns_cache: Optional[List[Dict[str, Any]]] = None
    _bnss_cache: Optional[List[Dict[str, Any]]] = None
    _bsa_cache: Optional[List[Dict[str, Any]]] = None
    _pred_cache: Optional[List[Dict[str, Any]]] = None
    _judgments_cache: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def _load_data(cls):
        if cls._bns_cache is None:
            bns_file = KB_DATA_DIR / "bns_sections.json"
            if bns_file.exists():
                with open(bns_file, "r", encoding="utf-8") as f:
                    cls._bns_cache = json.load(f)
            else:
                cls._bns_cache = []

        if cls._bnss_cache is None:
            bnss_file = KB_DATA_DIR / "bnss_sections.json"
            if bnss_file.exists():
                with open(bnss_file, "r", encoding="utf-8") as f:
                    cls._bnss_cache = json.load(f)
            else:
                cls._bnss_cache = []

        if cls._bsa_cache is None:
            bsa_file = KB_DATA_DIR / "bsa_sections.json"
            if bsa_file.exists():
                with open(bsa_file, "r", encoding="utf-8") as f:
                    cls._bsa_cache = json.load(f)
            else:
                cls._bsa_cache = []

        if cls._pred_cache is None:
            pred_file = KB_DATA_DIR / "predecessor_mappings.json"
            if pred_file.exists():
                with open(pred_file, "r", encoding="utf-8") as f:
                    cls._pred_cache = json.load(f)
            else:
                cls._pred_cache = []

        if cls._judgments_cache is None:
            j_file = KB_DATA_DIR / "verified_judgments.json"
            if j_file.exists():
                with open(j_file, "r", encoding="utf-8") as f:
                    cls._judgments_cache = json.load(f)
            else:
                cls._judgments_cache = []

    @classmethod
    def get_overview(cls, cursor: Optional[RealDictCursor] = None) -> Dict[str, Any]:
        """Returns corpus summary and statistics across all new legal knowledge modules."""
        cls._load_data()
        
        # In-memory defaults
        total_offences = sum(1 for s in cls._bns_cache if s.get("is_offence") and s.get("offence"))
        total_punishments = sum(1 for s in cls._bns_cache if s.get("punishment"))
        total_procedures = len(cls._bnss_cache)
        total_evidence = len(cls._bsa_cache)
        total_preds = len(cls._pred_cache)
        total_judgments = len(cls._judgments_cache)

        if cursor:
            try:
                cursor.execute("SELECT COUNT(*) FROM offences;")
                r = cursor.fetchone()
                if r and r[0] > 0:
                    total_offences = r[0]

                cursor.execute("SELECT COUNT(*) FROM punishments;")
                r = cursor.fetchone()
                if r and r[0] > 0:
                    total_punishments = r[0]

                cursor.execute("SELECT COUNT(*) FROM legal_procedures;")
                r = cursor.fetchone()
                if r and r[0] > 0:
                    total_procedures = r[0]

                cursor.execute("SELECT COUNT(*) FROM evidence_provisions;")
                r = cursor.fetchone()
                if r and r[0] > 0:
                    total_evidence = r[0]

                cursor.execute("SELECT COUNT(*) FROM predecessor_law_mappings;")
                r = cursor.fetchone()
                if r and r[0] > 0:
                    total_preds = r[0]

                cursor.execute("SELECT COUNT(*) FROM judgments;")
                r = cursor.fetchone()
                if r and r[0] > 0:
                    total_judgments = r[0]
            except Exception:
                pass

        return {
            "status": "active",
            "corpus": "Vidhik Advanced Legal Knowledge Base (Phase 17)",
            "supported_statutes": [
                "Bharatiya Nyaya Sanhita, 2023 (BNS)",
                "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)",
                "Bharatiya Sakshya Adhiniyam, 2023 (BSA)"
            ],
            "total_new_statutes": 3,
            "total_offences": total_offences,
            "total_punishments": total_punishments,
            "total_procedures": total_procedures,
            "total_evidence_provisions": total_evidence,
            "total_predecessor_mappings": total_preds,
            "total_verified_judgments": total_judgments,
            "categories": {
                "bns_sections": len(cls._bns_cache),
                "bnss_sections": len(cls._bnss_cache),
                "bsa_sections": len(cls._bsa_cache),
                "predecessor_mappings": total_preds,
                "verified_judgments": total_judgments
            }
        }

    @classmethod
    def get_offences(
        cls,
        law_id: Optional[int] = None,
        section_id: Optional[int] = None,
        query: Optional[str] = None,
        cursor: Optional[RealDictCursor] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves structured offences linked to statutory sections."""
        cls._load_data()
        results = []

        if cursor:
            try:
                sql = """
                    SELECT o.*, l.law_name, s.section_number, s.section_title
                    FROM offences o
                    JOIN laws l ON o.law_id = l.law_id
                    JOIN sections s ON o.section_id = s.section_id
                    WHERE 1=1
                """
                params = []
                if law_id:
                    sql += " AND o.law_id = %s"
                    params.append(law_id)
                if section_id:
                    sql += " AND o.section_id = %s"
                    params.append(section_id)
                if query:
                    sql += " AND (o.offence_name ILIKE %s OR o.description ILIKE %s)"
                    params.extend([f"%{query}%", f"%{query}%"])
                sql += " ORDER BY o.offence_id ASC;"
                cursor.execute(sql, tuple(params))
                rows = cursor.fetchall()
                if rows:
                    return [dict(r) for r in rows]
            except Exception:
                pass

        # In-memory fallback
        for idx, item in enumerate(cls._bns_cache, start=1):
            if item.get("is_offence") and item.get("offence"):
                off = item["offence"]
                name = off.get("offence_name", "")
                desc = off.get("description", "")
                if query:
                    q = query.lower()
                    if q not in name.lower() and q not in desc.lower() and q not in item["section_title"].lower() and q != item["section_number"]:
                        continue
                results.append({
                    "offence_id": idx,
                    "law_id": 9001,
                    "law_name": "Bharatiya Nyaya Sanhita, 2023",
                    "section_id": 90000 + int(item["section_number"]),
                    "section_number": item["section_number"],
                    "section_title": item["section_title"],
                    "offence_name": name,
                    "description": desc,
                    "section_reference": f"Section {item['section_number']}, Bharatiya Nyaya Sanhita, 2023",
                    "cognizable_status": off.get("cognizable_status", "Cognizable"),
                    "bailable_status": off.get("bailable_status", "Non-Bailable"),
                    "compoundable_status": off.get("compoundable_status", "Non-Compoundable"),
                    "triable_by": off.get("triable_by", "Court of Session"),
                    "source": "Official Bharatiya Nyaya Sanhita, 2023"
                })
        return results

    @classmethod
    def get_punishments(
        cls,
        offence_id: Optional[int] = None,
        section_id: Optional[int] = None,
        query: Optional[str] = None,
        cursor: Optional[RealDictCursor] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves structured punishments with alternative and community service options."""
        cls._load_data()
        results = []

        if cursor:
            try:
                sql = """
                    SELECT p.*, l.law_name, s.section_number, s.section_title, o.offence_name
                    FROM punishments p
                    JOIN laws l ON p.law_id = l.law_id
                    JOIN sections s ON p.section_id = s.section_id
                    LEFT JOIN offences o ON p.offence_id = o.offence_id
                    WHERE 1=1
                """
                params = []
                if offence_id:
                    sql += " AND p.offence_id = %s"
                    params.append(offence_id)
                if section_id:
                    sql += " AND p.section_id = %s"
                    params.append(section_id)
                if query:
                    sql += " AND (p.punishment_type ILIKE %s OR p.description ILIKE %s)"
                    params.extend([f"%{query}%", f"%{query}%"])
                sql += " ORDER BY p.punishment_id ASC;"
                cursor.execute(sql, tuple(params))
                rows = cursor.fetchall()
                if rows:
                    return [dict(r) for r in rows]
            except Exception:
                pass

        # In-memory fallback
        for idx, item in enumerate(cls._bns_cache, start=1):
            if item.get("punishment"):
                pun = item["punishment"]
                p_type = pun.get("punishment_type", "")
                p_desc = pun.get("description", "")
                if query:
                    q = query.lower()
                    if q not in p_type.lower() and q not in p_desc.lower() and q != item["section_number"]:
                        continue
                results.append({
                    "punishment_id": idx,
                    "law_id": 9001,
                    "law_name": "Bharatiya Nyaya Sanhita, 2023",
                    "section_id": 90000 + int(item["section_number"]),
                    "section_number": item["section_number"],
                    "section_title": item["section_title"],
                    "offence_id": idx if item.get("is_offence") else None,
                    "offence_name": item.get("offence", {}).get("offence_name") if item.get("offence") else None,
                    "punishment_type": p_type,
                    "description": p_desc,
                    "minimum_punishment": pun.get("minimum_punishment"),
                    "maximum_punishment": pun.get("maximum_punishment"),
                    "fine_details": pun.get("fine_details"),
                    "imprisonment_details": pun.get("imprisonment_details"),
                    "community_service": pun.get("community_service", False),
                    "other_penalty": pun.get("other_penalty"),
                    "source": "Official Statutory Source"
                })
        return results

    @classmethod
    def get_procedures(
        cls,
        category: Optional[str] = None,
        query: Optional[str] = None,
        cursor: Optional[RealDictCursor] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves procedural workflows under Bharatiya Nagarik Suraksha Sanhita (BNSS)."""
        cls._load_data()
        results = []

        if cursor:
            try:
                sql = """
                    SELECT p.*, l.law_name, s.section_number, s.section_title
                    FROM legal_procedures p
                    JOIN laws l ON p.law_id = l.law_id
                    JOIN sections s ON p.section_id = s.section_id
                    WHERE 1=1
                """
                params = []
                if category:
                    sql += " AND p.procedure_category ILIKE %s"
                    params.append(f"%{category}%")
                if query:
                    sql += " AND (p.title ILIKE %s OR p.description ILIKE %s OR s.section_number = %s)"
                    params.extend([f"%{query}%", f"%{query}%", query])
                sql += " ORDER BY p.procedure_id ASC;"
                cursor.execute(sql, tuple(params))
                rows = cursor.fetchall()
                if rows:
                    return [dict(r) for r in rows]
            except Exception:
                pass

        # In-memory fallback
        for idx, item in enumerate(cls._bnss_cache, start=1):
            proc = item.get("procedure", {})
            title = proc.get("title", item["section_title"])
            cat = proc.get("procedure_category", item.get("procedure_category", "General Procedure"))
            desc = proc.get("description", item.get("full_text", ""))
            if category and category.lower() not in cat.lower():
                continue
            if query:
                q = query.lower()
                if q not in title.lower() and q not in desc.lower() and q != item["section_number"]:
                    continue
            results.append({
                "procedure_id": idx,
                "law_id": 9002,
                "law_name": "Bharatiya Nagarik Suraksha Sanhita, 2023",
                "section_id": 91000 + int(item["section_number"]),
                "section_number": item["section_number"],
                "section_title": item["section_title"],
                "procedure_category": cat,
                "title": title,
                "description": desc,
                "statutory_steps": proc.get("statutory_steps", []),
                "safeguards": proc.get("safeguards", []),
                "timeline_days": proc.get("timeline_days"),
                "source": "Official Bharatiya Nagarik Suraksha Sanhita, 2023"
            })
        return results

    @classmethod
    def get_evidence_provisions(
        cls,
        provision_type: Optional[str] = None,
        query: Optional[str] = None,
        cursor: Optional[RealDictCursor] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves evidence rules under Bharatiya Sakshya Adhiniyam (BSA)."""
        cls._load_data()
        results = []

        if cursor:
            try:
                sql = """
                    SELECT e.*, l.law_name, s.section_number, s.section_title
                    FROM evidence_provisions e
                    JOIN laws l ON e.law_id = l.law_id
                    JOIN sections s ON e.section_id = s.section_id
                    WHERE 1=1
                """
                params = []
                if provision_type:
                    sql += " AND e.provision_type ILIKE %s"
                    params.append(f"%{provision_type}%")
                if query:
                    sql += " AND (e.rule_statement ILIKE %s OR s.section_number = %s)"
                    params.extend([f"%{query}%", query])
                sql += " ORDER BY e.evidence_provision_id ASC;"
                cursor.execute(sql, tuple(params))
                rows = cursor.fetchall()
                if rows:
                    return [dict(r) for r in rows]
            except Exception:
                pass

        # In-memory fallback
        for idx, item in enumerate(cls._bsa_cache, start=1):
            ep = item.get("evidence_provision", {})
            p_type = ep.get("provision_type", item.get("provision_type", "General Evidence"))
            rule = ep.get("rule_statement", item["full_text"])
            if provision_type and provision_type.lower() not in p_type.lower():
                continue
            if query:
                q = query.lower()
                if q not in rule.lower() and q not in item["section_title"].lower() and q != item["section_number"]:
                    continue
            results.append({
                "evidence_provision_id": idx,
                "law_id": 9003,
                "law_name": "Bharatiya Sakshya Adhiniyam, 2023",
                "section_id": 92000 + int(item["section_number"]),
                "section_number": item["section_number"],
                "section_title": item["section_title"],
                "provision_type": p_type,
                "rule_statement": rule,
                "statutory_condition": ep.get("statutory_condition"),
                "admissibility_criteria": ep.get("admissibility_criteria", []),
                "source": "Official Bharatiya Sakshya Adhiniyam, 2023"
            })
        return results

    @classmethod
    def get_predecessor_mappings(
        cls,
        new_section_number: Optional[str] = None,
        old_law_name: Optional[str] = None,
        old_section_number: Optional[str] = None,
        query: Optional[str] = None,
        cursor: Optional[RealDictCursor] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves exact IPC/CrPC/IEA predecessor correlations."""
        cls._load_data()
        results = []

        if cursor:
            try:
                sql = """
                    SELECT m.*, l.law_name as new_law_name, s.section_title as new_section_title
                    FROM predecessor_law_mappings m
                    LEFT JOIN laws l ON m.new_law_id = l.law_id
                    LEFT JOIN sections s ON m.new_section_id = s.section_id
                    WHERE 1=1
                """
                params = []
                if new_section_number:
                    sql += " AND m.new_section_number = %s"
                    params.append(new_section_number)
                if old_law_name:
                    sql += " AND m.old_law_name ILIKE %s"
                    params.append(f"%{old_law_name}%")
                if old_section_number:
                    sql += " AND m.old_section_number = %s"
                    params.append(old_section_number)
                if query:
                    sql += " AND (m.new_section_number = %s OR m.old_section_number = %s OR m.key_changes_summary ILIKE %s)"
                    params.extend([query, query, f"%{query}%"])
                sql += " ORDER BY m.mapping_id ASC;"
                cursor.execute(sql, tuple(params))
                rows = cursor.fetchall()
                if rows:
                    return [dict(r) for r in rows]
            except Exception:
                pass

        # In-memory fallback
        for idx, item in enumerate(cls._pred_cache, start=1):
            n_sec = str(item["new_section_number"])
            o_law = item["old_law_name"]
            o_sec = str(item["old_section_number"])
            summary = item.get("key_changes_summary", "")

            if new_section_number and new_section_number != n_sec:
                continue
            if old_law_name and old_law_name.lower() not in o_law.lower():
                continue
            if old_section_number and old_section_number not in o_sec:
                continue
            if query:
                q = query.lower()
                if q != n_sec and q not in o_sec and q not in summary.lower() and q not in o_law.lower():
                    continue

            results.append({
                "mapping_id": idx,
                "new_law_id": 9001 if "Nyaya" in item["new_law_name"] else (9002 if "Nagarik" in item["new_law_name"] else 9003),
                "new_law_name": item["new_law_name"],
                "new_section_id": 90000 + int(n_sec) if n_sec.isdigit() else 90000,
                "new_section_number": n_sec,
                "new_section_title": f"Provision under {item['new_law_name']}",
                "old_law_name": o_law,
                "old_section_number": o_sec,
                "correspondence_type": item.get("correspondence_type", "Modified"),
                "key_changes_summary": summary,
                "source": "Official Comparative Correlation Table"
            })
        return results

    @classmethod
    def get_judgments(
        cls,
        section_number: Optional[str] = None,
        law_name: Optional[str] = None,
        query: Optional[str] = None,
        cursor: Optional[RealDictCursor] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves authoritative verified judgments interpreting provisions."""
        cls._load_data()
        results = []

        if cursor:
            try:
                sql = """
                    SELECT j.*, 
                           COALESCE(json_agg(json_build_object(
                               'law_name', l.law_name,
                               'section_number', s.section_number,
                               'relationship_type', js.relationship_type,
                               'relevance', js.relevance,
                               'explanation', js.explanation
                           )) FILTER (WHERE s.section_id IS NOT NULL), '[]'::json) AS linked_sections
                    FROM judgments j
                    LEFT JOIN judgment_sections js ON j.judgment_id = js.judgment_id
                    LEFT JOIN laws l ON js.law_id = l.law_id
                    LEFT JOIN sections s ON js.section_id = s.section_id
                    WHERE 1=1
                """
                params = []
                if section_number:
                    sql += " AND s.section_number = %s"
                    params.append(section_number)
                if query:
                    sql += " AND (j.case_title ILIKE %s OR j.citation ILIKE %s OR j.headnotes ILIKE %s)"
                    params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])
                sql += " GROUP BY j.judgment_id ORDER BY j.judgment_date DESC;"
                cursor.execute(sql, tuple(params))
                rows = cursor.fetchall()
                if rows:
                    return [dict(r) for r in rows]
            except Exception:
                pass

        # In-memory fallback
        for idx, item in enumerate(cls._judgments_cache, start=1):
            links = item.get("linked_sections", [])
            if section_number:
                matches_sec = any(str(l.get("section_number")) == str(section_number) for l in links)
                if not matches_sec:
                    continue
            if law_name:
                matches_law = any(law_name.lower() in l.get("law_name", "").lower() for l in links)
                if not matches_law:
                    continue
            if query:
                q = query.lower()
                title = item.get("case_title", "").lower()
                cit = item.get("citation", "").lower()
                notes = item.get("headnotes", "").lower()
                if q not in title and q not in cit and q not in notes:
                    continue

            results.append({
                "judgment_id": idx,
                "case_title": item["case_title"],
                "case_number": item.get("case_number"),
                "court": item["court"],
                "bench": item.get("bench"),
                "judgment_date": item.get("judgment_date"),
                "citation": item.get("citation"),
                "judgment_text": item.get("judgment_text"),
                "headnotes": item.get("headnotes"),
                "source_url": item.get("source_url"),
                "source_name": item.get("source_name", "Supreme Court of India Official Repository"),
                "source_type": item.get("source_type", "Supreme Court of India"),
                "linked_sections": links
            })
        return results

    @classmethod
    def get_section_full_context(
        cls,
        section_number: str,
        law_code: str = "BNS",
        cursor: Optional[RealDictCursor] = None
    ) -> Dict[str, Any]:
        """
        Builds a comprehensive legal intelligence graph for a section, combining:
        Statutory body text, offence classification, punishments, procedural rules,
        evidence admissibility, predecessor mappings, and controlling judicial interpretations.
        """
        cls._load_data()
        clean_sec = section_number.strip()
        law_upper = law_code.upper()

        # Find base section
        base_sec = None
        target_law_name = "Bharatiya Nyaya Sanhita, 2023"
        if "BNSS" in law_upper or "NAGARIK" in law_upper:
            target_law_name = "Bharatiya Nagarik Suraksha Sanhita, 2023"
            pool = cls._bnss_cache
        elif "BSA" in law_upper or "SAKSHYA" in law_upper:
            target_law_name = "Bharatiya Sakshya Adhiniyam, 2023"
            pool = cls._bsa_cache
        else:
            target_law_name = "Bharatiya Nyaya Sanhita, 2023"
            pool = cls._bns_cache

        for s in pool:
            if str(s.get("section_number")) == clean_sec:
                base_sec = s
                break

        if not base_sec:
            base_sec = {
                "section_number": clean_sec,
                "section_title": f"Section {clean_sec}, {target_law_name}",
                "full_text": f"Statutory provision under {target_law_name}."
            }

        # Substantive metadata
        offences = cls.get_offences(query=clean_sec, cursor=cursor)
        matched_offence = offences[0] if offences else None

        punishments = cls.get_punishments(query=clean_sec, cursor=cursor)
        matched_punishment = punishments[0] if punishments else None

        # Cross-statutory procedures
        procedures = cls.get_procedures(query=clean_sec, cursor=cursor)
        if not procedures and "BNS" in law_upper:
            # Contextual procedure linking: e.g. for Serious crimes -> Investigation under 193 BNSS, Arrest under 35 BNSS
            procedures = cls.get_procedures(query="193", cursor=cursor) + cls.get_procedures(query="35", cursor=cursor)

        # Cross-statutory evidence
        evidence = cls.get_evidence_provisions(query=clean_sec, cursor=cursor)
        if not evidence and "BNS" in law_upper:
            # Contextual evidence linking: Electronic proof under 61/63 BSA, Confessions under 22/23 BSA
            evidence = cls.get_evidence_provisions(query="63", cursor=cursor) + cls.get_evidence_provisions(query="22", cursor=cursor)

        predecessors = cls.get_predecessor_mappings(new_section_number=clean_sec, cursor=cursor)
        judgments = cls.get_judgments(section_number=clean_sec, cursor=cursor)

        return {
            "law_id": 9001 if "Nyaya" in target_law_name else (9002 if "Nagarik" in target_law_name else 9003),
            "law_name": target_law_name,
            "section_id": 90000 + (int(clean_sec) if clean_sec.isdigit() else 1),
            "section_number": clean_sec,
            "section_title": base_sec.get("section_title", f"Section {clean_sec}"),
            "full_text": base_sec.get("full_text"),
            "source_url": "https://www.indiacode.nic.in",
            "source_name": "Official Gazette / IndiaCode",
            "offence": matched_offence,
            "punishment": matched_punishment,
            "procedures": procedures[:3],
            "evidence_provisions": evidence[:3],
            "predecessor_mappings": predecessors,
            "judgments": judgments
        }
