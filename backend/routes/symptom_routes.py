"""Feature 2 - Symptom Checker (with the emergency rules checked FIRST)."""
from flask import Blueprint, jsonify, request

from backend.services import gemini_service, prompts, safety_service
from backend.services.normalize import SYMPTOM_SPEC, coerce
from backend.utils.errors import ValidationError
from backend.utils.messages import DISCLAIMER
from backend.utils.rate_limit import rate_limited
from backend.utils.validators import (BODY_AREAS, SEVERITIES, choice, clean_age,
                                      clean_list, clean_text, get_language)

bp = Blueprint("symptoms", __name__, url_prefix="/api/symptoms")


@bp.post("/analyze")
@rate_limited
def analyze_symptoms():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValidationError("Invalid request. Please send the form data again.")

    language = get_language(body.get("language"))
    data = {
        "area": choice(body.get("area"), "body area", BODY_AREAS, "general"),
        "symptoms": clean_list(body.get("symptoms"), "Symptoms", 25, 120),
        "description": clean_text(body.get("description"), "Description", 2000),
        "duration": clean_text(body.get("duration"), "Duration", 100),
        "severity": choice(body.get("severity"), "severity", SEVERITIES, "moderate"),
        "age": clean_age(body.get("age")),
        "history": clean_text(body.get("history"), "Medical history", 1500),
    }
    if not data["symptoms"] and not data["description"]:
        raise ValidationError("Choose at least one symptom or describe how you feel.")

    # 1) RULES FIRST - instant, no AI. If a red flag is found we stop here and show the emergency warning.
    flags = safety_service.detect_from_form(data["area"], data["severity"], data["symptoms"], data["description"])
    if flags:
        return jsonify({
            "ok": True, "language": language, "result": None,
            "emergency": safety_service.build_emergency_payload(flags, language),
            "disclaimer": DISCLAIMER[language],
        })

    # 2) Otherwise ask the AI (it can ALSO raise the emergency flag).
    system, user = prompts.symptom_prompt(data, language)
    result = coerce(gemini_service.generate_json(system, user), SYMPTOM_SPEC)

    if result["emergency_suspected"]:
        return jsonify({
            "ok": True, "language": language, "result": None,
            "emergency": safety_service.build_emergency_payload([], language, ai_reason=result["emergency_reason"]),
            "disclaimer": DISCLAIMER[language],
        })

    return jsonify({
        "ok": True, "language": language, "result": result, "emergency": None,
        "ai_generated": True, "disclaimer": DISCLAIMER[language],
    })
