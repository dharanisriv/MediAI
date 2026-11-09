"""
Emergency red-flag detection - RULE BASED (no AI involved).

Why rules and not only AI?  An AI model can be slow, unavailable, or simply wrong.
These fixed rules run instantly on our own server, work even without a Gemini key,
and are deliberately CAUTIOUS: when in doubt, they show the warning.

Each red flag has:
  id        - short name used by the website
  label     - what the user sees, in 4 languages
  patterns  - regular expressions (English + Hindi/Telugu/Tamil + a few romanised words)

Limitations (also written in the README): keyword rules cannot understand every
spelling or sentence. They are a safety net, not a replacement for judgement.
"""
import re

from backend.utils.messages import EMERGENCY, SELF_HARM_EXTRA


def _p(*patterns):
    return [re.compile(p, re.IGNORECASE | re.UNICODE) for p in patterns]


RED_FLAGS = [
    {
        "id": "chest_pain",
        "label": {
            "en": "Chest pain, pressure or tightness",
            "hi": "सीने में दर्द, दबाव या जकड़न",
            "te": "ఛాతీలో నొప్పి, ఒత్తిడి లేదా బిగుతు",
            "ta": "நெஞ்சில் வலி, அழுத்தம் அல்லது இறுக்கம்",
        },
        "patterns": _p(
            r"\bchest\s+(pain|pains|pressure|tightness|heaviness|discomfort)\b",
            r"\b(pain|pressure|tightness|heaviness)\s+(in|on|across)\s+(my\s+|the\s+)?(chest|heart)\b",
            r"\bheart\s*attack\b",
            r"सीने\s+में\s+(\S+\s+)?(दर्द|दबाव|भारीपन)",
            r"छाती\s+में\s+(\S+\s+)?(दर्द|दबाव|भारीपन)",
            r"दिल\s+का\s+दौरा",
            r"\b(seene|chhati|chati)\s+mein\s+(\w+\s+)?(dard|dabav)\b",
            r"ఛాత[ిీ](లో)?\s+(\S+\s+)?(నొప్పి|బిగుతు|ఒత్తిడి)",
            r"గుండెపోటు",
            r"(நெஞ்சு|நெஞ்சில்|மார்பு|மார்பில்)\s+(\S+\s+)?(வலி|இறுக்கம்|அழுத்தம்)",
            r"மாரடைப்பு",
        ),
    },
    {
        "id": "breathing",
        "label": {
            "en": "Difficulty breathing or severe breathlessness",
            "hi": "सांस लेने में कठिनाई या बहुत ज़्यादा सांस फूलना",
            "te": "శ్వాస తీసుకోవడంలో ఇబ్బంది లేదా తీవ్రమైన ఆయాసం",
            "ta": "மூச்சு விடுவதில் சிரமம் அல்லது கடுமையான மூச்சுத் திணறல்",
        },
        "patterns": _p(
            r"\b(difficulty|trouble|struggling|difficult|hard)\s+(in\s+|with\s+|to\s+)?breath(e|ing)\b",
            r"\b(can['’]?t|cannot|can\s+not|unable\s+to|not\s+able\s+to)\s+(properly\s+|even\s+)?breathe\b",
            r"\bshort(ness)?\s+of\s+breath\b",
            r"\bbreathless(ness)?\b",
            r"\bgasping\b",
            r"\bout\s+of\s+breath\b",
            r"\b(blue|bluish)\s+(lips|face|fingers|skin)\b",
            r"\bchoking\b",
            r"सा[ंँ]स\s+(लेने\s+में\s+)?(\S+\s+)?(तकलीफ|दिक्कत|कठिनाई|परेशानी)",
            r"सा[ंँ]स\s+(नहीं\s+ले|फूल)",
            r"\bsans\s+(lene\s+mein\s+)?(takleef|dikkat)\b",
            r"(శ్వాస|ఊపిరి)[^.\n]{0,25}(ఇబ్బంది|ఆడ|కష్టం)",
            r"(மூச்சு|சுவாசிக்க)[^.\n]{0,25}(சிரம|கஷ்ட|திணறல்|முடிய)",
            r"மூச்சுத்\s*திணறல்",
        ),
    },
    {
        "id": "stroke",
        "label": {
            "en": "Sudden weakness or numbness on one side, face drooping or slurred speech",
            "hi": "शरीर के एक तरफ अचानक कमज़ोरी या सुन्नपन, चेहरा टेढ़ा होना या बोलने में लड़खड़ाहट",
            "te": "శరీరంలో ఒక వైపు అకస్మాత్తుగా బలహీనత లేదా మొద్దుబారడం, ముఖం వంకరపోవడం లేదా మాట తడబడటం",
            "ta": "உடலின் ஒரு பக்கம் திடீர் பலவீனம் அல்லது மரத்துப்போதல், முகம் கோணுதல் அல்லது பேச்சு குழறுதல்",
        },
        "patterns": _p(
            r"\b(weakness|numbness|paralysis|paralyzed|paralysed)\s+(on|in)\s+(one|the\s+left|the\s+right|my\s+left|my\s+right)\s+side\b",
            r"\bone[-\s]sided\s+(weakness|numbness)\b",
            r"\bone\s+side\s+of\s+(my\s+|the\s+)?(body|face)\b[^.\n]{0,40}(weak|numb|droop|paraly)",
            r"\b(face|facial|mouth)\s+(is\s+|are\s+|has\s+|feels?\s+|looks?\s+)?(droop(ing|y)?|sagging|uneven)\b",
            r"\bdrooping\s+(face|mouth)\b",
            r"\bsudden(ly)?\b[^.\n]{0,30}\b(numb(ness)?|weak(ness)?|paraly\w+)\b",
            r"\bslurred\s+speech\b",
            r"\b(can['’]?t|cannot|unable\s+to)\s+(speak|talk|move\s+(my\s+)?(arm|leg|face))\b",
            r"\b(having|had|signs\s+of)\s+(a\s+)?stroke\b",
            r"लकवा|पक्षाघात",
            r"एक\s+तरफ[^.\n]{0,25}(कमज़ोरी|कमजोरी|सुन्न)",
            r"चेहरा\s+टेढ",
            r"(बोलने|जुबान|ज़ुबान)[^.\n]{0,15}(लड़खड़|अटक)",
            r"పక్షవాతం",
            r"ఒక\s+(వైపు|పక్క)[^.\n]{0,30}(బలహీనత|మొద్దుబారి)",
            r"ముఖం\s+వంక",
            r"మాట\s+తడబ",
            r"பக்கவாதம்",
            r"ஒரு\s+பக்க[^.\n]{0,30}(பலவீனம்|மரத்து)",
            r"பேச்சு\s+குழறு|பேச்சு\s+குழறல்",
            r"முகம்\s+கோண",
        ),
    },
    {
        "id": "confusion",
        "label": {
            "en": "Sudden confusion or not responding normally",
            "hi": "अचानक भ्रम या सामान्य रूप से प्रतिक्रिया न देना",
            "te": "అకస్మాత్తుగా గందరగోళం లేదా సాధారణంగా స్పందించకపోవడం",
            "ta": "திடீர் குழப்பம் அல்லது இயல்பாக பதிலளிக்காமை",
        },
        "patterns": _p(
            r"\b(confus(ed|ion)|disorient(ed|ation)|delirious|incoherent|unresponsive)\b",
            r"\bnot\s+responding\b",
            r"\b(won['’]?t|will\s+not)\s+wake\s+up\b",
            r"अचानक[^.\n]{0,20}(भ्रम|भ्रमित)",
            r"भ्रमित",
            r"గందరగోళ",
            r"திடீர்\s+குழப்ப|குழப்பமாக\s+இருக்க",
        ),
    },
    {
        "id": "allergic",
        "label": {
            "en": "Severe allergic reaction (swelling of face, lips, tongue or throat)",
            "hi": "गंभीर एलर्जी प्रतिक्रिया (चेहरे, होंठ, जीभ या गले में सूजन)",
            "te": "తీవ్రమైన అలర్జీ ప్రతిచర్య (ముఖం, పెదవులు, నాలుక లేదా గొంతు వాపు)",
            "ta": "கடுமையான ஒவ்வாமை எதிர்வினை (முகம், உதடு, நாக்கு அல்லது தொண்டை வீக்கம்)",
        },
        "patterns": _p(
            r"\banaphyla(xis|ctic)\b",
            r"\b(swelling|swollen)\s+(of\s+|in\s+)?(my\s+|the\s+)?(face|lips|tongue|throat)\b",
            r"\b(face|lips|tongue|throat)\s+(is\s+|are\s+|feels?\s+)?(swelling|swollen)\b",
            r"\bthroat\s+(closing|tight(ness|ening)?)\b",
            r"\bsevere\s+allergic\b",
            r"\ballergic\s+reaction\b[^.\n]{0,40}(breath|swell|throat|faint)",
            r"एलर्जी[^.\n]{0,30}(सूजन|सांस|साँस)",
            r"(चेहरे|होंठ|होठ|गले|जीभ)\s+(पर\s+|में\s+)?(सूजन|सूज)",
            r"(ముఖం|పెదవులు|గొంతు|నాలుక)[^.\n]{0,15}వాపు",
            r"(முகம்|உதடு|தொண்டை|நாக்கு)[^.\n]{0,15}வீக்கம்",
        ),
    },
    {
        "id": "bleeding",
        "label": {
            "en": "Heavy or uncontrolled bleeding",
            "hi": "बहुत ज़्यादा या न रुकने वाला रक्तस्राव",
            "te": "అధిక లేదా ఆగని రక్తస్రావం",
            "ta": "அதிகமான அல்லது நிற்காத இரத்தப்போக்கு",
        },
        "patterns": _p(
            r"\b(heavy|severe|profuse|uncontrolled|uncontrollable|continuous|excessive)\s+(bleeding|blood\s+loss)\b",
            r"\bbleeding\b[^.\n]{0,30}(won['’]?t\s+stop|not\s+stopping|can['’]?t\s+(be\s+)?stop|soaking)",
            r"\bsoaking\s+(through\s+)?(a\s+|the\s+)?(pad|towel|cloth|bandage)",
            r"\bcoughing\s+(up\s+)?blood\b",
            r"खून\s+(बह|निकल|नहीं\s+रुक)",
            r"रक्तस्राव|रक्त\s*स्राव",
            r"రక్తస్రావం",
            r"రక్తం\s+(కారడం|ఆగడం\s+లేదు|ఆగట్లేదు)",
            r"(இ)?ரத்தப்?\s*போக்கு",
            r"(இ)?ரத்தம்\s+(நிற்க|கொட்டு)",
        ),
    },
    {
        "id": "unconscious",
        "label": {
            "en": "Fainting or loss of consciousness",
            "hi": "बेहोशी या होश खोना",
            "te": "స్పృహ కోల్పోవడం",
            "ta": "மயங்கி விழுதல் அல்லது சுயநினைவு இழப்பு",
        },
        "patterns": _p(
            r"\b(lost|loss\s+of|losing)\s+consciousness\b",
            r"\b(passed\s+out|passing\s+out|blacked\s+out|fainted|fainting|collapsed|unconscious)\b",
            r"बेहोश",
            r"होश\s+खो",
            r"స్పృహ\s+(కోల్పో|తప్ప|లేదు)",
            r"மயங்கி",
            r"சுயநினைவு\s+(இழ|இல்லை)",
        ),
    },
    {
        "id": "seizure",
        "label": {
            "en": "Seizure or convulsions (fits)",
            "hi": "दौरे या झटके पड़ना",
            "te": "మూర్ఛ లేదా ఫిట్స్",
            "ta": "வலிப்பு",
        },
        "patterns": _p(
            r"\b(seizure|seizures|convulsion|convulsions|convulsing)\b",
            r"\bhaving\s+(a\s+)?fits?\b",
            r"दौरा\s+(पड़|आ)|दौरे\s+(पड़|आ)|झटके\s+(आ|लग)|मिर्गी",
            r"మూర్ఛ|మూర్చ|ఫిట్స్",
            r"வலிப்பு",
        ),
    },
    {
        "id": "self_harm",
        "label": {
            "en": "Thoughts of suicide or self-harm",
            "hi": "आत्महत्या या खुद को नुकसान पहुँचाने के विचार",
            "te": "ఆత్మహత్య లేదా స్వీయ హాని ఆలోచనలు",
            "ta": "தற்கொலை அல்லது தன்னைத்தானே காயப்படுத்தும் எண்ணங்கள்",
        },
        "patterns": _p(
            r"\b(suicid(e|al)|kill\s+myself|end\s+my\s+life|want\s+to\s+die|take\s+my\s+own\s+life|better\s+off\s+dead)\b",
            r"\b(self[-\s]?harm|hurt\s+myself|harm\s+myself|cut\s+myself)\b",
            r"आत्महत्या|खुदकुशी|खुद\s*कुशी|मरना\s+चाह",
            r"\b(atmahatya|marna\s+chah)\w*",
            r"ఆత్మహత్య|చనిపోవాలని|చావాలని",
            r"தற்கொலை|சாக\s+வேண்டும்",
        ),
    },
    {
        "id": "poisoning",
        "label": {
            "en": "Suspected poisoning, overdose or snake bite",
            "hi": "ज़हर, दवा की अधिक मात्रा या सांप के काटने का संदेह",
            "te": "విషం, మందు అధిక మోతాదు లేదా పాము కాటు అనుమానం",
            "ta": "விஷம், மருந்து அதிக அளவு அல்லது பாம்புக்கடி சந்தேகம்",
        },
        "patterns": _p(
            r"\b(overdos(e|ed|ing)|poison(ed|ing))\b",
            r"\b(swallowed|drank|ate)\s+(poison|bleach|pesticide|kerosene|acid)\b",
            r"\btook\s+too\s+many\s+(pills|tablets|medicines?|capsules)\b",
            r"\bsnake\s*bite\b|\bbitten\s+by\s+a?\s*snake\b",
            r"ज़हर|जहर|ओवरडोज़|ओवरडोज|सांप\s+(ने\s+)?काट|साँप\s+(ने\s+)?काट",
            r"విషం|పాము\s+కాటు|పాము\s+కరిచ|అధిక\s+మోతాదు",
            r"விஷம்|பாம்பு\s+(கடி|கடித்த)|அதிக\s+அளவு\s+மருந்து",
        ),
    },
    {
        "id": "gi_bleeding",
        "label": {
            "en": "Vomiting blood or black / bloody stools",
            "hi": "खून की उल्टी या काला / खूनी मल",
            "te": "రక్తం వాంతులు లేదా నల్లటి / రక్తంతో కూడిన మలం",
            "ta": "இரத்த வாந்தி அல்லது கருப்பு / இரத்தம் கலந்த மலம்",
        },
        "patterns": _p(
            r"\b(vomit(ing|ed)?|throwing\s+up)\s+(up\s+)?(blood|coffee[-\s]ground)",
            r"\b(black|tarry)\s+(stool|stools|poop|motions?)\b",
            r"\bblood\s+in\s+(my\s+)?(stool|stools|vomit|poop)\b",
            r"\bbloody\s+(stool|stools|vomit|poop)\b",
            r"खून\s+की\s+उल्टी|उल्टी\s+(में\s+)?खून|काला\s+(मल|पखाना)|मल\s+में\s+खून",
            r"రక్తం\s+వాంతి|వాంతిలో\s+రక్తం|నల్లటి\s+మలం|మలంలో\s+రక్తం",
            r"(இ)?ரத்த\s*வாந்தி|வாந்தியில்\s+(இ)?ரத்தம்|கருப்பு\s+(நிற\s+)?மலம்|மலத்தில்\s+(இ)?ரத்தம்",
        ),
    },
    {
        "id": "severe_headache",
        "label": {
            "en": "Sudden, severe 'worst-ever' headache, or fever with a stiff neck",
            "hi": "अचानक बहुत तेज़ सिरदर्द ('ज़िंदगी का सबसे बुरा') या बुखार के साथ गर्दन में अकड़न",
            "te": "అకస్మాత్తుగా తీవ్రమైన తలనొప్పి ('జీవితంలో అత్యంత తీవ్రమైనది') లేదా జ్వరంతో మెడ బిగుసుకుపోవడం",
            "ta": "திடீரென கடுமையான தலைவலி ('வாழ்க்கையில் மிக மோசமானது') அல்லது காய்ச்சலுடன் கழுத்து இறுக்கம்",
        },
        "patterns": _p(
            r"\bworst\s+headache\b",
            r"\bthunderclap\b",
            r"\bsudden(ly)?\b[^.\n]{0,30}\b(severe|worst|terrible|excruciating)\b[^.\n]{0,20}\bheadache\b",
            r"\bheadache\b[^.\n]{0,40}\b(worst|thunderclap)\b",
            r"\bstiff\s+neck\b[^.\n]{0,40}\bfever\b|\bfever\b[^.\n]{0,40}\bstiff\s+neck\b",
            r"अचानक[^.\n]{0,25}सिर\s*दर्द",
            r"అకస్మాత్తుగా[^.\n]{0,25}తలనొప్పి",
            r"திடீர்[^.\n]{0,25}தலைவலி",
        ),
    },
]

