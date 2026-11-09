"""Small helpers that check and clean everything that comes from the browser."""
from backend.utils.errors import ValidationError

SUPPORTED_LANGUAGES = {"en", "hi", "te", "ta"}

BODY_AREAS = {
    "head", "eyes", "ears", "nose", "throat", "chest", "abdomen",
    "back", "arms", "hands", "legs", "feet", "skin", "general",
}
SEVERITIES = {"mild", "moderate", "severe"}


def get_language(value) -> str:
    """Return a valid language code (defaults to English)."""
    value = (value or "en")
    if not isinstance(value, str) or value.strip().lower() not in SUPPORTED_LANGUAGES:
        raise ValidationError("Unsupported language. Choose English, Hindi, Telugu or Tamil.")
    return value.strip().lower()


def clean_text(value, field: str, max_len: int, required: bool = False) -> str:
    """Make sure `value` is text, remove hidden null characters, trim spaces, enforce a max length."""
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be text.")
    value = value.replace("\x00", "").strip()
    if required and not value:
        raise ValidationError(f"{field} is required.")
    if len(value) > max_len:
        raise ValidationError(f"{field} is too long (maximum {max_len} characters).")
    return value


def clean_list(value, field: str, max_items: int, max_len: int) -> list:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError(f"{field} must be a list.")
    if len(value) > max_items:
        raise ValidationError(f"Too many items in {field} (maximum {max_items}).")
    return [clean_text(v, field, max_len) for v in value if str(v).strip()]


def clean_age(value):
    """Age is optional. Returns an int between 0 and 120, or None."""
    if value in (None, ""):
        return None
    try:
        age = int(str(value).strip())
    except ValueError:
        raise ValidationError("Age must be a whole number.")
    if not 0 <= age <= 120:
        raise ValidationError("Age must be between 0 and 120.")
    return age


def choice(value, field: str, allowed: set, default: str) -> str:
    value = (value or default)
    if not isinstance(value, str) or value.strip().lower() not in allowed:
        raise ValidationError(f"Invalid {field}.")
    return value.strip().lower()
