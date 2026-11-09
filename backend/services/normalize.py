"""
Gemini usually follows our JSON schema, but not always. `coerce` forces the answer into the
exact shape the website expects (right types, no missing keys) so the page never breaks.

Spec language:  "str" | "list" | "bool" | ("enum", {allowed...}, default) | ("objects", {sub-spec}, max_items) | {nested spec}
"""


def _to_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "\n".join(str(v).strip() for v in value if str(v).strip())
    return str(value).strip()


def coerce(data, spec: dict) -> dict:
    data = data if isinstance(data, dict) else {}
    out = {}
    for key, kind in spec.items():
        value = data.get(key)
        if kind == "str":
            out[key] = _to_str(value)
        elif kind == "list":
            if isinstance(value, list):
                out[key] = [_to_str(v) for v in value if _to_str(v)]
            else:
                out[key] = [_to_str(value)] if _to_str(value) else []
        elif kind == "bool":
            out[key] = value is True or str(value).strip().lower() == "true"
        elif isinstance(kind, tuple) and kind[0] == "enum":
            text = _to_str(value).lower()
            out[key] = text if text in kind[1] else kind[2]
        elif isinstance(kind, tuple) and kind[0] == "objects":
            items = value if isinstance(value, list) else []
            out[key] = [coerce(i, kind[1]) for i in items[: kind[2]] if isinstance(i, dict)]
        elif isinstance(kind, dict):
            out[key] = coerce(value, kind)
    return out


REPORT_SPEC = {
    "report_type": "str",
    "plain_summary": "str",
    "lab_values": ("objects", {
        "test": "str", "purpose": "str", "value": "str", "unit": "str", "reference_range": "str",
        "flag": ("enum", {"high", "low", "normal", "abnormal_other", "not_determined"}, "not_determined"),
        "meaning": "str",
    }, 60),
    "medical_terms": ("objects", {"term": "str", "explanation": "str"}, 25),
    "key_findings": "list",
    "what_it_may_generally_indicate": "list",
    "answer_to_user_question": "str",
    "questions_for_doctor": "list",
    "readability_note": "str",
}

SYMPTOM_SPEC = {
    "symptom_summary": "str",
    "possible_explanations": ("objects", {"name": "str", "why_it_may_fit": "str"}, 6),
    "self_care": "list",
    "when_to_see_doctor": {
        "urgency": ("enum", {"self_care_ok", "see_doctor_soon", "see_doctor_within_24_hours", "urgent_care_today"}, "see_doctor_soon"),
        "urgency_label": "str",
        "reasoning": "str",
        "warning_signs_to_watch": "list",
    },
    "questions_for_doctor": "list",
    "emergency_suspected": "bool",
    "emergency_reason": "str",
}

MEDICINE_SPEC = {
    "identified": "bool", "needs_more_info": "bool", "clarification_message": "str",
    "medicine_name": "str", "generic_name": "str", "drug_class": "str",
    "common_uses": "list", "how_it_works": "str", "common_side_effects": "list",
    "serious_side_effects_seek_help": "list", "important_warnings": "list",
    "potential_interactions": "list", "storage": "str", "questions_for_pharmacist_or_doctor": "list",
}

SUMMARY_SPEC = {
    "basic_information": "str", "medical_history": "str", "medications_and_allergies": "str",
    "symptoms_summary": "str", "report_findings_summary": "str",
    "important_concerns": "list", "questions_for_professional": "list", "missing_information_note": "str",
}
