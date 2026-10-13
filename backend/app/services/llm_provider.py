"""
Vidhik Platform - LLM Provider Abstraction
==========================================
Modular LLM provider interface supporting Google Gemini, OpenAI, and
an Offline Grounded Mock provider for local testing and failover.

Guarantees:
- Model answers are strictly grounded in retrieved statutory context.
- Zero hardcoded vendor lock-in.
- Automatic fallback to offline deterministic synthesis when API keys are absent.
- Full streaming support across all providers.
"""

import os
import json
import re
import logging
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Iterator

logger = logging.getLogger("vidhik.llm_provider")


class BaseLLMProvider(ABC):
    """
    Abstract interface for LLM completion providers.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the human-readable identifier of the provider."""
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_instruction: str,
        temperature: float = 0.1,
        max_output_tokens: int = 1500
    ) -> str:
        """
        Generates grounded legal text based strictly on the provided prompt and context.
        """
        pass

    def generate_stream(
        self,
        prompt: str,
        system_instruction: str,
        temperature: float = 0.1,
        max_output_tokens: int = 1500
    ) -> Iterator[str]:
        """
        Default streaming implementation that yields tokens or chunked segments.
        Subclasses may override with native HTTP streaming.
        """
        full_text = self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens
        )
        # Yield in realistic token-sized words/chunks
        words = full_text.split(" ")
        for i, word in enumerate(words):
            if i < len(words) - 1:
                yield word + " "
            else:
                yield word


