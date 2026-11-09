"""Feature 4 - Personalised Health Summary. Nothing is stored on the server."""
from flask import Blueprint, jsonify, request

from backend.services import gemini_service, prompts, safety_service
from backend.services.normalize import SUMMARY_SPEC, coerce
from backend.utils.errors import ValidationError
from backend.utils.messages import DISCLAIMER
from backend.utils.rate_limit import rate_limited
from backend.utils.validators import clean_age, clean_text, get_language

bp = Blueprint("summary", __name__, url_prefix="/api/summary")


@bp.post("/generate")
@rate_limited
def generate_summary():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValidationError("Invalid request. Please send the form data again.")

    language = get_language(body.get("language"))
    data = {
        "age": clean_age(body.get("age")),
        "history": clean_text(body.get("history"), "Medical history", 3000),
        "conditions": clean_text(body.get("conditions"), "Existing conditions", 3000),
        "medications": clean_text(body.get("medications"), "Current medications", 3000),
        "allergies": clean_text(body.get("allergies"), "Allergies", 1500),
        "symptoms": clean_text(body.get("symptoms"), "Symptoms", 3000),
        "report_findings": clean_text(body.get("report_findings"), "Report findings", 4000),
        "concerns": clean_text(body.get("concerns"), "Recent health concerns", 3000),
    }
    if not any(v not in (None, "") for v in data.values()):
        raise ValidationError("Please fill in at least one field to generate a summary.")

    # Rule-based emergency check on the text that describes CURRENT problems (not old history).
    flags = safety_service.detect_red_flags(". ".join([data["symptoms"], data["concerns"]]))
    emergency = safety_service.build_emergency_payload(flags, language) if flags else None

    system, user = prompts.summary_prompt(data, language)
    result = coerce(gemini_service.generate_json(system, user), SUMMARY_SPEC)

    return jsonify({
        "ok": True, "language": language, "result": result, "emergency": emergency,
        "ai_generated": True, "disclaimer": DISCLAIMER[language],
    })
