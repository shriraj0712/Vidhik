import json
import re

with open('scripts/translations_cache.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

# Sort keys and separate mr and hi dictionaries
dict_mr = {}
dict_hi = {}

for k, v in cache.items():
    clean_k = re.sub(r'\s+', ' ', k).strip()
    if not clean_k:
        continue
    mr_val = v.get('mr', '').strip()
    hi_val = v.get('hi', '').strip()
    if mr_val:
        dict_mr[clean_k] = mr_val
    if hi_val:
        dict_hi[clean_k] = hi_val

# Also add special UI & status mappings
ADDITIONAL = {
    "Case Details": {"mr": "खटल्याचा तपशील", "hi": "मामले का विवरण"},
    "Legal Analysis": {"mr": "कायदेशीर विश्लेषण", "hi": "विधिक विश्लेषण"},
    "Risk Level": {"mr": "जोखीम पातळी", "hi": "जोखिम स्तर"},
    "Recommended Authority": {"mr": "शिफारस केलेले प्राधिकरण", "hi": "अनुशंसित प्राधिकरण"},
    "Upload Document": {"mr": "कागदपत्र अपलोड करा", "hi": "दस्तावेज़ अपलोड करें"},
    "Processing...": {"mr": "प्रक्रिया सुरू आहे...", "hi": "प्रक्रिया जारी है..."},
    "Case Status": {"mr": "खटल्याची स्थिती", "hi": "मामले की स्थिति"},
    "Critical Risk": {"mr": "गंभीर जोखीम", "hi": "गंभीर जोखिम"},
    "High Risk": {"mr": "उच्च जोखीम", "hi": "उच्च जोखिम"},
    "Medium Risk": {"mr": "मध्यम जोखीम", "hi": "मध्यम जोखिम"},
    "Low Risk": {"mr": "कमी जोखीम", "hi": "कम जोखिम"},
    "Informational": {"mr": "माहितीपर", "hi": "सूचनात्मक"},
    "Active": {"mr": "सक्रिय", "hi": "सक्रिय"},
    "Pending": {"mr": "प्रलंबित", "hi": "लंबित"},
    "Resolved": {"mr": "निकाली काढलेले", "hi": "निपटाया गया"},
    "Urgent": {"mr": "तातडीचे", "hi": "अत्यावश्यक"},
    "Closed": {"mr": "बंद", "hi": "बंद"},
    "In Progress": {"mr": "प्रगतीपथावर", "hi": "प्रगति पर"},
    "Draft": {"mr": "मसुदा", "hi": "प्रारूप"},
    "Verified": {"mr": "सत्यापित", "hi": "सत्यापित"},
    "Completed": {"mr": "पूर्ण", "hi": "पूर्ण"},
    "Upcoming": {"mr": "आगामी", "hi": "आगामी"},
    "Overdue": {"mr": "मुदत संपलेले", "hi": "विलंबित"},
    "Today": {"mr": "आज", "hi": "आज"},
    "Yesterday": {"mr": "काल", "hi": "कल"},
    "Tomorrow": {"mr": "उद्या", "hi": "कल"},
    "Days ago": {"mr": "दिवसांपूर्वी", "hi": "दिन पहले"},
    "Hours ago": {"mr": "तासांपूर्वी", "hi": "घंटे पहले"},
    "Just now": {"mr": "आत्ताच", "hi": "अभी"},
    "View Details": {"mr": "तपशील पहा", "hi": "विवरण देखें"},
    "Learn More": {"mr": "अधिक जाणून घ्या", "hi": "अधिक जानें"},
    "Take Action": {"mr": "कारवाई करा", "hi": "कार्रवाई करें"},
    "Proceed": {"mr": "पुढे जा", "hi": "आगे बढ़ें"},
    "Step 1": {"mr": "पायरी १", "hi": "चरण 1"},
    "Step 2": {"mr": "पायरी २", "hi": "चरण 2"},
    "Step 3": {"mr": "पायरी ३", "hi": "चरण 3"},
    "Step 4": {"mr": "पायरी ४", "hi": "चरण 4"},
    "Overview": {"mr": "आढावा", "hi": "अवलोकन"},
    "Details": {"mr": "तपशील", "hi": "विवरण"},
    "Description": {"mr": "वर्णन", "hi": "विवरण"},
    "Category": {"mr": "वर्ग / श्रेणी", "hi": "श्रेणी"},
    "Date": {"mr": "दिनांक", "hi": "दिनांक"},
    "Time": {"mr": "वेळ", "hi": "समय"},
    "Location": {"mr": "स्थान", "hi": "स्थान"},
    "Name": {"mr": "नाव", "hi": "नाम"},
    "Phone": {"mr": "फोन", "hi": "फ़ोन"},
    "Email": {"mr": "ईमेल", "hi": "ईमेल"},
    "Address": {"mr": "पत्ता", "hi": "पता"},
    "Actions": {"mr": "कृती", "hi": "कार्रवाई"},
    "Action Steps": {"mr": "कृती पायऱ्या", "hi": "कार्रवाई चरण"},
    "Immediate Action": {"mr": "तातडीची कारवाई", "hi": "त्वरित कार्रवाई"},
    "Next Hearing": {"mr": "पुढील सुनावणी", "hi": "अगली सुनवाई"},
    "Court": {"mr": "न्यायालय", "hi": "न्यायालय"},
    "Judge": {"mr": "न्यायाधीश", "hi": "न्यायाधीश"},
    "Filing Date": {"mr": "दाखल दिनांक", "hi": "दायर करने की तिथि"},
    "Petitioner": {"mr": "याचिकाकर्ता", "hi": "याचिकाकर्ता"},
    "Respondent": {"mr": "प्रतिवादी", "hi": "प्रतिवादी"},
    "Complainant": {"mr": "तक्रारदार", "hi": "शिकायतकर्ता"},
    "Accused": {"mr": "आरोपी", "hi": "अभियुक्त / आरोपी"},
    "Witnesses": {"mr": "साक्षीदार", "hi": "गवाह"},
    "Evidence": {"mr": "पुरावा", "hi": "साक्ष्य / सबूत"},
    "Police Station": {"mr": "पोलीस ठाणे", "hi": "पुलिस स्टेशन"},
    "FIR Number": {"mr": "एफआयआर क्रमांक", "hi": "प्राथमिकी संख्या"},
    "CNR Number": {"mr": "सीएनआर क्रमांक", "hi": "सीएनआर नंबर"},
    "Challan Number": {"mr": "चलन क्रमांक", "hi": "चालान नंबर"},
    "Fine Amount": {"mr": "दंड रक्कम", "hi": "जुर्माना राशि"},
    "Penalty": {"mr": "दंड", "hi": "जुर्माना / दंड"},
    "Impoundment Risk": {"mr": "जप्ती जोखीम", "hi": "जब्ती जोखिम"},
    "Applicable Sections": {"mr": "लागू कलमे", "hi": "लागू धाराएं"},
    "Applicable Statutes": {"mr": "लागू कायदे", "hi": "लागू कानून"},
    "Statutory Grounding": {"mr": "कायदेशीर आधार", "hi": "विधिक आधार"},
    "Recommended Resolution Tier": {"mr": "शिफारस केलेली निवारण श्रेणी", "hi": "अनुशंसित समाधान स्तर"},
    "Emergency Helplines": {"mr": "आपत्कालीन हेल्पलाइन", "hi": "आपातकालीन हेल्पलाइन"},
    "Helpline": {"mr": "हेल्पलाइन", "hi": "हेल्पलाइन"},
    "Official Filing Portals": {"mr": "अधिकृत दाखल पोर्टल", "hi": "आधिकारिक फाइलिंग पोर्टल"},
    "Procedure Checklist": {"mr": "कार्यपद्धती सूची", "hi": "प्रक्रिया चेकलिस्ट"},
    "Prerequisite Documents": {"mr": "आवश्यक कागदपत्रे", "hi": "आवश्यक दस्तावेज़"},
    "Document Inspection & Preview": {"mr": "कागदपत्र तपासणी व पूर्वावलोकन", "hi": "दस्तावेज़ निरीक्षण एवं पूर्वावलोकन"},
    "Legal Instrument": {"mr": "कायदेशीर दस्तऐवज", "hi": "विधिक दस्तावेज़"},
    "Book Advocate Consultation": {"mr": "वकील सल्लामसलत बुक करा", "hi": "अधिवक्ता परामर्श बुक करें"},
    "Request Consultation": {"mr": "सल्ला विनंती करा", "hi": "परामर्श का अनुरोध करें"},
    "Consultation Fee": {"mr": "सल्ला शुल्क", "hi": "परामर्श शुल्क"},
    "Experience": {"mr": "अनुभव", "hi": "अनुभव"},
    "Bar Registration": {"mr": "बार नोंदणी", "hi": "बार पंजीकरण"},
    "Contact": {"mr": "संपर्क", "hi": "संपर्क"},
    "Phone Consultation": {"mr": "दूरध्वनी सल्ला", "hi": "फोन परामर्श"},
    "In-Person Consultation": {"mr": "प्रत्यक्ष भेट सल्ला", "hi": "कार्यालय में परामर्श"},
    "Video Conference": {"mr": "व्हिडिओ कॉन्फरन्स", "hi": "वीडियो कॉन्फ्रेंस"},
    "Voice Transcript": {"mr": "व्हॉइस मजकूर", "hi": "ध्वनि प्रतिलेख"},
    "Speak": {"mr": "बोला", "hi": "बोलें"},
    "Listening...": {"mr": "ऐकत आहे...", "hi": "सुन रहा है..."},
    "Tap to speak in English, Hindi, or Marathi": {"mr": "मराठी, हिंदी किंवा इंग्रजीत बोलण्यासाठी टॅप करा", "hi": "हिंदी, अंग्रेजी या मराठी में बोलने के लिए टैप करें"},
    "Clear Chat": {"mr": "चॅट साफ करा", "hi": "चैट साफ़ करें"},
    "New Consultation": {"mr": "नवीन सल्ला", "hi": "नया परामर्श"},
    "Ask a legal question...": {"mr": "कायदेशीर प्रश्न विचारा...", "hi": "कानूनी प्रश्न पूछें..."},
    "Quick search cases, statutes, procedures...": {"mr": "खटले, कायदे, कार्यपद्धती त्वरित शोधा...", "hi": "मामले, धाराएं, प्रक्रियाएं खोजें..."},
    "No records found": {"mr": "कोणतीही नोंद आढळली नाही", "hi": "कोई रिकॉर्ड नहीं मिला"},
    "No active cases": {"mr": "सक्रिय खटले नाहीत", "hi": "कोई सक्रिय मामला नहीं"},
    "No notifications": {"mr": "कोणत्याही सूचना नाहीत", "hi": "कोई सूचना नहीं"},
    "You're all caught up": {"mr": "सर्व अद्ययावत आहे", "hi": "सब कुछ देखा जा चुका है"},
    "No new notifications at this time.": {"mr": "या वेळी कोणत्याही नवीन सूचना नाहीत.", "hi": "इस समय कोई नई सूचना नहीं है।"},
    "Mark All Read": {"mr": "सर्व वाचलेले चिन्हांकित करा", "hi": "सभी को पढ़ा हुआ चिह्नित करें"},
    "View All Notifications": {"mr": "सर्व सूचना पहा", "hi": "सभी सूचनाएं देखें"},
    "Upload Document": {"mr": "कागदपत्र अपलोड करा", "hi": "दस्तावेज़ अपलोड करें"},
    "Upload New Document": {"mr": "नवीन कागदपत्र अपलोड करा", "hi": "नया दस्तावेज़ अपलोड करें"},
    "Select File": {"mr": "फाइल निवडा", "hi": "फ़ाइल चुनें"},
    "Browse": {"mr": "ब्राउझ करा", "hi": "ब्राउज़ करें"},
    "Drag & drop files here": {"mr": "येथे फाइल ड्रॅग आणि ड्रॉप करा", "hi": "फ़ाइलें यहाँ खींचें और छोड़ें"},
    "Supported formats: PDF, PNG, JPG": {"mr": "समर्थित फॉरमॅट: PDF, PNG, JPG", "hi": "समर्थित प्रारूप: PDF, PNG, JPG"},
    "Extracted Text": {"mr": "काढलेला मजकूर", "hi": "निकाला गया पाठ"},
    "Identified Clauses": {"mr": "ओळखलेली कलमे व अटी", "hi": "पहचाने गए खंड"},
    "Potential Red Flags": {"mr": "संभाव्य धोके / जोखीम", "hi": "संभावित जोखिम बिंदु"},
    "Recommendations": {"mr": "शिफारसी", "hi": "सिफारिशें"},
    "Analysis Summary": {"mr": "विश्लेषण सारांश", "hi": "विश्लेषण सारांश"},
    "Save to Case": {"mr": "खटल्यामध्ये जतन करा", "hi": "मामले में सहेजें"},
    "Saved successfully": {"mr": "यशस्वीरित्या जतन केले", "hi": "सफलतापूर्वक सहेजा गया"},
    "Deleted successfully": {"mr": "यशस्वीरित्या हटवले", "hi": "सफलतापूर्वक हटाया गया"},
    "Updated successfully": {"mr": "यशस्वीरित्या अद्ययावत केले", "hi": "सफलतापूर्वक अपडेट किया गया"},
    "Error occurred": {"mr": "त्रुटी आली", "hi": "त्रुटि हुई"},
    "Please fill all required fields": {"mr": "कृपया सर्व आवश्यक माहिती भरा", "hi": "कृपया सभी आवश्यक फ़ील्ड भरें"},
    "Language switched to Marathi": {"mr": "भाषा मराठीमध्ये बदलली", "hi": "भाषा मराठी में बदली गई"},
    "Language switched to Hindi": {"mr": "भाषा हिंदीमध्ये बदलली", "hi": "भाषा हिंदी में बदली गई"},
    "Language switched to English": {"mr": "भाषा इंग्रजीमध्ये बदलली", "hi": "भाषा अंग्रेजी में बदली गई"},
    "Started new AI Legal Assistant conversation.": {"mr": "नवीन एआय विधी सहाय्यक संभाषण सुरू केले.", "hi": "नया एआई विधिक सहायक वार्तालाप शुरू किया।"},
    "Complaint draft generated successfully!": {"mr": "तक्रार मसुदा यशस्वीरित्या तयार केला!", "hi": "शिकायत प्रारूप सफलतापूर्वक तैयार किया गया!"},
    "Dispute evaluated successfully!": {"mr": "विवादाचे यशस्वीरित्या मूल्यांकन झाले!", "hi": "विवाद का सफलतापूर्वक मूल्यांकन किया गया!"},
    "Document analyzed successfully!": {"mr": "कागदपत्राचे यशस्वीरित्या विश्लेषण झाले!", "hi": "दस्तावेज़ का सफलतापूर्वक विश्लेषण किया गया!"},
    "Copied to clipboard": {"mr": "क्लिपबोर्डवर कॉपी केले", "hi": "क्लिपबोर्ड पर कॉपी किया गया"}
}

for k, v in ADDITIONAL.items():
    dict_mr[k] = v['mr']
    dict_hi[k] = v['hi']

print(f"Total Marathi entries: {len(dict_mr)}")
print(f"Total Hindi entries: {len(dict_hi)}")

mr_json = json.dumps(dict_mr, ensure_ascii=False, indent=2)
hi_json = json.dumps(dict_hi, ensure_ascii=False, indent=2)

js_content = f"""// ============================================================================
// VIDHIK AI — COMPLETE MULTI-LINGUAL LOCALIZATION ENGINE (i18n)
// Official Locales: en (English), hi (हिंदी), mr (मराठी)
// ============================================================================

(function () {{
  'use strict';

  const STORAGE_KEY = 'vidhik_lang';

  const DICT_MR = {mr_json};

  const DICT_HI = {hi_json};

  const LOWER_MR = {{}};
  for (const [k, v] of Object.entries(DICT_MR)) {{
    LOWER_MR[k.toLowerCase()] = v;
  }}

  const LOWER_HI = {{}};
  for (const [k, v] of Object.entries(DICT_HI)) {{
    LOWER_HI[k.toLowerCase()] = v;
  }}

  window.VidhikI18n = {{
    currentLang: localStorage.getItem(STORAGE_KEY) || 'en',
    dictMr: DICT_MR,
    dictHi: DICT_HI,
    lowerMr: LOWER_MR,
    lowerHi: LOWER_HI,

    t(text, lang = this.currentLang) {{
      if (!text || typeof text !== 'string') return text;
      if (lang === 'en') return text;

      const trimmed = text.trim();
      if (!trimmed) return text;

      const normalized = trimmed.replace(/\\s+/g, ' ');
      const dict = lang === 'mr' ? this.dictMr : this.dictHi;
      const lowerDict = lang === 'mr' ? this.lowerMr : this.lowerHi;

      // 1. Exact match
      if (dict[trimmed]) return dict[trimmed];
      if (dict[normalized]) return dict[normalized];

      // 2. Lowercase match
      const lower = normalized.toLowerCase();
      if (lowerDict[lower]) return lowerDict[lower];

      // 3. Leading icon/bullet/number extraction
      const iconMatch = text.match(/^([\\s\\p{{Emoji}}\\u2000-\\u3300\\uFE00-\\uFEFF\\+\\-\\*(•—→←✓✔⏳⚖🔍📝🏛📁📅📑📖🔬🎙📋🏠👥📊🛡✨🚗📜💡⚠️✅❌ℹ️🔔👤⚙️🔒🔓💬📌🏷📈📉📂📄📃🗂✉📞🌐▾▸▼▲\\d+\\.\\s*]+)(.*)$/u);
      if (iconMatch && iconMatch[2].trim()) {{
        const prefix = iconMatch[1];
        const rest = iconMatch[2].trim();
        const transRest = this.t(rest, lang);
        if (transRest !== rest) {{
          return prefix + transRest;
        }}
      }}

      // 4. Trailing badge/number extraction: e.g. "Cases (5)"
      const suffixMatch = text.match(/^(.*?)(\\s*[\\(\\[]\\d+[\\)\\]]|\\s*→|\\s*›|\\s*▾)$/);
      if (suffixMatch && suffixMatch[1].trim()) {{
        const main = suffixMatch[1].trim();
        const suffix = suffixMatch[2];
        const transMain = this.t(main, lang);
        if (transMain !== main) {{
          return transMain + suffix;
        }}
      }}

      // 5. Dynamic template/prefix replacements
      const patterns = lang === 'mr' ? [
        [/^Welcome back,\\s*(.*)$/i, 'पुन्हा स्वागत आहे, $1'],
        [/^Welcome to Vidhik AI,\\s*(.*)$/i, 'विधिक एआयमध्ये आपले स्वागत आहे, $1'],
        [/^Welcome,\\s*(.*)$/i, 'स्वागत आहे, $1'],
        [/^Case #(\\d+)/i, 'खटला #$1'],
        [/^Section\\s+(\\d+[A-Za-z]*)/i, 'कलम $1'],
        [/^Article\\s+(\\d+[A-Za-z]*)/i, 'अनुच्छेद $1'],
        [/^Theme:\\s*(.*?)\\s*Mode$/i, 'थीम: $1 मोड'],
        [/^Heard:\\s*\\\"(.*)\\\"$/i, 'ऐकले: "$1"'],
        [/^Could not switch case:\\s*(.*)$/i, 'खटला बदलता आला नाही: $1'],
        [/^Failed to re-analyze case:\\s*(.*)$/i, 'खटल्याचे पुन्हा विश्लेषण अयशस्वी: $1'],
        [/^Could not load.*:\\s*(.*)$/i, 'लोड करता आले नाही: $1'],
        [/^Reminder added to calendar for\\s*(.*)$/i, 'कॅलेंडरमध्ये स्मरणपत्र जोडले: $1'],
        [/^Chambers contact:\\s*(.*)$/i, 'कार्यालय संपर्क: $1'],
        [/^Consultation request submitted to\\s*(.*?)\\s*for\\s*(.*?)\\s*\\((.*?)\\)\\.\\s*(.*)$/i, 'सल्लामसलत विनंती $1 कडे $2 ($3) साठी सबमिट केली. $4'],
        [/^Linked\\s*(.*?)\\s*to current active matter\\s*\\(ID:\\s*(\\d+)\\)\\.$/i, '$1 ला चालू सक्रिय खटल्याशी जोडले (आयडी: $2).'],
        [/^(.*?)\\s*selected\\.\\s*You can assign this advocate when filing a new matter\\.$/i, '$1 निवडले. नवीन खटला दाखल करताना आपण या वकिलाची नियुक्ती करू शकता.'],
        [/^Checklist saved to Case #(\\d+)\\s*(.*)$/i, 'चेकलिस्ट केस #$1 मध्ये जतन केली $2'],
        [/^Analysis saved to Case #(\\d+)!?\\s*\\((.*)\\)$/i, 'विश्लेषण केस #$1 मध्ये जतन केले ($2)'],
        [/^Current Case switched to:\\s*(.*)$/i, 'सध्याचा खटला बदलला: $1'],
        [/^Size:\\s*([\\d\\.]+)\\s*KB\\s*•\\s*Checksum:\\s*(.*)$/i, 'आकार: $1 KB • चेकसम: $2'],
        [/^Error retrieving answer:\\s*(.*)$/i, 'उत्तर मिळवण्यात त्रुटी: $1'],
        [/^(\\d+)\\s*Years\\s*Courtroom\\s*Practice$/i, '$1 वर्षे न्यायालयीन सराव'],
        [/^(\\d+)\\+?\\s*Years$/i, '$1+ वर्षे'],
        [/^(\\d+)\\s*Grounded Provisions$/i, '$1 आधारभूत तरतुदी'],
        [/^Version\\s*([\\d\\.]+)$/i, 'आवृत्ती $1'],
        [/^([\\w\\s]+)\\s*Urgency$/i, (m, u) => `${{u.trim() === 'High' ? 'उच्च' : (u.trim() === 'Low' ? 'कमी' : 'मध्यम')}} निकड`],
        [/^Filed on:\\s*(.*)$/i, 'दाखल दिनांक: $1'],
        [/^Registered on:\\s*(.*)$/i, 'नोंदणी दिनांक: $1'],
        [/^Advocate:\\s*(.*)$/i, 'वकील: $1'],
        [/^Jurisdiction:\\s*(.*)$/i, 'अधिकारक्षेत्र: $1'],
        [/^Next Court Hearing:\\s*(.*)$/i, 'पुढील न्यायालयीन सुनावणी: $1'],
        [/^Purpose:\\s*(.*)$/i, 'उद्देश: $1']
      ] : [
        [/^Welcome back,\\s*(.*)$/i, 'वापसी पर स्वागत है, $1'],
        [/^Welcome to Vidhik AI,\\s*(.*)$/i, 'विधिक एआई में आपका स्वागत है, $1'],
        [/^Welcome,\\s*(.*)$/i, 'स्वागत है, $1'],
        [/^Case #(\\d+)/i, 'मामला #$1'],
        [/^Section\\s+(\\d+[A-Za-z]*)/i, 'धारा $1'],
        [/^Article\\s+(\\d+[A-Za-z]*)/i, 'अनुच्छेद $1'],
        [/^Theme:\\s*(.*?)\\s*Mode$/i, 'थीम: $1 मोड'],
        [/^Heard:\\s*\\\"(.*)\\\"$/i, 'सुना गया: "$1"'],
        [/^Could not switch case:\\s*(.*)$/i, 'मामला नहीं बदला जा सका: $1'],
        [/^Failed to re-analyze case:\\s*(.*)$/i, 'मामले का पुनः विश्लेषण विफल: $1'],
        [/^Could not load.*:\\s*(.*)$/i, 'लोड नहीं किया जा सका: $1'],
        [/^Reminder added to calendar for\\s*(.*)$/i, 'कैलेंडर में अनुस्मारक जोड़ा गया: $1'],
        [/^Chambers contact:\\s*(.*)$/i, 'कार्यालय संपर्क: $1'],
        [/^Consultation request submitted to\\s*(.*?)\\s*for\\s*(.*?)\\s*\\((.*?)\\)\\.\\s*(.*)$/i, 'परामर्श अनुरोध $1 को $2 ($3) के लिए प्रस्तुत किया गया। $4'],
        [/^Linked\\s*(.*?)\\s*to current active matter\\s*\\(ID:\\s*(\\d+)\\)\\.$/i, '$1 को वर्तमान सक्रिय मामले से जोड़ा गया (आईडी: $2)।'],
        [/^(.*?)\\s*selected\\.\\s*You can assign this advocate when filing a new matter\\.$/i, '$1 चुना गया। नया मामला दर्ज करते समय आप इस अधिवक्ता को सौंप सकते हैं।'],
        [/^Checklist saved to Case #(\\d+)\\s*(.*)$/i, 'चेकलिस्ट मामला #$1 में सहेजी गई $2'],
        [/^Analysis saved to Case #(\\d+)!?\\s*\\((.*)\\)$/i, 'विश्लेषण मामला #$1 में सहेजा गया ($2)'],
        [/^Current Case switched to:\\s*(.*)$/i, 'वर्तमान मामला बदला गया: $1'],
        [/^Size:\\s*([\\d\\.]+)\\s*KB\\s*•\\s*Checksum:\\s*(.*)$/i, 'आकार: $1 KB • चेकसम: $2'],
        [/^Error retrieving answer:\\s*(.*)$/i, 'उत्तर प्राप्त करने में त्रुटि: $1'],
        [/^(\\d+)\\s*Years\\s*Courtroom\\s*Practice$/i, '$1 वर्ष अदालती अभ्यास'],
        [/^(\\d+)\\+?\\s*Years$/i, '$1+ वर्ष'],
        [/^(\\d+)\\s*Grounded Provisions$/i, '$1 आधारभूत प्रावधान'],
        [/^Version\\s*([\\d\\.]+)$/i, 'संस्करण $1'],
        [/^([\\w\\s]+)\\s*Urgency$/i, (m, u) => `${{u.trim() === 'High' ? 'उच्च' : (u.trim() === 'Low' ? 'कम' : 'मध्यम')}} तात्कालिकता`],
        [/^Filed on:\\s*(.*)$/i, 'दायर दिनांक: $1'],
        [/^Registered on:\\s*(.*)$/i, 'पंजीकृत दिनांक: $1'],
        [/^Advocate:\\s*(.*)$/i, 'अधिवक्ता: $1'],
        [/^Jurisdiction:\\s*(.*)$/i, 'अधिकार क्षेत्र: $1'],
        [/^Next Court Hearing:\\s*(.*)$/i, 'अगली अदालत सुनवाई: $1'],
        [/^Purpose:\\s*(.*)$/i, 'उद्देश्य: $1']
      ];

      for (const [rgx, repl] of patterns) {{
        if (rgx.test(trimmed)) {{
          return trimmed.replace(rgx, repl);
        }}
      }}

      return text;
    }},

    translateNode(node, lang = this.currentLang) {{
      if (!node) return;

      if (node.nodeType === Node.ELEMENT_NODE) {{
        const tag = node.tagName.toLowerCase();
        if (['script', 'style', 'code', 'pre', 'svg', 'path'].includes(tag) || node.classList.contains('notranslate')) {{
          return;
        }}

        // Translate attributes
        if (node.hasAttribute('placeholder')) {{
          if (node._origPlaceholder === undefined) node._origPlaceholder = node.getAttribute('placeholder');
          node.setAttribute('placeholder', lang === 'en' ? node._origPlaceholder : this.t(node._origPlaceholder, lang));
        }}
        if (node.hasAttribute('title')) {{
          if (node._origTitle === undefined) node._origTitle = node.getAttribute('title');
          node.setAttribute('title', lang === 'en' ? node._origTitle : this.t(node._origTitle, lang));
        }}
        if (node.hasAttribute('aria-label')) {{
          if (node._origAriaLabel === undefined) node._origAriaLabel = node.getAttribute('aria-label');
          node.setAttribute('aria-label', lang === 'en' ? node._origAriaLabel : this.t(node._origAriaLabel, lang));
        }}
        if (tag === 'option') {{
          if (node._origText === undefined) node._origText = node.textContent;
          node.textContent = lang === 'en' ? node._origText : this.t(node._origText, lang);
        }}
        if (tag === 'input' && (node.type === 'button' || node.type === 'submit')) {{
          if (node._origValue === undefined) node._origValue = node.value;
          node.value = lang === 'en' ? node._origValue : this.t(node._origValue, lang);
        }}
      }} else if (node.nodeType === Node.TEXT_NODE) {{
        const val = node.nodeValue;
        if (!val || !val.trim()) return;

        const parent = node.parentElement;
        if (parent) {{
          const tag = parent.tagName.toLowerCase();
          if (['script', 'style', 'code', 'pre', 'svg', 'path'].includes(tag) || parent.classList.contains('notranslate')) {{
            return;
          }}
        }}

        if (node._origText === undefined) {{
          node._origText = val;
        }}

        if (lang === 'en') {{
          if (node.nodeValue !== node._origText) {{
            node.nodeValue = node._origText;
          }}
        }} else {{
          const trans = this.t(node._origText, lang);
          if (trans !== node._origText && node.nodeValue !== trans) {{
            node.nodeValue = trans;
          }}
        }}
      }}

      let child = node.firstChild;
      while (child) {{
        this.translateNode(child, lang);
        child = child.nextSibling;
      }}
    }},

    translateDom(root = document.body, lang = this.currentLang) {{
      if (!root) return;
      this.translateNode(root, lang);
      this.syncFormControls(lang);
    }},

    syncFormControls(lang = this.currentLang) {{
      const aiLang = document.getElementById('ai-chat-lang');
      if (aiLang && aiLang.value !== lang) aiLang.value = lang;

      const cgLang = document.getElementById('cg-language');
      if (cgLang && cgLang.value !== lang) cgLang.value = lang;

      const voiceLang = document.getElementById('voice-lang-select');
      if (voiceLang) {{
        const vCode = lang === 'hi' ? 'hi-IN' : (lang === 'mr' ? 'mr-IN' : 'en-IN');
        if (voiceLang.value !== vCode) voiceLang.value = vCode;
      }}
    }},

    setLanguage(lang) {{
      this.currentLang = lang;
      localStorage.setItem(STORAGE_KEY, lang);
      this.translateDom(document.body, lang);
    }},

    _observer: null,
    _observerDebounce: null,
    setupObserver() {{
      if (this._observer) return;
      const self = this;
      this._observer = new MutationObserver(mutations => {{
        if (self.currentLang === 'en') return;
        let needsTranslation = false;
        for (const m of mutations) {{
          if (m.addedNodes && m.addedNodes.length > 0) {{
            needsTranslation = true;
            break;
          }}
        }}
        if (needsTranslation) {{
          clearTimeout(self._observerDebounce);
          self._observerDebounce = setTimeout(() => {{
            self._observer.disconnect();
            self.translateDom(document.body, self.currentLang);
            self._observer.observe(document.body, {{ childList: true, subtree: true }});
          }}, 40);
        }}
      }});
      this._observer.observe(document.body, {{ childList: true, subtree: true }});
    }}
  }};

  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', () => {{
      window.VidhikI18n.translateDom(document.body, window.VidhikI18n.currentLang);
      window.VidhikI18n.setupObserver();
    }});
  }} else {{
    window.VidhikI18n.translateDom(document.body, window.VidhikI18n.currentLang);
    window.VidhikI18n.setupObserver();
  }}
}})();
"""

with open('backend/app/static/i18n.js', 'w', encoding='utf-8') as f:
    f.write(js_content)

print(f"Generated backend/app/static/i18n.js successfully! Length: {len(js_content)} bytes")
