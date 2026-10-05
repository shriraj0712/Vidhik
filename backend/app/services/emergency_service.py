import re
import time
from typing import List, Dict, Any, Optional
from app.schemas.emergency import EmergencyEvaluationRequest, EmergencyEvaluationResponse, HelplineInfo


class EmergencyInterceptorService:
    """
    Centralized Emergency Detection and Interception Layer.
    Detects critical situations requiring immediate law enforcement, medical, child protection,
    or cyber financial helpline escalation.
    """

    VERIFIED_HELPLINES = {
        "all_emergency": HelplineInfo(name="National Emergency Response", number="112", description="Immediate Police, Fire, and Ambulance response across India"),
        "women": HelplineInfo(name="Women in Distress Helpline", number="1091", description="24x7 support for women facing violence or harassment"),
        "domestic_violence": HelplineInfo(name="National Commission for Women Helpline", number="7827170170", description="Dedicated domestic violence reporting line"),
        "child": HelplineInfo(name="Childline India", number="1098", description="24x7 emergency assistance for children in danger or distress"),
        "cyber_fraud": HelplineInfo(name="National Cyber Crime Helpline", number="1930", description="Golden-hour reporting for online financial fraud & account freezing"),
        "legal_aid": HelplineInfo(name="NALSA Legal Aid Helpline", number="15100", description="Toll-free free legal assistance for citizens in custody or indigent persons"),
    }

    EMERGENCY_RULES = [
        {
            "type": "physical_danger",
            "urgency": "critical",
            "patterns": [
                r"\b(someone is attacking|under attack|trying to kill|stab|shoot|armed with knife|break into my house|physically attacking|physically assaulted|life in danger|with weapons)\b",
                r"\b(हल्ला होत आहे|जीव धोक्यात|मारहाण सुरू आहे|हत्या करण्याचा प्रयत्न|घरात घुसले)\b",
                r"\b(हमला हो रहा है|जान खतरे में|मारने की कोशिश|घर में घुसे)\b"
            ],
            "helplines": ["all_emergency"],
            "actions": [
                "Call 112 immediately for emergency police dispatch.",
                "Move to a secure location with locked doors if safe to do so.",
                "Do not confront armed or violent individuals directly."
            ]
        },
        {
            "type": "domestic_violence",
            "urgency": "critical",
            "patterns": [
                r"\b(husband\s+is\s+beating|husband\s+beating|beating\s+me|in-laws\s+assaulting|domestic\s+violence\s+in\s+progress|locked\s+in\s+room\s+by\s+husband|threatened\s+with\s+death\s+by\s+spouse)\b",
                r"\b(पती मारहाण करत आहे|सासरचे लोक त्रास देत आहेत|घरात कोंडून ठेवले|जीवघेणी मारहाण)\b",
                r"\b(पति मार पीट रहा है|ससुराल वाले प्रताड़ित कर रहे हैं|कमरे में बंद कर दिया)\b"
            ],
            "helplines": ["women", "domestic_violence", "all_emergency"],
            "actions": [
                "Call 112 or Women Helpline 1091 immediately.",
                "Reach out to the nearest safe neighbor, relative, or Protection Officer.",
                "Preserve any photographic evidence or medical records of injuries once safe."
            ]
        },
        {
            "type": "child_endangerment",
            "urgency": "critical",
            "patterns": [
                r"\b(child is missing|child kidnapping|kidnapped child|child abuse in progress|minor beaten|child trafficking)\b",
                r"\b(मूल बेपत्ता|मुलाचे अपहरण|बाल शोषण|मुलावर अत्याचार)\b",
                r"\b(बच्चा गायब|बच्चे का अपहरण|बाल शोषण)\b"
            ],
            "helplines": ["child", "all_emergency"],
            "actions": [
                "Call Childline 1098 and Police 112 immediately.",
                "Keep recent photographs and identifying details of the child ready.",
                "Do not delay filing an immediate zero-FIR at the nearest police station."
            ]
        },
        {
            "type": "cyber_financial_fraud",
            "urgency": "high",
            "patterns": [
                r"\b(money just deducted|hacked just now|otp shared money lost|fraud transaction within 1 hour|bank balance emptied|fraud link clicked right now|cyber fraud right now)\b",
                r"\b(खात्यातून पैसे गेले|आत्ताच फसवणूक झाली|ओटीपी दिला आणि पैसे कापले|बँक खाते रिकामे झाले)\b",
                r"\b(पैसे कट गए|अभी फ्रॉड हुआ|ओटीपी शेयर किया पैसे कटे)\b"
            ],
            "helplines": ["cyber_fraud"],
            "actions": [
                "Dial 1930 immediately to report the transaction within the financial golden hour.",
                "Log in to your banking app or call your bank to freeze debit cards, UPI, and net banking access.",
                "File an official complaint at https://cybercrime.gov.in."
            ]
        },
        {
            "type": "imminent_arrest_custody",
            "urgency": "high",
            "patterns": [
                r"\b(police at door to arrest|illegal detention by police|arrested without warrant|in lockup without magistrate)\b",
                r"\b(पोलीस अटक करायला आले आहेत|बेकायदेशीर ताबा|विना वॉरंट अटक|पोलीस कोठडी)\b",
                r"\b(पुलिस गिरफ्तार करने आई है|अवैध हिरासत|बिना वारंट गिरफ्तारी)\b"
            ],
            "helplines": ["legal_aid", "all_emergency"],
            "actions": [
                "Demand to know the grounds of arrest and request an arrest memo under Section 47 BNSS / DK Basu guidelines.",
                "Inform a trusted family member or advocate immediately.",
                "Contact NALSA Free Legal Aid helpline 15100 if unable to afford counsel."
            ]
        }
    ]

    @classmethod
    def evaluate(cls, request: EmergencyEvaluationRequest) -> EmergencyEvaluationResponse:
        start_time = time.time()
        text = request.text.lower()

        for rule in cls.EMERGENCY_RULES:
            for pattern in rule["patterns"]:
                if re.search(pattern, text, re.IGNORECASE):
                    helpline_objects = [cls.VERIFIED_HELPLINES[h_key] for h_key in rule["helplines"] if h_key in cls.VERIFIED_HELPLINES]
                    
                    escalation_msg = (
                        f"CRITICAL ASSISTANCE REQUIRED: Your situation appears to involve an active {rule['type'].replace('_', ' ')}. "
                        f"Please contact emergency services ({', '.join([f'{h.name}: {h.number}' for h in helpline_objects])}) immediately."
                    )

                    return EmergencyEvaluationResponse(
                        is_emergency=True,
                        urgency_level=rule["urgency"],
                        emergency_type=rule["type"],
                        immediate_actions=rule["actions"],
                        verified_helplines=helpline_objects,
                        escalation_message=escalation_msg,
                        can_proceed_with_legal_assistance=False if rule["urgency"] == "critical" else True,
                        metadata={"latency_ms": round((time.time() - start_time) * 1000, 2), "matched_pattern": pattern}
                    )

        # No emergency detected
        return EmergencyEvaluationResponse(
            is_emergency=False,
            urgency_level="none",
            emergency_type=None,
            immediate_actions=[],
            verified_helplines=[],
            escalation_message=None,
            can_proceed_with_legal_assistance=True,
            metadata={"latency_ms": round((time.time() - start_time) * 1000, 2)}
        )
