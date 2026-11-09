"""Custom errors. Raising one of these anywhere becomes a clean JSON error for the website."""
from flask import jsonify, request
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge
import logging

from backend.config import Config

log = logging.getLogger("mediai")


class MediAIError(Exception):
    status = 400
    code = "error"

    def __init__(self, message: str, status: int = None):
        super().__init__(message)
        self.message = message
        if status:
            self.status = status


class ValidationError(MediAIError):
    """The user sent something we cannot accept (wrong file type, empty field...)."""
    status = 400
    code = "validation"


class AIServiceError(MediAIError):
    """Gemini failed (bad key, quota, timeout...)."""
    status = 502
    code = "ai_error"


class RateLimitError(MediAIError):
    status = 429
    code = "rate_limit"


def _json_error(message, status, code):
    return jsonify({"ok": False, "error": message, "code": code}), status


def register_error_handlers(app):
    @app.errorhandler(MediAIError)
    def handle_mediai_error(err):
        return _json_error(err.message, err.status, err.code)

    @app.errorhandler(RequestEntityTooLarge)
    def handle_too_large(_err):
        return _json_error(f"The file is too large. Maximum size is {Config.MAX_UPLOAD_MB} MB.", 413, "validation")

    @app.errorhandler(404)
    def handle_404(_err):
        if request.path.startswith("/api/"):
            return _json_error("This API address does not exist.", 404, "not_found")
        return (
            "<h1>Page not found</h1><p><a href='/'>Go to the MediAI home page</a></p>",
            404,
        )

    @app.errorhandler(405)
    def handle_405(_err):
        return _json_error("This request method is not allowed here.", 405, "method")

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        if isinstance(err, HTTPException):
            return _json_error(err.description or "Request error.", err.code or 500, "http")
        # Log the technical details in the terminal (never the user's medical text).
        log.exception("Unexpected server error")
        return _json_error("Something unexpected went wrong on the server. Please try again.", 500, "server")
