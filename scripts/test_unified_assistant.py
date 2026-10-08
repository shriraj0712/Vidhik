import sys
import os

# Set UTF-8 encoding for stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend path is on sys.path
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

test_cases = [
    {
        "domain": "Constitution of India",
        "query": "What is Article 21?",
        "lang": "en"
    },
    {
        "domain": "Constitution Fundamental Rights",
        "query": "What is Article 14?",
        "lang": "en"
    },
    {
        "domain": "Criminal Law (BNS)",
        "query": "What is the punishment for theft?",
        "lang": "en"
    },
    {
        "domain": "Criminal Procedure (BNSS)",
        "query": "How can I get bail?",
        "lang": "en"
    },
    {
        "domain": "Multi-Law / Unlawful Arrest (Constitution + BNSS)",
        "query": "Police arrested me without telling me the reason. What are my rights and what can I do?",
        "lang": "en"
    },
    {
        "domain": "Consumer Protection Bare Act",
        "query": "What can I do about a defective product?",
        "lang": "en"
    },
    {
        "domain": "Labour & Wages Bare Act",
        "query": "What can I do if my employer doesn't pay my salary?",
        "lang": "en"
    },
    {
        "domain": "Contract Law Bare Act",
        "query": "What happens if a contract is breached?",
        "lang": "en"
    },
    {
        "domain": "Cyber & Personal Data",
        "query": "What can I do if someone steals my personal information online?",
        "lang": "en"
    },
    {
        "domain": "Evidence (BSA)",
        "query": "What evidence is admissible in court under BSA?",
        "lang": "en"
    },
    {
        "domain": "Multilingual Hindi",
        "query": "अगर पुलिस मुझे गिरफ्तार करती है तो मेरे क्या अधिकार हैं?",
        "lang": "hi"
    },
    {
        "domain": "Multilingual Marathi",
        "query": "पोलिसांनी मला अटक केली तर माझे अधिकार काय आहेत?",
        "lang": "mr"
    },
    {
        "domain": "Document Context Integration",
        "query": "What does this legal notice say and what sections are mentioned?",
        "lang": "en",
        "doc_title": "Demand Notice for Alleged Defamation",
        "doc_text": "This is a formal notice issued under Section 356 of Bharatiya Nyaya Sanhita, 2023 demanding unconditional apology and damages of Rs. 10 Lakhs within 15 days failing which criminal proceedings will be initiated."
    }
]

print("=" * 75)
print("VIDHIK AI UNIFIED LEGAL ASSISTANT — COMPLETE ACCEPTANCE VERIFICATION")
print("=" * 75)

passed = 0
failed = 0

for idx, tc in enumerate(test_cases, 1):
    print(f"\n[TEST {idx}/{len(test_cases)}] Domain: {tc['domain']}")
    print(f"Query: \"{tc['query']}\" (Lang: {tc['lang']})")
    if "doc_title" in tc:
        print(f"Document Attached: {tc['doc_title']}")

    payload = {
        "message": tc["query"],
        "language": tc["lang"]
    }
    if "doc_text" in tc:
        payload["document_text"] = tc["doc_text"]
    if "doc_title" in tc:
        payload["document_title"] = tc["doc_title"]

    resp = client.post("/api/assistant/chat", json=payload)
    if resp.status_code != 200:
        print(f"HTTP ERROR: {resp.status_code} - {resp.text}")
        failed += 1
        continue

    data = resp.json()
    is_grounded = data.get("is_grounded", False)
    sources = data.get("sources", [])
    answer = data.get("answer", "")

    print(f"Status: HTTP 200 | Grounded: {is_grounded} | Sources Retrieved: {len(sources)}")
    for s in sources[:4]:
        law = s.get("short_name") or s.get("law_name")
        sec = s.get("section_number") or s.get("article_number")
        title = s.get("section_title") or ""
        print(f"   • {law} [{sec}]: {title[:55]}")

    clean_preview = answer[:220].replace("\n", " ").strip()
    print(f"Answer Head: {clean_preview}...")

    # Verification criteria
    if is_grounded and len(sources) > 0 and len(answer) > 60:
        passed += 1
        print(">>> RESULT: [PASS]")
    else:
        failed += 1
        print(">>> RESULT: [FAIL]")

# Conversational follow-up memory test
print("\n[TEST 14/14] Conversational Follow-Up Memory Context")
conv_1 = client.post("/api/assistant/chat", json={"message": "What is bail?", "language": "en"})
data_1 = conv_1.json()
conv_id = data_1.get("conversation_id")
print(f"Turn 1 ('What is bail?') -> Conversation ID: {conv_id}")

conv_2 = client.post("/api/assistant/chat", json={
    "message": "Can I get it if arrested for theft?",
    "conversation_id": conv_id,
    "language": "en"
})
data_2 = conv_2.json()
answer_2 = data_2.get("answer", "")
sources_2 = data_2.get("sources", [])
print(f"Turn 2 ('Can I get it if arrested for theft?') -> Sources: {len(sources_2)}")
print(f"Answer Head: {answer_2[:220].replace(chr(10), ' ').strip()}...")

if len(sources_2) > 0 and len(answer_2) > 60:
    passed += 1
    print(">>> RESULT: [PASS]")
else:
    failed += 1
    print(">>> RESULT: [FAIL]")

print("\n" + "=" * 75)
print(f"FINAL RESULT: {passed} PASSED / {failed} FAILED (TOTAL {len(test_cases) + 1} TESTS)")
print("=" * 75)