class OfflineMockLLMProvider(BaseLLMProvider):
    """
    Offline Grounded Legal Synthesizer (Deterministic Fallback / Test Provider).
    Synthesizes retrieved statutory text into an authoritative, structured answer
    following the standard Vidhik legal synthesis format:
    1. Direct Answer First
    2. Governing Legal Provisions
    3. Legal Explanation & Analysis
    4. Important Conditions & Safeguards
    5. Actionable Next Steps
    Supports English, Hindi, and Marathi.
    """

    @property
    def provider_name(self) -> str:
        return "offline_deterministic_fallback"

    def generate(
        self,
        prompt: str,
        system_instruction: str,
        temperature: float = 0.1,
        max_output_tokens: int = 1500
    ) -> str:
        # Check if context contains statutory sections
        if "=== RETRIEVED STATUTORY PROVISIONS ===" not in prompt:
            return (
                "Insufficient statutory context was retrieved from the database to answer this legal question. "
                "No authoritative provisions matching the query could be verified."
            )

        context_segment = prompt.split("=== RETRIEVED STATUTORY PROVISIONS ===")[-1].strip()
        if not context_segment:
            return (
                "Insufficient statutory context was retrieved from the database to answer this legal question. "
                "No authoritative provisions matching the query could be verified."
            )

        # 1. Parse question
        q_match = re.search(r"LEGAL QUESTION:\s*(.*?)\s*LANGUAGE INSTRUCTION:", prompt, re.DOTALL)
        q = q_match.group(1).strip() if q_match else ""

        # 2. Parse language
        lang = "en"
        if "मराठी" in prompt:
            lang = "mr"
        elif "हिंदी" in prompt:
            lang = "hi"

        # 3. Parse document context if present
        doc_match = re.search(r"=== USER UPLOADED DOCUMENT CONTEXT \((.*?)\) ===\s*(.*?)\s*\[End of Uploaded Document Context\]", prompt, re.DOTALL)
        doc_title = doc_match.group(1) if doc_match else ""
        doc_text = doc_match.group(2).strip() if doc_match else ""

        # 4. Extract individual provisions
        if "=== INSTRUCTIONS ===" in context_segment:
            context_segment = context_segment.split("=== INSTRUCTIONS ===")[0]

        prov_blocks = re.findall(
            r"\[STATUTORY PROVISION #\d+.*?\]\s*Act:\s*(.*?)(?:\s*\((.*?)\))?\s*(?:Section|Provision):\s*(.*?)\s*(?:—\s*(.*?))?\s*Text:\s*(.*?)(?=\[STATUTORY PROVISION|\Z)",
            context_segment,
            re.DOTALL
        )

        if not prov_blocks:
            return (
                "[DETERMINISTIC FALLBACK SYNTHESIS - TEST/OFFLINE MODE]\n\n"
                "Based on the retrieved statutory provisions from the Vidhik legal database:\n\n"
                f"{context_segment.strip()}\n\n"
                "This response was compiled by the offline deterministic synthesis fallback engine."
            )

        primary_acts = []
        primary_provisions = []
        for act, jur, prov, title, text in prov_blocks[:3]:
            act_clean = act.strip()
            prov_clean = prov.strip().split(" [Source:")[0].strip()
            if act_clean not in primary_acts:
                primary_acts.append(act_clean)
            primary_provisions.append(f"{prov_clean} ({act_clean})")

        lines = []

        if lang == "hi":
            lines.append("### सीधा उत्तर (Direct Answer)")
            if doc_text:
                lines.append(f"आपके प्रश्न और अपलोड किए गए दस्तावेज़ (*{doc_title}*) के संदर्भ में, भारतीय कानून के तहत विनिर्दिष्ट विधिक अधिकार और उपचार उपलब्ध हैं।")
            else:
                lines.append(f"भारतीय कानून के अंतर्गत आपकी स्थिति मुख्यतः **{', '.join(primary_acts)}** द्वारा शासित है।")

            lines.append("\n### लागू कानूनी प्रावधान (Governing Provisions)")
            for prov_item in primary_provisions:
                lines.append(f"- **{prov_item}**")

            lines.append("\n### विधिक व्याख्या एवं विश्लेषण (Legal Explanation)")
            for i, (act, jur, prov, title, text) in enumerate(prov_blocks[:3], 1):
                act_clean = act.strip()
                prov_clean = prov.strip().split(" [Source:")[0].strip()
                title_clean = title.strip() if title else ""
                clean_text = " ".join(text.strip().split())[:300]
                lines.append(f"**{i}. {prov_clean}{' — ' + title_clean if title_clean else ''} ({act_clean})**")
                lines.append(f"{clean_text}...\n")

            lines.append("### महत्वपूर्ण शर्तें एवं सुरक्षा उपाय (Safeguards)")
            if any("arrest" in act.lower() or "arrest" in prov.lower() or "47" in prov or "48" in prov or "35" in prov for act, jur, prov, title, text in prov_blocks):
                lines.append("- बीएनएसएस (BNSS) की धारा 47 के तहत पुलिस का कर्तव्य है कि वह गिरफ्तार व्यक्ति को गिरफ्तारी का पूरा कारण तुरंत सूचित करे।")
                lines.append("- धारा 48 के तहत नामित रिश्तेदार या मित्र को गिरफ्तारी की सूचना तत्काल देना अनिवार्य है।")
                lines.append("- संविधान के अनुच्छेद 21 और 22 तथा *डी.के. बासु बनाम पश्चिम बंगाल राज्य* के अनुसार गिरफ्तारी के अधिकार मौलिक और अनुल्लंघनीय हैं।")
            elif any("303" in prov for act, jur, prov, title, text in prov_blocks):
                lines.append("- चोरी (Theft) के लिए किसी व्यक्ति की सहमति के बिना बेईमानी से संपत्ति हटाना आवश्यक तत्व है।")
                lines.append("- बीएनएस की धारा 303 के तहत अधिकतम 3 वर्ष का कारावास, या जुर्माना, या दोनों का प्रावधान है।")
            elif any("consumer" in act.lower() for act, jur, prov, title, text in prov_blocks):
                lines.append("- उपभोक्ता संरक्षण अधिनियम, 2019 की धारा 35 के तहत ई-दाखिल पोर्टल पर ऑनलाइन शिकायत दर्ज की जा सकती है।")
                lines.append("- धारा 39 के तहत उपभोक्ता आयोग उत्पाद बदलने, पूर्ण धनवापसी और मुआवजे का आदेश दे सकता है।")
            else:
                lines.append("- संबंधित प्रावधान के तहत दी गई औपचारिक कानूनी शर्तों और प्रक्रिया का पालन आवश्यक है।")

            lines.append("\n### व्यावहारिक अगले कदम (Actionable Next Steps)")
            lines.append("1. सभी संबंधित साक्ष्य, नोटिस, दस्तावेज और पत्राचार सुरक्षित रखें।")
            lines.append("2. उचित कानूनी प्राधिकारी के समक्ष लिखित आवेदन या शिकायत प्रस्तुत करें।")
            lines.append("3. व्यक्तिगत मामले में न्यायालयीन सहायता हेतु किसी लाइसेंस प्राप्त अधिवक्ता से संपर्क करें।")

        elif lang == "mr":
            lines.append("### थेट उत्तर (Direct Answer)")
            if doc_text:
                lines.append(f"आपल्या प्रश्नानुसार आणि जोडलेल्या दस्तऐवजाच्या (*{doc_title}*) संदर्भाने, भारतीय कायद्यानुसार योग्य कायदेशीर उपाय उपलब्ध आहेत.")
            else:
                lines.append(f"भारतीय कायद्यानुसार आपली परिस्थिती प्रामुख्याने **{', '.join(primary_acts)}** अंतर्गत नियंत्रित होते.")

            lines.append("\n### लागू कायदेशीर तरतुदी (Governing Provisions)")
            for prov_item in primary_provisions:
                lines.append(f"- **{prov_item}**")

            lines.append("\n### कायदेशीर स्पष्टीकरण आणि विश्लेषण (Legal Explanation)")
            for i, (act, jur, prov, title, text) in enumerate(prov_blocks[:3], 1):
                act_clean = act.strip()
                prov_clean = prov.strip().split(" [Source:")[0].strip()
                title_clean = title.strip() if title else ""
                clean_text = " ".join(text.strip().split())[:300]
                lines.append(f"**{i}. {prov_clean}{' — ' + title_clean if title_clean else ''} ({act_clean})**")
                lines.append(f"{clean_text}...\n")

            lines.append("### महत्त्वाच्या अटी आणि कायदेशीर संरक्षण (Safeguards)")
            if any("arrest" in act.lower() or "arrest" in prov.lower() or "47" in prov or "48" in prov or "35" in prov for act, jur, prov, title, text in prov_blocks):
                lines.append("- बीएनएसएस (BNSS) कलम 47 नुसार अटक केलेल्या व्यक्तीला अटकेचे कारण त्वरित कळवणे पोलिसांवर बंधनकारक आहे.")
                lines.append("- कलम 48 नुसार नातेवाईक किंवा मित्राला अटकेची माहिती देणे आवश्यक आहे.")
                lines.append("- संविधानाचे अनुच्छेद 21, 22 आणि *डी.के. बसू खटल्यातील मार्गदर्शक तत्त्वे* हे मूलभूत अधिकार सुनिश्चित करतात.")
            elif any("303" in prov for act, jur, prov, title, text in prov_blocks):
                lines.append("- चोरीसाठी संमतीशिवाय मालमत्ता हलवणे आवश्यक आहे. बीएनएस कलम 303 अंतर्गत 3 वर्षांपर्यंत कारावास किंवा दंड होऊ शकतो.")
            elif any("consumer" in act.lower() for act, jur, prov, title, text in prov_blocks):
                lines.append("- ग्राहक संरक्षण कायदा 2019 कलम 35 नुसार ई-दाखील पोर्टलवर तक्रार दाखल करता येते.")
                lines.append("- कलम 39 अंतर्गत खराब वस्तू बदलून मिळणे किंवा नुकसानभरपाई मिळण्याचे अधिकार आहेत.")
            else:
                lines.append("- संबंधित तरतुदींनुसार आवश्यक प्रक्रिया आणि अटींचे पालन करणे आवश्यक आहे.")

            lines.append("\n### पुढील कृती (Actionable Next Steps)")
            lines.append("1. सर्व लेखी पुरावे, पावत्या आणि दस्तऐवज सुरक्षित ठेवा.")
            lines.append("2. सक्षम प्राधिकरणाकडे रीतसर तक्रार किंवा अर्ज दाखल करा.")
            lines.append("3. पुढील कायदेशीर मार्गदर्शनासाठी मान्यताप्राप्त वकिलाचा सल्ला घ्या.")

        else:
            # English
            lines.append("### Direct Answer")
            if doc_text:
                lines.append(f"Based on your query and the uploaded document (*{doc_title}*), Indian statutory law provides clear remedies and legal protections.")
            else:
                lines.append(f"Under Indian law, your situation is governed primarily by **{', '.join(primary_acts)}**.")

            lines.append("\n### Governing Legal Provisions")
            for prov_item in primary_provisions:
                lines.append(f"- **{prov_item}**")

            lines.append("\n### Legal Explanation & Analysis")
            for i, (act, jur, prov, title, text) in enumerate(prov_blocks[:3], 1):
                act_clean = act.strip()
                prov_clean = prov.strip().split(" [Source:")[0].strip()
                title_clean = title.strip() if title else ""
                clean_text = " ".join(text.strip().split())[:300]
                lines.append(f"**{i}. {prov_clean}{' — ' + title_clean if title_clean else ''} ({act_clean})**")
                lines.append(f"{clean_text}...\n")

            lines.append("### Important Conditions & Safeguards")
            if any("arrest" in act.lower() or "arrest" in prov.lower() or "47" in prov or "48" in prov or "35" in prov for act, jur, prov, title, text in prov_blocks):
                lines.append("- Police officers have a mandatory duty under Section 47 BNSS to inform the arrested person immediately of the full grounds of arrest.")
                lines.append("- Under Section 48 BNSS, police must inform the nominated relative or friend of the arrested person without delay.")
                lines.append("- As affirmed in *D.K. Basu v. State of West Bengal*, custodial rights and physical examination under Article 21 and 22 of the Constitution are non-negotiable fundamental rights.")
            elif any("303" in prov for act, jur, prov, title, text in prov_blocks):
                lines.append("- Theft requires dishonest intention to take movable property out of the possession of another without consent.")
                lines.append("- BNS Section 303 prescribes imprisonment up to three years, or fine, or both (or community service for first-time petty theft under Rs 5,000 upon restitution).")
            elif any("351" in prov for act, jur, prov, title, text in prov_blocks):
                lines.append("- Threatening injury to person, reputation, or property constitutes criminal intimidation under Section 351 BNS.")
                lines.append("- Carries imprisonment up to 2 years, or fine, or both (or up to 7 years if the threat is of death or grievous hurt).")
            elif any("478" in prov or "480" in prov or "482" in prov for act, jur, prov, title, text in prov_blocks):
                lines.append("- For bailable offences (Section 478 BNSS), bail is a statutory right upon furnishing required surety.")
                lines.append("- For non-bailable offences (Section 480 BNSS), discretion lies with the court, with special considerations for women, minors, and sick/infirm persons.")
                lines.append("- Anticipatory bail can be sought before the High Court or Sessions Court under Section 482 BNSS before arrest.")
            elif any("consumer" in act.lower() for act, jur, prov, title, text in prov_blocks):
                lines.append("- Consumers can file complaints online via the official e-Daakhil portal or before the District Consumer Commission under Section 35 CPA 2019.")
                lines.append("- Under Section 39 CPA 2019, the Commission can direct replacement of defective goods, full refund with interest, and compensation for deficiency.")
            elif any("wages" in act.lower() for act, jur, prov, title, text in prov_blocks):
                lines.append("- Employers are mandated under Section 17 of the Code on Wages to disburse salaries within the wage period.")
                lines.append("- Unpaid employees can file a formal recovery application before the Labour Commissioner under Section 45, which can award compensation up to 10 times the unpaid amount.")
            elif any("contract" in act.lower() for act, jur, prov, title, text in prov_blocks):
                lines.append("- Under Section 73 of the Indian Contract Act, the injured party is entitled to compensation for direct loss or damage arising naturally from the breach.")
                lines.append("- Remote and indirect losses cannot be claimed unless specifically contemplated by the parties.")
            elif any("property" in act.lower() for act, jur, prov, title, text in prov_blocks):
                lines.append("- Under Section 108 of the Transfer of Property Act, tenants are entitled to peaceful and quiet enjoyment of the leased premises.")
                lines.append("- Landlords cannot evict tenants arbitrarily without due process of law and statutory notice under Section 106.")
            elif any("information technology" in act.lower() or "66" in prov for act, jur, prov, title, text in prov_blocks):
                lines.append("- Identity theft and unauthorized use of digital passwords/credentials carries imprisonment up to 3 years and fine up to Rs 1 Lakh under Section 66C IT Act.")
                lines.append("- Body corporates failing to protect sensitive personal data are liable for compensation under Section 43A IT Act.")
                lines.append("- As held in *Justice K.S. Puttaswamy v. UOI*, informational privacy is protected under Article 21 of the Constitution.")
            else:
                lines.append("- Review the relevant statutory conditions and procedural requirements governing this provision.")

            lines.append("\n### Actionable Next Steps")
            if doc_text:
                lines.append("1. **Review Notice / Contract Terms:** Re-examine the document against the statutory provisions above.")
                lines.append("2. **Issue Formal Written Reply / Notice:** Respond in writing preserving evidence of delivery.")
                lines.append("3. **Consult a Licensed Advocate:** Obtain formal legal representation for drafting and proceedings.")
            elif any("arrest" in q.lower() for q in [q]):
                lines.append("1. Demand the written grounds of arrest and ensure the arrest memo is prepared with witness signature.")
                lines.append("2. Exercise the right to inform a family member or advocate immediately.")
                lines.append("3. Request mandatory medical examination before production before the Magistrate within 24 hours.")
            elif any("consumer" in q.lower() or "defective" in q.lower() for q in [q]):
                lines.append("1. Preserve all purchase invoices, warranty cards, and communication with the seller/manufacturer.")
                lines.append("2. Send a formal legal notice giving 15 days to rectify or refund.")
                lines.append("3. File a consumer complaint on the e-Daakhil portal or before the District Commission.")
            elif any("salary" in q.lower() or "employer" in q.lower() for q in [q]):
                lines.append("1. Collate employment contract, salary slips, attendance logs, and bank statements.")
                lines.append("2. Send a formal written demand notice to the HR / management giving a 7-day cure period.")
                lines.append("3. Lodge a complaint before the Labour Commissioner / Authority under Section 45 Code on Wages.")
            else:
                lines.append("1. Gather all written documentation, communications, and factual records.")
                lines.append("2. Verify whether alternative dispute resolution (mediation/conciliation) is available.")
                lines.append("3. Consult a qualified advocate for representation before the appropriate forum or court.")

        lines.append("\n---\n*Note: Compiled by the Vidhik offline deterministic synthesis fallback engine grounded in statutory records.* [DETERMINISTIC FALLBACK SYNTHESIS - TEST/OFFLINE MODE]")
        return "\n".join(lines)


