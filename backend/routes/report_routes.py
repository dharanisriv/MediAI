"""Feature 1 - Medical Report Explainer."""
from flask import Blueprint, jsonify, request

from backend.config import Config
from backend.services import gemini_service, ocr_service, prompts
from backend.services.normalize import REPORT_SPEC, coerce
from backend.utils.errors import ValidationError
from backend.utils.file_utils import read_upload
from backend.utils.messages import DISCLAIMER
from backend.utils.rate_limit import rate_limited
from backend.utils.validators import clean_text, get_language

bp = Blueprint("report", __name__, url_prefix="/api/report")


@bp.post("/analyze")
@rate_limited
def analyze_report():
    # The browser sends a "multipart form": text fields + an optional file.
    language = get_language(request.form.get("language"))
    question = clean_text(request.form.get("question"), "Question", 500)
    pasted = clean_text(request.form.get("text"), "Report text", Config.MAX_REPORT_CHARS)
    upload = request.files.get("file")

    texts, warnings, methods = [], [], []
    if upload and upload.filename:
        data, ext = read_upload(upload)
        extracted = ocr_service.extract_text(data, ext)  # data is never saved to disk
        texts.append(extracted["text"])
        warnings += extracted["warnings"]
        methods.append(extracted["method"])
        del data
    if pasted:
        texts.append(pasted)
        methods.append("pasted-text")

    combined = "\n\n".join(t.strip() for t in texts if t and t.strip())
    if len(combined) < 20:
        raise ValidationError("No readable report text was found. Upload a clearer file or paste the report text.")
    if len(combined) > Config.MAX_REPORT_CHARS:
        combined = combined[: Config.MAX_REPORT_CHARS]
        warnings.append("The report was very long, so only the first part was analysed.")

    system, user = prompts.report_prompt(combined, question, language)
    result = coerce(gemini_service.generate_json(system, user), REPORT_SPEC)

    return jsonify({
        "ok": True,
        "language": language,
        "result": result,
        "extracted_text": combined,  # shown to the user so they can check for OCR mistakes
        "extraction_methods": methods,
        "warnings": warnings,
        "ai_generated": True,
        "disclaimer": DISCLAIMER[language],
    })
