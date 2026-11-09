"""Small endpoints used by every page: health check and the instant emergency check."""
from flask import Blueprint, jsonify, request

from backend.config import Config, get_api_key, get_model_candidates
from backend.services import ocr_service, safety_service
from backend.utils.messages import DISCLAIMER
from backend.utils.validators import clean_text, get_language

bp = Blueprint("common", __name__, url_prefix="/api")


@bp.get("/health")
def health():
    """Open http://127.0.0.1:5000/api/health to check that the server and your API key are set up."""
    return jsonify({
        "ok": True,
        "app": "MediAI",
        "gemini_key_configured": bool(get_api_key()),  # we only say yes/no, never show the key
        "models_in_order": get_model_candidates(),
        "tesseract_available": ocr_service.tesseract_available(),
        "ocr_engine": Config.OCR_ENGINE,
        "max_upload_mb": Config.MAX_UPLOAD_MB,
    })


@bp.post("/safety/check")
def safety_check():
    """
    Instant, rule-based emergency check (no AI, no waiting).
    The symptom page calls this while the user types so the warning can appear immediately.
    """
    data = request.get_json(silent=True) or {}
    language = get_language(data.get("language"))
    text = clean_text(data.get("text"), "Text", 5000)
    flags = safety_service.detect_red_flags(text)
    if flags:
        return jsonify({"ok": True, "emergency": safety_service.build_emergency_payload(flags, language)})
    return jsonify({"ok": True, "emergency": None, "disclaimer": DISCLAIMER[language]})
