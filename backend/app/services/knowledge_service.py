"""
Vidhik Platform - Advanced Legal Knowledge Base Service (Phase 17)
==================================================================
Service layer managing authoritative legal intelligence across ALL 24
Indian Bare Acts, including BNS, BNSS, BSA, IT Act, POCSO, JJ Act,
PWDVA, Dowry Prohibition, POSH, Hindu Marriage, Hindu Succession,
Special Marriage, Contract Act, Specific Relief, Transfer of Property,
Registration, NI Act, Consumer Protection, Motor Vehicles, RTI,
Legal Services Authorities, Arbitration, Companies Act, and IBC.

Implements resilient dual-mode architecture: executes against PostgreSQL
when connected, with automatic fallback to verified in-memory statutory
knowledge graphs to ensure zero downtime and high-availability retrieval.
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
ACTS_DATA_DIR = KB_DATA_DIR / "acts"


class LegalKnowledgeService:
    """
    Authoritative knowledge engine covering the complete 24 Indian Bare Acts
    corpus for Vidhik AI.
    """

    _registry_cache: Optional[List[Dict[str, Any]]] = None
    _master_kb_cache: Optional[Dict[str, Any]] = None
    _bns_cache: Optional[List[Dict[str, Any]]] = None

    _bnss_cache: Optional[List[Dict[str, Any]]] = None
    _bsa_cache: Optional[List[Dict[str, Any]]] = None
    _pred_cache: Optional[List[Dict[str, Any]]] = None
    _judgments_cache: Optional[List[Dict[str, Any]]] = None
    _act_sections_cache: Dict[int, List[Dict[str, Any]]] = {}
    _all_sections_cache: Optional[List[Dict[str, Any]]] = None
    _all_offences_cache: Optional[List[Dict[str, Any]]] = None
    _all_punishments_cache: Optional[List[Dict[str, Any]]] = None
    _all_procedures_cache: Optional[List[Dict[str, Any]]] = None
    _all_evidence_cache: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def _load_data(cls):
        # 1. Load 24-Act Registry
        if cls._registry_cache is None:
            reg_file = KB_DATA_DIR / "phase17_24_acts_registry.json"
            if reg_file.exists():
                with open(reg_file, "r", encoding="utf-8") as f:
                    cls._registry_cache = json.load(f)
            else:
                cls._registry_cache = []

        # 2. Load Master Knowledge Base Summary
        if cls._master_kb_cache is None:
            master_file = KB_DATA_DIR / "acts_knowledge.json"
            if master_file.exists():
                with open(master_file, "r", encoding="utf-8") as f:
                    cls._master_kb_cache = json.load(f)
            else:
                cls._master_kb_cache = {}

        # 3. Load BNS, BNSS, BSA specialized caches for backward compatibility
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

        # 4. Load all 24 Acts compiled section archives into fast memory
        if cls._all_sections_cache is None:
            cls._all_sections_cache = []
            cls._all_offences_cache = []
            cls._all_punishments_cache = []
            cls._all_procedures_cache = []
            cls._all_evidence_cache = []

            for act in cls._registry_cache:
                act_id = act["act_id"]
                short_name = act["short_name"]
                safe_short = short_name.lower().replace(" ", "_")
                act_file = ACTS_DATA_DIR / f"act_{act_id:02d}_{safe_short}.json"

                secs = []
                if act_file.exists():
                    with open(act_file, "r", encoding="utf-8") as f:
                        act_payload = json.load(f)
                        secs = act_payload.get("sections", [])

                cls._act_sections_cache[act_id] = secs

                for s in secs:
                    cls._all_sections_cache.append(s)
                    if s.get("is_offence") and s.get("offence"):
                        cls._all_offences_cache.append(s)
                    if s.get("punishment"):
                        cls._all_punishments_cache.append(s)
                    if s.get("procedure"):
                        cls._all_procedures_cache.append(s)
                    if s.get("evidence"):
                        cls._all_evidence_cache.append(s)

    @classmethod
    def get_overview(cls, cursor: Optional[RealDictCursor] = None) -> Dict[str, Any]:
        """Returns comprehensive overview across all 24 Bare Acts."""
        cls._load_data()

        # Compile list of all supported statutes
        supported = [f"{a['act_name']} ({a['short_name']})" for a in cls._registry_cache]

        total_offences = len(cls._all_offences_cache)
        total_punishments = len(cls._all_punishments_cache)
        total_procedures = len(cls._all_procedures_cache)
        total_evidence = len(cls._all_evidence_cache)
        total_preds = len(cls._pred_cache)
        total_judgments = len(cls._judgments_cache)
        total_secs = len(cls._all_sections_cache)

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
            "supported_statutes": supported,
            "total_new_statutes": len(cls._registry_cache),
            "total_acts": len(cls._registry_cache),
            "total_sections": total_secs,
            "total_offences": total_offences,
            "total_punishments": total_punishments,
            "total_procedures": total_procedures,
            "total_evidence_provisions": total_evidence,
            "total_predecessor_mappings": total_preds,
            "total_verified_judgments": total_judgments,
            "categories": {
                "total_acts": len(cls._registry_cache),
                "total_sections": total_secs,
                "offences": total_offences,
                "punishments": total_punishments,
                "procedures": total_procedures,
                "evidence_provisions": total_evidence,
                "predecessor_mappings": total_preds,
                "verified_judgments": total_judgments
            }
        }

    @classmethod
    def get_acts(cls, cursor: Optional[RealDictCursor] = None) -> List[Dict[str, Any]]:
        """Returns catalog of all 24 Bare Acts with metadata and statutory properties."""
        cls._load_data()
        return cls._registry_cache

    @classmethod
    def get_act_by_id(cls, act_identifier: Any, cursor: Optional[RealDictCursor] = None) -> Optional[Dict[str, Any]]:
        """Returns full Act details including all statutory sections."""
        cls._load_data()
        act_meta = None
        for a in cls._registry_cache:
            if str(a["act_id"]) == str(act_identifier) or a["short_name"].lower() == str(act_identifier).lower() or a["act_name"].lower() == str(act_identifier).lower():
                act_meta = a
                break

        if not act_meta:
            return None

        act_id = act_meta["act_id"]
        sections = cls._act_sections_cache.get(act_id, [])
        return {
            "act_metadata": act_meta,
            "total_sections": len(sections),
            "sections": sections
        }

    @classmethod
    def get_offences(
        cls,
        law_id: Optional[int] = None,
        section_id: Optional[int] = None,
        query: Optional[str] = None,
        cursor: Optional[RealDictCursor] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves structured offences across all applicable Acts in the 24-Act corpus."""
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
                    sql += " AND (o.offence_name ILIKE %s OR o.description ILIKE %s OR s.section_number = %s)"
                    params.extend([f"%{query}%", f"%{query}%", query])
                sql += " ORDER BY o.offence_id ASC;"
                cursor.execute(sql, tuple(params))
                rows = cursor.fetchall()
                if rows:
                    return [dict(r) for r in rows]
            except Exception:
                pass

        # In-memory retrieval across all 24 Acts
        idx = 1
        for s in cls._all_offences_cache:
            if law_id and s.get("law_id") != law_id:
                continue
            off = s.get("offence", {})
            name = off.get("offence_name", "")
            desc = off.get("description", "")
            sec_num = str(s.get("section_number", ""))
            sec_title = s.get("section_title", "")

            if query:
                q = query.lower()
                if (q not in name.lower() and 
                    q not in desc.lower() and 
                    q not in sec_title.lower() and 
                    q != sec_num and
                    q not in s.get("short_name", "").lower()):
                    continue

            results.append({
                "offence_id": idx,
                "law_id": s.get("law_id", 1),
                "law_name": s.get("law_name", "Bharatiya Nyaya Sanhita, 2023"),
                "section_id": 90000 + idx,
                "section_number": sec_num,
                "section_title": sec_title,
                "offence_name": name,
                "description": desc,
                "section_reference": off.get("section_reference", f"Section {sec_num}, {s.get('short_name')}"),
                "cognizable_status": off.get("cognizable_status", "Cognizable"),
                "bailable_status": off.get("bailable_status", "Non-Bailable"),
                "compoundable_status": off.get("compoundable_status", "Non-Compoundable"),
                "triable_by": off.get("triable_by", "Magistrate of First Class"),
                "source": s.get("provenance", "Official Statutory Source")
            })
            idx += 1
        return results

    @classmethod
    def get_punishments(
        cls,
        offence_id: Optional[int] = None,
        section_id: Optional[int] = None,
        query: Optional[str] = None,
        cursor: Optional[RealDictCursor] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves structured statutory punishments across the 24-Act corpus."""
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
                    sql += " AND (p.punishment_type ILIKE %s OR p.description ILIKE %s OR s.section_number = %s)"
                    params.extend([f"%{query}%", f"%{query}%", query])
                sql += " ORDER BY p.punishment_id ASC;"
                cursor.execute(sql, tuple(params))
                rows = cursor.fetchall()
                if rows:
                    return [dict(r) for r in rows]
            except Exception:
                pass

        # In-memory retrieval across all 24 Acts
        idx = 1
        for s in cls._all_punishments_cache:
            pun = s.get("punishment", {})
            p_type = pun.get("punishment_type", "")
            p_desc = pun.get("description", "")
            sec_num = str(s.get("section_number", ""))
            sec_title = s.get("section_title", "")

            if query:
                q = query.lower()
                if (q not in p_type.lower() and 
                    q not in p_desc.lower() and 
                    q not in sec_title.lower() and 
                    q != sec_num and
                    q not in s.get("short_name", "").lower()):
                    continue

            results.append({
                "punishment_id": idx,
                "law_id": s.get("law_id", 1),
                "law_name": s.get("law_name", "Bharatiya Nyaya Sanhita, 2023"),
                "section_id": 90000 + idx,
                "section_number": sec_num,
                "section_title": sec_title,
                "offence_id": idx if s.get("is_offence") else None,
                "offence_name": s.get("offence", {}).get("offence_name") if s.get("offence") else None,
                "punishment_type": p_type,
                "description": p_desc,
                "minimum_punishment": pun.get("minimum_punishment"),
                "maximum_punishment": pun.get("maximum_punishment"),
                "fine_details": pun.get("fine_details"),
                "imprisonment_details": pun.get("imprisonment_details"),
                "community_service": pun.get("community_service", False),
                "other_penalty": pun.get("other_penalty"),
                "source": s.get("provenance", "Official Statutory Source")
            })
            idx += 1
        return results

    @classmethod
    def get_procedures(
        cls,
        category: Optional[str] = None,
        query: Optional[str] = None,
        cursor: Optional[RealDictCursor] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves procedural workflows under BNSS and procedural provisions in other Acts."""
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

        # In-memory retrieval across BNSS and procedural provisions
        idx = 1
        seen_keys = set()
        # Include BNSS specialized cache first for backward compatibility
        for item in cls._bnss_cache:
            proc = item.get("procedure", {})
            title = proc.get("title", item.get("section_title", ""))
            cat = proc.get("procedure_category", item.get("procedure_category", "General Procedure"))
            desc = proc.get("description", item.get("full_text", ""))
            sec_num = str(item.get("section_number", ""))
            seen_keys.add((2, sec_num))

            if category and category.lower() not in cat.lower():
                continue
            if query:
                q = query.lower()
                if q not in title.lower() and q not in desc.lower() and q != sec_num:
                    continue

            results.append({
                "procedure_id": idx,
                "law_id": 2,
                "law_name": "Bharatiya Nagarik Suraksha Sanhita, 2023",
                "section_id": 91000 + (int(sec_num) if sec_num.isdigit() else idx),
                "section_number": sec_num,
                "section_title": item.get("section_title", f"Section {sec_num}"),
                "procedure_category": cat,
                "title": title,
                "description": desc,
                "statutory_steps": proc.get("statutory_steps", []),
                "safeguards": proc.get("safeguards", []),
                "timeline_days": proc.get("timeline_days"),
                "source": "Official Bharatiya Nagarik Suraksha Sanhita, 2023"
            })
            idx += 1

        # Include other procedural statutes (e.g. CPA, Arbitration, PWDVA, RTI, IBC, JJ Act)
        for s in cls._all_procedures_cache:
            sec_num = str(s.get("section_number", ""))
            law_id = s.get("law_id", 1)
            if (law_id, sec_num) in seen_keys:
                continue
            seen_keys.add((law_id, sec_num))

            proc = s.get("procedure", {})
            cat = proc.get("procedure_category", "Statutory Procedure")
            title = proc.get("title", s.get("section_title", ""))
            desc = proc.get("description", s.get("full_text", "")[:350])


            if category and category.lower() not in cat.lower():
                continue
            if query:
                q = query.lower()
                if (q not in title.lower() and 
                    q not in desc.lower() and 
                    q != sec_num and 
                    q not in s.get("short_name", "").lower()):
                    continue

            results.append({
                "procedure_id": idx,
                "law_id": s.get("law_id", 1),
                "law_name": s.get("law_name", "Statutory Procedure"),
                "section_id": 91000 + idx,
                "section_number": sec_num,
                "section_title": s.get("section_title", f"Section {sec_num}"),
                "procedure_category": cat,
                "title": title,
                "description": desc,
                "statutory_steps": proc.get("statutory_steps", []),
                "safeguards": proc.get("safeguards", []),
                "timeline_days": proc.get("timeline_days"),
                "source": s.get("provenance", "Official Statutory Source")
            })
            idx += 1

        return results

    @classmethod
    def get_evidence_provisions(
        cls,
        provision_type: Optional[str] = None,
        query: Optional[str] = None,
        cursor: Optional[RealDictCursor] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves evidence rules and legal presumptions across BSA and related Acts."""
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

        # In-memory retrieval: BSA specialized first
        idx = 1
        seen_keys = set()
        for item in cls._bsa_cache:
            ep = item.get("evidence_provision", {})
            p_type = ep.get("provision_type", item.get("provision_type", "General Evidence"))
            rule = ep.get("rule_statement", item.get("full_text", ""))
            sec_num = str(item.get("section_number", ""))
            seen_keys.add((3, sec_num))

            if provision_type and provision_type.lower() not in p_type.lower():
                continue
            if query:
                q = query.lower()
                if q not in rule.lower() and q not in item.get("section_title", "").lower() and q != sec_num:
                    continue

            results.append({
                "evidence_provision_id": idx,
                "law_id": 3,
                "law_name": "Bharatiya Sakshya Adhiniyam, 2023",
                "section_id": 92000 + (int(sec_num) if sec_num.isdigit() else idx),
                "section_number": sec_num,
                "section_title": item.get("section_title", f"Section {sec_num}"),
                "provision_type": p_type,
                "rule_statement": rule,
                "statutory_condition": ep.get("statutory_condition"),
                "admissibility_criteria": ep.get("admissibility_criteria", []),
                "source": "Official Bharatiya Sakshya Adhiniyam, 2023"
            })
            idx += 1

        # Other evidence/presumption provisions (e.g. NI Act 139, POCSO 29/30, DPA 8A)
        for s in cls._all_evidence_cache:
            sec_num = str(s.get("section_number", ""))
            law_id = s.get("law_id", 1)
            if (law_id, sec_num) in seen_keys:
                continue
            seen_keys.add((law_id, sec_num))

            ev = s.get("evidence", {})
            p_type = ev.get("provision_type", "Statutory Presumption")
            rule = ev.get("rule_statement", s.get("full_text", "")[:300])
            sec_num = str(s.get("section_number", ""))

            if provision_type and provision_type.lower() not in p_type.lower():
                continue
            if query:
                q = query.lower()
                if (q not in rule.lower() and 
                    q not in s.get("section_title", "").lower() and 
                    q != sec_num and
                    q not in s.get("short_name", "").lower()):
                    continue

            results.append({
                "evidence_provision_id": idx,
                "law_id": s.get("law_id", 1),
                "law_name": s.get("law_name", "Evidence Provision"),
                "section_id": 92000 + idx,
                "section_number": sec_num,
                "section_title": s.get("section_title", f"Section {sec_num}"),
                "provision_type": p_type,
                "rule_statement": rule,
                "statutory_condition": ev.get("statutory_condition"),
                "admissibility_criteria": ev.get("admissibility_criteria", []),
                "source": s.get("provenance", "Official Statutory Source")
            })
            idx += 1

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
        """Retrieves exact comparative predecessor correlations."""
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
            if new_section_number and str(item.get("new_section_number")) != str(new_section_number):
                continue
            if old_law_name and old_law_name.lower() not in item.get("old_law_name", "").lower():
                continue
            if old_section_number and str(item.get("old_section_number")) != str(old_section_number):
                continue
            if query:
                q = query.lower()
                sum_text = item.get("key_changes_summary", "").lower()
                n_sec = str(item.get("new_section_number", ""))
                o_sec = str(item.get("old_section_number", ""))
                if q not in sum_text and q != n_sec and q != o_sec:
                    continue

            results.append({
                "mapping_id": idx,
                "new_law_id": 9001 if "BNS" in item.get("new_law_name", "") else 9002,
                "new_law_name": item.get("new_law_name", ""),
                "new_section_id": 90000 + int(item["new_section_number"]) if item.get("new_section_number", "").isdigit() else 90001,
                "new_section_number": item["new_section_number"],
                "new_section_title": item.get("new_section_title"),
                "old_law_name": item["old_law_name"],
                "old_section_number": item["old_section_number"],
                "correspondence_type": item.get("correspondence_type", "Substantially Altered"),
                "key_changes_summary": item.get("key_changes_summary"),
                "source": "Official Comparative Correlation Table"
            })
        return results

    @classmethod
    def get_judgments(
        cls,
        section_number: Optional[str] = None,
        law_name: Optional[str] = None,
        act_id: Optional[int] = None,
        query: Optional[str] = None,
        cursor: Optional[RealDictCursor] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves verified landmark judicial interpretations.
        For Acts 4-24 where case law is not in project source, returns empty list
        with authoritative status preserved as 'NOT IN SOURCE'.
        """
        cls._load_data()
        
        # If explicitly querying for an Act outside Acts 1-3, return empty (NOT IN SOURCE)
        if act_id and act_id > 3:
            return []

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

        # In-memory fallback for verified Supreme Court precedents (Acts 1-3)
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
        Builds a comprehensive legal intelligence graph for any section in the 24 Acts.
        """
        cls._load_data()
        clean_sec = section_number.strip()
        code_upper = law_code.strip().upper()

        # Resolve Target Act
        target_act = None
        for a in cls._registry_cache:
            if (a["short_name"].upper() == code_upper or 
                a["act_name"].upper() == code_upper or 
                str(a["act_id"]) == code_upper or
                code_upper in a["short_name"].upper() or
                code_upper in a["act_name"].upper()):
                target_act = a
                break

        if not target_act:
            # Fallback to BNS
            target_act = cls._registry_cache[0]

        act_id = target_act["act_id"]
        law_name = target_act["act_name"]
        short_name = target_act["short_name"]

        # Search for the section in the resolved Act's sections
        act_sections = cls._act_sections_cache.get(act_id, [])
        base_sec = None
        for s in act_sections:
            if str(s.get("section_number")) == clean_sec:
                base_sec = s
                break

        if not base_sec:
            base_sec = {
                "section_number": clean_sec,
                "section_title": f"Section {clean_sec}, {short_name}",
                "full_text": f"Statutory provision under {law_name}.",
                "provenance": target_act["provenance"]
            }

        # Substantive metadata
        offences = cls.get_offences(law_id=act_id, query=clean_sec, cursor=cursor)
        matched_offence = offences[0] if offences else None

        punishments = cls.get_punishments(query=clean_sec, cursor=cursor)
        matched_punishment = punishments[0] if punishments else None

        procedures = cls.get_procedures(query=clean_sec, cursor=cursor)
        if not procedures and act_id == 1:
            procedures = cls.get_procedures(query="193", cursor=cursor) + cls.get_procedures(query="35", cursor=cursor)

        evidence = cls.get_evidence_provisions(query=clean_sec, cursor=cursor)
        if not evidence and act_id == 1:
            evidence = cls.get_evidence_provisions(query="63", cursor=cursor) + cls.get_evidence_provisions(query="22", cursor=cursor)

        predecessors = cls.get_predecessor_mappings(new_section_number=clean_sec, cursor=cursor)
        judgments = cls.get_judgments(section_number=clean_sec, act_id=act_id, cursor=cursor)

        return {
            "law_id": act_id,
            "law_name": law_name,
            "section_id": 90000 + (int(clean_sec) if clean_sec.isdigit() else 1),
            "section_number": clean_sec,
            "section_title": base_sec.get("section_title", f"Section {clean_sec}"),
            "full_text": base_sec.get("full_text"),
            "source_url": "https://www.indiacode.nic.in",
            "source_name": base_sec.get("provenance", target_act["provenance"]),
            "offence": matched_offence,
            "punishment": matched_punishment,
            "procedures": procedures[:3],
            "evidence_provisions": evidence[:3],
            "predecessor_mappings": predecessors,
            "judgments": judgments
        }

    @classmethod
    def search_knowledge_base(
        cls,
        query: str,
        act_filter: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[RealDictCursor] = None
    ) -> List[Dict[str, Any]]:
        """Multi-statute search across all 24 Bare Acts."""
        cls._load_data()
        q_lower = query.lower().strip()
        results = []

        pool = cls._all_sections_cache
        if act_filter:
            act_filter_upper = act_filter.upper()
            pool = [s for s in pool if s.get("short_name", "").upper() == act_filter_upper or act_filter_upper in s.get("law_name", "").upper()]

        for s in pool:
            score = 0
            sec_num = str(s.get("section_number", ""))
            sec_title = s.get("section_title", "")
            full_txt = s.get("full_text", "")
            short_name = s.get("short_name", "")
            law_name = s.get("law_name", "")
            off = s.get("offence") or {}
            off_name = off.get("offence_name", "")
            off_desc = off.get("description", "")
            proc = s.get("procedure") or {}
            proc_title = proc.get("title", "")
            proc_cat = proc.get("procedure_category", "")
            ev = s.get("evidence") or {}
            ev_rule = ev.get("rule_statement", "")

            combined_meta = f"{short_name} {law_name} {sec_title} {off_name} {off_desc} {proc_title} {proc_cat} {ev_rule}".lower()

            if q_lower == sec_num.lower():
                score += 100
            elif q_lower in sec_title.lower():
                score += 60
            elif q_lower in off_name.lower():
                score += 55
            elif q_lower in short_name.lower():
                score += 50
            elif q_lower in law_name.lower():
                score += 45
            elif q_lower in combined_meta:
                score += 35
            elif q_lower in full_txt.lower():
                score += 20
            else:
                # Token matching
                tokens = q_lower.split()
                if any(t in sec_title.lower() or t in off_name.lower() for t in tokens):
                    score += 15
                elif any(t in combined_meta for t in tokens):
                    score += 12
                elif any(t in full_txt.lower() for t in tokens):
                    score += 5



            if score > 0:
                results.append({
                    "score": score,
                    "act_id": s.get("law_id"),
                    "act_name": s.get("law_name"),
                    "short_name": s.get("short_name"),
                    "section_number": sec_num,
                    "section_title": sec_title,
                    "snippet": full_txt[:250] + ("..." if len(full_txt) > 250 else ""),
                    "is_offence": s.get("is_offence", False),
                    "has_punishment": bool(s.get("punishment")),
                    "has_procedure": bool(s.get("procedure")),
                    "has_evidence": bool(s.get("evidence"))
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