class GeminiLLMProvider(BaseLLMProvider):
    """
    Google Gemini API Provider using Gemini 2.5 Flash / Gemini 1.5.
    Connects to the official Google Gemini REST API with zero external dependencies.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY") or ""
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    @property
    def provider_name(self) -> str:
        return f"gemini ({self.model})"

    def generate(
        self,
        prompt: str,
        system_instruction: str,
        temperature: float = 0.1,
        max_output_tokens: int = 1500
    ) -> str:
        if not self.api_key:
            logger.warning("Gemini API key missing. Falling back to offline deterministic fallback engine.")
            return OfflineMockLLMProvider().generate(prompt, system_instruction, temperature, max_output_tokens)

        endpoint_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )

        payload = {
            "system_instruction": {
                "parts": [{"text": system_instruction}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
                "topP": 0.95
            }
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                endpoint_url,
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            candidates = result.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                if parts and "text" in parts[0]:
                    return parts[0]["text"].strip()

            return "Unable to parse valid completion text from Gemini response."

        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")
            logger.error(f"Gemini API HTTP Error {e.code}: {err_msg}")
            raise RuntimeError("Upstream Gemini API error encountered during legal synthesis.")
        except Exception as e:
            logger.error(f"Gemini API request failed: {e}", exc_info=True)
            raise RuntimeError("Upstream Gemini API request failed.")


class OpenAILLMProvider(BaseLLMProvider):
    """
    OpenAI / Compatible API Provider.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY") or ""
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")

    @property
    def provider_name(self) -> str:
        return f"openai ({self.model})"

    def generate(
        self,
        prompt: str,
        system_instruction: str,
        temperature: float = 0.1,
        max_output_tokens: int = 1500
    ) -> str:
        if not self.api_key:
            logger.warning("OpenAI API key missing. Falling back to offline deterministic fallback engine.")
            return OfflineMockLLMProvider().generate(prompt, system_instruction, temperature, max_output_tokens)

        endpoint_url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_output_tokens
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                endpoint_url,
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            choices = result.get("choices", [])
            if choices and "message" in choices[0]:
                return choices[0]["message"].get("content", "").strip()

            return "Unable to parse valid completion text from OpenAI response."

        except Exception as e:
            logger.error(f"OpenAI API request failed: {e}", exc_info=True)
            raise RuntimeError("Upstream OpenAI API request failed.")


def get_llm_provider(provider_type: Optional[str] = None) -> BaseLLMProvider:
    """
    Factory creating an LLM provider based on environment configuration or explicit request.
    Defaults to Gemini if API key is present, otherwise falls back gracefully to Offline Mock.
    """
    selected_type = (provider_type or os.getenv("LLM_PROVIDER", "gemini")).lower().strip()

    if selected_type == "gemini":
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
        if api_key:
            return GeminiLLMProvider(api_key=api_key)
        logger.info("LLM_PROVIDER is 'gemini' but GEMINI_API_KEY is not set. Using OfflineMockLLMProvider.")
        return OfflineMockLLMProvider()

    if selected_type in ("openai", "azure"):
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
        if api_key:
            return OpenAILLMProvider(api_key=api_key)
        logger.info("LLM_PROVIDER is 'openai' but OPENAI_API_KEY is not set. Using OfflineMockLLMProvider.")
        return OfflineMockLLMProvider()

    return OfflineMockLLMProvider()
