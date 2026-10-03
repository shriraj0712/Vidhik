"""
VIDHIK LEGAL PLATFORM - PHASE 17 VERIFICATION SUITE
===================================================
Automated verification suite validating:
1. BNS statutory provisions, offences, punishments, and community service
2. BNSS procedural provisions (FIR, arrest, search videography, undertrial bail)
3. BSA evidence rules (digital evidence parity, Section 63 certificates)
4. Exact IPC/CrPC/IEA predecessor law mappings
5. Verified Supreme Court of India landmark judgments and section linking
6. Full Section Legal Context Graph
7. Deterministic LegalSearchService and LegalRankingService integration
"""

import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.services.knowledge_service import LegalKnowledgeService
from app.services.search_service import LegalSearchService
from app.services.ranking_service import LegalRankingService
from app.schemas.search import SearchResponse

print("=" * 70)
print("VIDHIK PHASE 17 - ADVANCED LEGAL KNOWLEDGE BASE VERIFICATION")
print("=" * 70)

# TEST 1: KNOWLEDGE BASE OVERVIEW
print("\n[TEST 1/8] Verifying Knowledge Base Overview...")
overview = LegalKnowledgeService.get_overview()
assert overview["status"] == "active", "Expected active status"
assert overview["total_new_statutes"] == 3, "Expected 3 new statutes"
assert overview["total_offences"] > 0, "Expected non-zero offences"
assert overview["total_procedures"] > 0, "Expected non-zero procedures"
assert overview["total_evidence_provisions"] > 0, "Expected non-zero evidence rules"
assert overview["total_predecessor_mappings"] > 0, "Expected non-zero predecessor mappings"
assert overview["total_verified_judgments"] > 0, "Expected non-zero verified judgments"
print(f"  ✓ Overview verified: {overview['total_offences']} Offences, {overview['total_procedures']} Procedures, {overview['total_evidence_provisions']} Evidence Rules, {overview['total_predecessor_mappings']} Mappings, {overview['total_verified_judgments']} Judgments")

# TEST 2: BNS OFFENCES & PUNISHMENTS
print("\n[TEST 2/8] Verifying Bharatiya Nyaya Sanhita, 2023 (BNS)...")
offences = LegalKnowledgeService.get_offences()
punishments = LegalKnowledgeService.get_punishments()
assert len(offences) >= 5, "Expected at least 5 structured offences"
assert len(punishments) >= 5, "Expected at least 5 structured punishments"

# Verify Murder & Mob Lynching (Sec 103)
murd_off = [o for o in offences if o["section_number"] == "103"]
assert len(murd_off) == 1, "Section 103 Murder not found"
assert "Murder" in murd_off[0]["offence_name"], "Incorrect offence name for Sec 103"
assert murd_off[0]["bailable_status"] == "Non-Bailable", "Sec 103 should be Non-Bailable"
print(f"  ✓ Section 103 BNS verified: {murd_off[0]['offence_name']} [{murd_off[0]['bailable_status']}]")

# Verify Hit-and-Run (Sec 106)
hit_off = [o for o in offences if o["section_number"] == "106"]
assert len(hit_off) == 1, "Section 106 Hit-and-Run not found"
print(f"  ✓ Section 106 BNS verified: {hit_off[0]['offence_name']}")

# Verify Petty Theft & Community Service (Sec 303)
theft_pun = [p for p in punishments if p["section_number"] == "303"]
assert len(theft_pun) == 1, "Section 303 Theft punishment not found"
assert theft_pun[0]["community_service"] is True, "Community service should be enabled for first-time petty theft"
print(f"  ✓ Section 303 BNS verified: Community service provision active")

# TEST 3: BNSS PROCEDURES
print("\n[TEST 3/8] Verifying Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)...")
procedures = LegalKnowledgeService.get_procedures()
assert len(procedures) >= 5, "Expected at least 5 structured procedures"

# Check e-FIR & Zero FIR (Sec 173)
fir_proc = [p for p in procedures if p["section_number"] == "173"]
assert len(fir_proc) == 1, "Section 173 FIR procedure not found"
assert "Zero FIR" in fir_proc[0]["title"], "Zero FIR not documented in Sec 173"
assert fir_proc[0]["timeline_days"] == 14, "Preliminary enquiry should be 14 days"
print(f"  ✓ Section 173 BNSS verified: {fir_proc[0]['title']} (Timeline: {fir_proc[0]['timeline_days']} days)")

# Check Audio-Video Recording of Search and Seizure (Sec 105)
search_proc = [p for p in procedures if p["section_number"] == "105"]
assert len(search_proc) == 1, "Section 105 Search/Seizure videography not found"
print(f"  ✓ Section 105 BNSS verified: {search_proc[0]['title']}")

# Check Undertrial Bail 1/3rd rule (Sec 479)
bail_proc = [p for p in procedures if p["section_number"] == "479"]
assert len(bail_proc) == 1, "Section 479 Bail procedure not found"
print(f"  ✓ Section 479 BNSS verified: {bail_proc[0]['title']}")

# TEST 4: BSA EVIDENCE PROVISIONS
print("\n[TEST 4/8] Verifying Bharatiya Sakshya Adhiniyam, 2023 (BSA)...")
evidence_rules = LegalKnowledgeService.get_evidence_provisions()
assert len(evidence_rules) >= 5, "Expected at least 5 structured evidence provisions"

# Check Digital Evidence Parity (Sec 61) & Electronic Certificate (Sec 63)
sec61 = [e for e in evidence_rules if e["section_number"] == "61"]
assert len(sec61) == 1, "Section 61 BSA not found"
print(f"  ✓ Section 61 BSA verified: {sec61[0]['provision_type']} parity established")