_FLAGS_BY_ID = {f["id"]: f for f in RED_FLAGS}

# Words like "no chest pain" or "without breathlessness" cancel an ENGLISH match.
# We only look one word back, so "no fever but chest pain" still triggers the warning.
_NEGATION = re.compile(
    r"\b(no|not|without|never|denies|denied|nor|free\s+of|negative\s+for)\b(?:\W+\w+){0,1}\W*$",
    re.IGNORECASE,
)


def _is_negated(text: str, match_start: int) -> bool:
    before = text[max(0, match_start - 30):match_start]
    return bool(_NEGATION.search(before))


def _flag_matches(flag: dict, text: str) -> bool:
    for pattern in flag["patterns"]:
        for match in pattern.finditer(text):
            if not _is_negated(text, match.start()):
                return True
    return False


def detect_red_flags(text: str) -> list:
    """Return the list of red flags found in free text (any of the 4 languages)."""
    if not text or not text.strip():
        return []
    return [flag for flag in RED_FLAGS if _flag_matches(flag, text)]


def detect_from_form(area: str, severity: str, symptoms: list, description: str) -> list:
    """Check the symptom-checker form: selected symptoms + typed description + a severity rule."""
    text = ". ".join([*symptoms, description])
    flags = detect_red_flags(text)
    # Extra rule: SEVERE problem in the chest area is always treated as a red flag.
    if area == "chest" and severity == "severe" and _FLAGS_BY_ID["chest_pain"] not in flags:
        flags.append(_FLAGS_BY_ID["chest_pain"])
    return flags


def build_emergency_payload(flags: list, language: str, ai_reason: str = "") -> dict:
    """Create the data the website needs to show the big red emergency banner."""
    texts = EMERGENCY[language]
    extra = []
    if any(f["id"] == "self_harm" for f in flags):
        extra.append(SELF_HARM_EXTRA[language])
    return {
        "emergency": True,
        "title": texts["title"],
        "message": texts["message"],
        "actions": texts["actions"],
        "call_label": texts["call"],
        "emergency_number": "112",
        "flags": [{"id": f["id"], "label": f["label"][language]} for f in flags],
        "extra": extra,
        "source": "rules" if flags else "ai",
        "ai_reason": ai_reason,
    }
