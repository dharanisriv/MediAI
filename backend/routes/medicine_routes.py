"""Feature 3 - Medicine Information Lookup."""
import re

from flask import Blueprint, jsonify, request

from backend.services import medicine_service
from backend.utils.errors import ValidationError
from backend.utils.messages import DISCLAIMER
from backend.utils.rate_limit import rate_limited
from backend.utils.validators import clean_text, get_language

bp = Blueprint("medicines", __name__, url_prefix="/api/medicines")

# Letters (any language), digits, spaces and a few symbols that appear in medicine names.
_NAME_OK = re.compile(r"^[\w\s.,+/()%'\-]{2,80}$", re.UNICODE)


@bp.post("/search")
@rate_limited
def search_medicine():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValidationError("Invalid request. Please send the form data again.")
    language = get_language(body.get("language"))
    name = clean_text(body.get("name"), "Medicine name", 80, required=True)
    if not _NAME_OK.match(name):
        raise ValidationError("Please type only the medicine name (letters and numbers), for example: Paracetamol 500.")

    found = medicine_service.lookup(name, language)
    return jsonify({
        "ok": True, "language": language, "query": name,
        "result": found["result"], "source": found["source"],
        "ai_generated": True, "disclaimer": DISCLAIMER[language],
    })