sec63 = [e for e in evidence_rules if e["section_number"] == "63"]
assert len(sec63) == 1, "Section 63 BSA not found"
assert "Section 63" in sec63[0]["rule_statement"] or "computer" in sec63[0]["rule_statement"].lower()
print(f"  ✓ Section 63 BSA verified: {sec63[0]['provision_type']} certificate standards verified")

# TEST 5: PREDECESSOR CORRELATIONS
print("\n[TEST 5/8] Verifying Predecessor Law Mappings (IPC/CrPC/IEA)...")
preds = LegalKnowledgeService.get_predecessor_mappings()
assert len(preds) >= 15, "Expected at least 15 predecessor mappings"

# Verify IPC 302 -> BNS 103
p_103 = [p for p in preds if p["new_section_number"] == "103" and "Indian Penal Code" in p["old_law_name"]]
assert len(p_103) == 1, "Mapping IPC 302 -> BNS 103 not found"
assert p_103[0]["old_section_number"] == "302", "Expected old section 302"
print(f"  ✓ Predecessor Mapping verified: IPC Section {p_103[0]['old_section_number']} → BNS Section {p_103[0]['new_section_number']}")

# Verify IEA 65B -> BSA 63
p_63 = [p for p in preds if p["new_section_number"] == "63" and "Indian Evidence Act" in p["old_law_name"]]
assert len(p_63) == 1, "Mapping IEA 65B -> BSA 63 not found"
assert p_63[0]["old_section_number"] == "65B", "Expected old section 65B"
print(f"  ✓ Predecessor Mapping verified: IEA Section {p_63[0]['old_section_number']} → BSA Section {p_63[0]['new_section_number']}")

# TEST 6: VERIFIED SUPREME COURT JUDGMENTS
print("\n[TEST 6/8] Verifying Landmark Supreme Court Judgments...")
judgments = LegalKnowledgeService.get_judgments()
assert len(judgments) >= 4, "Expected at least 4 verified landmark judgments"

# Check Arjun Panditrao Khotkar
arjun = [j for j in judgments if "Arjun Panditrao Khotkar" in j["case_title"]]
assert len(arjun) == 1, "Arjun Panditrao Khotkar judgment not found"
assert arjun[0]["citation"] == "(2020) 7 SCC 1", "Incorrect citation for Arjun Panditrao Khotkar"
print(f"  ✓ Judgment verified: {arjun[0]['case_title']} [{arjun[0]['citation']}]")

# Check Satender Kumar Antil
satender = [j for j in judgments if "Satender Kumar Antil" in j["case_title"]]
assert len(satender) == 1, "Satender Kumar Antil judgment not found"
assert satender[0]["citation"] == "(2022) 10 SCC 51", "Incorrect citation for Satender Kumar Antil"
print(f"  ✓ Judgment verified: {satender[0]['case_title']} [{satender[0]['citation']}]")

# TEST 7: SECTION FULL CONTEXT GRAPH
print("\n[TEST 7/8] Verifying Section Full Legal Context Graph...")
context_103 = LegalKnowledgeService.get_section_full_context("103", "BNS")
assert context_103["section_number"] == "103"
assert context_103["offence"] is not None
assert context_103["punishment"] is not None
assert len(context_103["procedures"]) > 0, "Expected cross-statute procedures linked"
assert len(context_103["evidence_provisions"]) > 0, "Expected cross-statute evidence linked"
assert len(context_103["predecessor_mappings"]) > 0, "Expected predecessor mappings linked"
assert len(context_103["judgments"]) > 0, "Expected controlling judgments linked"
print(f"  ✓ Section 103 BNS Full Legal Graph successfully assembled (Offence + Punishment + Procedures + Evidence + Predecessors + Judgments)")

# TEST 8: DETERMINISTIC LEGAL SEARCH INTEGRATION
print("\n[TEST 8/8] Verifying LegalSearchService & Deterministic Ranking...")
# Test snippet extraction
snippet = LegalSearchService.extract_snippet(
    full_text="Whoever causes death by doing an act with the intention of causing death commits culpable homicide.",
    description="Culpable homicide definition",
    section_title="Culpable homicide",
    law_name="Bharatiya Nyaya Sanhita, 2023",
    query="culpable homicide"
)
assert snippet is not None, "Snippet extraction failed"
assert "culpable homicide" in snippet.lower(), "Snippet does not contain query keyword"
print(f"  ✓ Snippet Extraction: '{snippet}'")

# Test ranking deterministic consistency
cand1 = {
    "law_id": 9001,
    "law_name": "Bharatiya Nyaya Sanhita, 2023",
    "short_name": "BNS",
    "section_id": 90103,
    "section_number": "103",
    "section_title": "Punishment for murder",
    "description": "Punishment for murder and mob lynching",
    "full_text": "Whoever commits murder shall be punished with death or imprisonment for life.",
    "jurisdiction": "Central",
    "manual_review_required": False
}
cand2 = {
    "law_id": 14,
    "law_name": "The Air (Prevention and Control of Pollution) Act, 1981",
    "short_name": "Air Act",
    "section_id": 566,
    "section_number": "5",
    "section_title": "Constitution of State Boards",
    "description": "Board constitution",
    "full_text": "State boards constitution and provisions.",
    "jurisdiction": "Central",
    "manual_review_required": False
}

ranked = LegalRankingService.rank_candidates([cand2, cand1], query="103")
assert ranked[0]["section_number"] == "103", "Exact section number 103 should rank first"
print("  ✓ Deterministic LegalRankingService: Exact section match prioritizes Tier 1 successfully")

print("\n" + "=" * 70)
print("ALL 8 VERIFICATION TESTS PASSED WITH 100% SUCCESS!")
print("=" * 70)
