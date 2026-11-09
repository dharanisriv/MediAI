"""
Central settings for MediAI.

All secrets and options come from ENVIRONMENT VARIABLES:
  * on your PC they are read from the .env file,
  * in Google Colab we copy them from Colab Secrets into os.environ,
  * on a hosting website you type them into the dashboard.
Nothing secret is ever written in the code or sent to the browser.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")  # does nothing if there is no .env file


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    FRONTEND_DIR = BASE_DIR / "frontend"

    # ---- upload limits -------------------------------------------------
    MAX_UPLOAD_MB = _int_env("MAX_UPLOAD_MB", 8)
    # Flask refuses any request bigger than this (HTTP 413) before our code even runs.
    MAX_CONTENT_LENGTH = (MAX_UPLOAD_MB + 1) * 1024 * 1024
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "pdf", "txt"}
    MAX_PDF_PAGES = 15
    MAX_REPORT_CHARS = 30000  # text sent to the AI is cut at this length

    # ---- misc ----------------------------------------------------------
    RATE_LIMIT_PER_MINUTE = _int_env("RATE_LIMIT_PER_MINUTE", 20)
    OCR_ENGINE = os.getenv("OCR_ENGINE", "auto").lower()  # auto | gemini | tesseract


# The functions below read the environment at the moment they are called, so
# changing a key in Colab (or restarting with a new .env) works without re-importing.
def get_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "").strip()


def get_timeout_seconds() -> int:
    return _int_env("GEMINI_TIMEOUT_SECONDS", 60)


def get_model_candidates() -> list:
    """Main model first, then fallbacks (used automatically if a model is retired)."""
    main = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
    fallbacks = os.getenv("GEMINI_FALLBACK_MODELS", "gemini-2.5-flash-lite,gemini-flash-latest")
    names = [main] + [m.strip() for m in fallbacks.split(",")]
    unique = []
    for name in names:
        if name and name not in unique:
            unique.append(name)
    return unique
