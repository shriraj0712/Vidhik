import re
import time
from typing import Dict, Any, List, Optional
from app.schemas.element_verification import (
    ElementVerificationRequest,
    ElementVerificationResponse,
    ElementMatch
)


class ElementVerificationService:
    """
    Statutory Element Verification Service.
    Maps factual user statements to explicit statutory elements of Indian law (BNS / IT Act / NI Act),
    determining if the facts substantiate all legal prerequisites of an offence or claim.
    """

    STATUTORY_ELEMENTS_DB = {
        "theft": {
            "provision_name": "Theft",
            "act_name": "Bharatiya Nyaya Sanhita, 2023",
            "section_reference": "Section 303(2) BNS (formerly Section 378/379 IPC)",
            "elements": [
                {
                    "name": "Dishonest intention to take property",
                    "patterns": [r"\b(without permission|stole|dishonestly|stolen|took without asking|unauthorized taking)\b", r"\b(चोरी|विनापरवानगी|चोरून नेले)\b"],
                    "significance": "Mens rea: intention to cause wrongful gain or wrongful loss."
                },
                {
                    "name": "Movable property",
                    "patterns": [r"\b(phone|mobile|laptop|money|cash|vehicle|car|bike|gold|jewellery|wallet|bag|bicycle|gadget)\b", r"\b(फोन|लॅपटॉप|पैसे|दागिने|गाडी|पाकीट)\b"],
                    "significance": "The subject matter must be movable property."
                },
                {
                    "name": "Out of possession of another person",
                    "patterns": [r"\b(from my house|from my bag|from my pocket|from my desk|from my shop|from my possession|belonged to me)\b", r"\b(माझ्या घरातून|माझ्या बॅगेतून|माझ्या खिशातून|माझ्या दुकानातून)\b"],
                    "significance": "Property must be taken out of someone's possession."
                },
                {
                    "name": "Without that person's consent",
                    "patterns": [r"\b(without consent|without my knowledge|did not permit|never agreed|without asking me)\b", r"\b(संमतीशिवाय|माझ्या माहितीशिवाय|परवानगी न घेता)\b"],
                    "significance": "Taking must occur without the consent of the possessor."
                },
                {
                    "name": "Moving the property to effect taking",
                    "patterns": [r"\b(took away|fled with|ran away with|removed|carried away|disappeared with)\b", r"\b(घेऊन पळून गेला|काढून नेले|पळाला)\b"],
                    "significance": "Physical moving in order to effect such taking."
                }
            ]
        },
        "cheating": {
            "provision_name": "Cheating / Fraud",
            "act_name": "Bharatiya Nyaya Sanhita, 2023",
            "section_reference": "Section 318(4) BNS (formerly Section 420 IPC)",
            "elements": [
                {
                    "name": "Deception or false representation",
                    "patterns": [r"\b(lied|false promise|misrepresented|fake identity|promised high returns|misled|fraudulent claim)\b", r"\b(खोटे बोलले|खोटे आश्वासन|फसविले|बनावट ओळख)\b"],
                    "significance": "Accused must have practiced deception from the outset."
                },
                {
                    "name": "Dishonest inducement",
                    "patterns": [r"\b(induced me|convinced me to transfer|asked me to pay|pressured to send money|tricked into signing)\b", r"\b(पैसे देण्यास भाग पाडले|भुलवले|बँक ट्रान्सफर करायला लावले)\b"],
                    "significance": "Deception must induce the victim to act or deliver property."
                },
                {
                    "name": "Delivery of property or valuable security",
                    "patterns": [r"\b(paid amount|transferred money|sent ₹|paid advance|handed over goods|transferred funds)\b", r"\b(पैसे दिले|रक्कम पाठवली|अ‍ॅडव्हान्स दिला)\b"],
                    "significance": "Victim must deliver property or consent that person retain property."
                },
                {
                    "name": "Wrongful loss or damage caused",
                    "patterns": [r"\b(lost money|blocked my number|never delivered|no refund|defrauded of|financial loss)\b", r"\b(आर्थिक नुकसान|पैसे बुडाले|ब्लॉक केले|वस्तू दिली नाही)\b"],
                    "significance": "Loss in property, reputation, or body to the person deceived."
                }
            ]
        },
        "criminal_intimidation": {
            "provision_name": "Criminal Intimidation",
            "act_name": "Bharatiya Nyaya Sanhita, 2023",
            "section_reference": "Section 351 BNS (formerly Section 503/506 IPC)",
            "elements": [
                {
                    "name": "Threat of injury to person, reputation, or property",
                    "patterns": [r"\b(threatened to kill|threatened to beat|threatened to harm|threatened to ruin|threatened to destroy property)\b", r"\b(मारण्याची धमकी|नुकसान करण्याची धमकी|बदनामी करण्याची धमकी)\b"],
                    "significance": "Explicit or implicit threat causing injury to person, reputation, or property."
                },
                {
                    "name": "Intent to cause alarm or compel action",
                    "patterns": [r"\b(demanded money|ordered to withdraw case|forced to sign|caused severe fear|intimidated)\b", r"\b(केस मागे घेण्यास सांगितले|दहशत निर्माण केली|जबरदस्तीने सही घेतली)\b"],
                    "significance": "Intent to cause alarm or make the person do any act which they are not legally bound to do."
                }
            ]
        },
        "cheque_bounce": {
            "provision_name": "Dishonour of Cheque",
            "act_name": "Negotiable Instruments Act, 1881",
            "section_reference": "Section 138 NI Act",
            "elements": [
                {
                    "name": "Cheque drawn for discharge of legally enforceable debt",
                    "patterns": [r"\b(issued cheque|gave cheque for loan|cheque for goods|cheque payment for bill|towards debt|settlement)\b", r"\b(चेक दिला|धनादेश दिला|कर्जापोटी चेक|बिलापोटी चेक)\b"],
                    "significance": "Cheque must be issued for discharge of a legally enforceable debt or liability."
                },
                {
                    "name": "Presentation within validity period (3 months)",
                    "patterns": [r"\b(deposited in bank|presented cheque|submitted to bank|presented for clearing)\b", r"\b(बँकेत जमा केला|वटवण्यासाठी दिला)\b"],
                    "significance": "Presentation to the bank must occur within validity period."
                },
                {
                    "name": "Dishonour due to insufficient funds / exceeds arrangement",
                    "patterns": [r"\b(insufficient funds|cheque bounced|dishonoured|funds insufficient memo|return memo)\b", r"\b(चेक बाउंस झाला|खात्यात शिल्लक नाही|अनादरित झाला)\b"],
                    "significance": "Bank returns cheque unpaid due to insufficiency of funds."
                },
                {
                    "name": "Statutory legal demand notice within 30 days",
                    "patterns": [r"\b(sent legal notice|demanded payment within 15 days|30 days notice sent|advocate notice served)\b", r"\b(कायदेशीर नोटीस पाठवली|१५ दिवसांची नोटीस)\b"],
                    "significance": "Payee makes demand for payment by written notice within 30 days of receipt of memo."
                }
            ]
        },
        "cyber_fraud": {
            "provision_name": "Cheating by Personation Using Computer Resource",
            "act_name": "Information Technology Act, 2000",
            "section_reference": "Section 66D IT Act",
            "elements": [
                {
                    "name": "Use of communication device or computer resource",
                    "patterns": [r"\b(via whatsapp|through telegram|online link|fake website|phishing email|mobile app|sms link)\b", r"\b(व्हॉट्सअ‍ॅप|टेलिग्राम|वेबसाईट|अ‍ॅप|ईमेल लिंक)\b"],
                    "significance": "Digital medium or computer resource utilized to execute the act."
                },
                {
                    "name": "Cheating by personation",
                    "patterns": [r"\b(pretended to be bank manager|fake customer care|posed as army officer|fake electricity official|impersonated)\b", r"\b(बँक अधिकारी असल्याचे भासवले|खोटे कस्टमर केअर|तोतया अधिकारी)\b"],
                    "significance": "Deceptive impersonation of another entity or authority."
                },
                {
                    "name": "Wrongful gain or loss resulting from computer usage",
                    "patterns": [r"\b(debited money|account drained|financial fraud|lost funds via upi)\b", r"\b(पैसे कट झाले|खाते रिकामे झाले|यूपीआय द्वारे नुकसान)\b"],
                    "significance": "Fraudulent inducement causing financial or digital loss."
                }
            ]
        }
    }

    @classmethod
    def verify_elements(cls, request: ElementVerificationRequest) -> ElementVerificationResponse:
        start_time = time.time()
        facts_clean = request.facts.strip().lower()

        # Identify target provision
        target_key = "theft"
        if request.provision:
            prov_input = request.provision.strip().lower()
            for k in cls.STATUTORY_ELEMENTS_DB.keys():
                if k in prov_input:
                    target_key = k
                    break
        else:
            # Auto-infer based on facts
            for k in ["cheque_bounce", "cyber_fraud", "criminal_intimidation", "cheating", "theft"]:
                patterns_all = []
                for elem in cls.STATUTORY_ELEMENTS_DB[k]["elements"]:
                    patterns_all.extend(elem["patterns"])
                if any(re.search(p, facts_clean, re.IGNORECASE) for p in patterns_all):
                    target_key = k
                    break

        db_entry = cls.STATUTORY_ELEMENTS_DB[target_key]
        element_evaluations: List[ElementMatch] = []
        missing_elements: List[str] = []
        supported_count = 0

        for elem in db_entry["elements"]:
            matched_snippets = []
            for pattern in elem["patterns"]:
                matches = re.finditer(pattern, facts_clean, re.IGNORECASE)
                for m in matches:
                    matched_snippets.append(m.group(0))
            
            is_present = len(matched_snippets) > 0
            if is_present:
                supported_count += 1
            else:
                missing_elements.append(elem["name"])

            element_evaluations.append(ElementMatch(
                element_name=elem["name"],
                is_present=is_present,
                matched_facts=list(set(matched_snippets)),
                significance=elem["significance"]
            ))

        total_elements = len(db_entry["elements"])
        if len(facts_clean.split()) < 8:
            status = "insufficient_facts"
            analysis = "The provided narrative contains insufficient factual detail to perform statutory element evaluation."
        elif supported_count == total_elements:
            status = "supported"
            analysis = f"All {total_elements} statutory elements for {db_entry['provision_name']} have corresponding factual indications in the statement."
        elif supported_count > 0:
            status = "partially_supported"
            analysis = f"Facts substantiate {supported_count} out of {total_elements} required statutory elements. Crucial elements are missing: {', '.join(missing_elements)}."
        else:
            status = "not_supported"
            analysis = f"The provided facts do not contain clear evidence corresponding to the statutory elements of {db_entry['provision_name']}."

        return ElementVerificationResponse(
            provision_name=db_entry["provision_name"],
            act_name=db_entry["act_name"],
            section_reference=db_entry["section_reference"],
            verification_status=status,
            required_elements=[e["name"] for e in db_entry["elements"]],
            element_evaluations=element_evaluations,
            missing_elements=missing_elements,
            factual_analysis=analysis,
            metadata={"latency_ms": round((time.time() - start_time) * 1000, 2), "matched_element_count": supported_count}
        )
