"""
Medicine information.

Step 1  Look the medicine up in the official US FDA drug-label database (openFDA - free, no key needed).
Step 2  If not found, ask Gemini for the generic (ingredient) name of the brand and search again.
Step 3  Give Gemini ONLY the official label text and ask it to simplify it.   -> "verified source"
        If there is no label at all, Gemini answers from general knowledge.  -> clearly marked "NOT verified"

Important: openFDA contains US labels. Indian brands can differ (strengths, extra ingredients).
"""
import logging
import os

import requests

from backend.services import gemini_service
from backend.utils.errors import AIServiceError

log = logging.getLogger("mediai")

OPENFDA_URL = "https://api.fda.gov/drug/label.json"

# Which parts of the label we keep (dosage sections are deliberately NOT included).
LABEL_FIELDS = [
    ("indications_and_usage", "Uses"),
    ("purpose", "Purpose"),
    ("mechanism_of_action", "How it works"),
    ("boxed_warning", "Boxed warning"),
    ("warnings", "Warnings"),
    ("warnings_and_cautions", "Warnings and precautions"),
    ("do_not_use", "Do not use"),
    ("ask_doctor", "Ask a doctor before use"),
    ("stop_use", "Stop use and ask a doctor"),
    ("adverse_reactions", "Side effects"),
    ("drug_interactions", "Interactions"),
    ("storage_and_handling", "Storage"),
    ("how_supplied", "How supplied / storage"),
]
MAX_CHARS_PER_FIELD = 1800


def _query_openfda(field: str, name: str):
    """Search one openFDA field. Returns the first label found, or None."""
    params = {"search": f'{field}:"{name}"', "limit": 1}
    api_key = os.getenv("OPENFDA_API_KEY")
    if api_key:
        params["api_key"] = api_key
    try:
        response = requests.get(OPENFDA_URL, params=params, timeout=8)
    except requests.RequestException:
        raise AIServiceError("The medicine database could not be reached. Check your internet connection and try again.")
    if response.status_code == 404:  # openFDA uses 404 for "no matches"
        return None
    if response.status_code == 429:
        raise AIServiceError("The medicine database is busy. Please try again in a minute.", status=429)
    if response.status_code != 200:
        return None
    results = response.json().get("results") or []
    return results[0] if results else None


def find_label(names: list):
    for name in names:
        for field in ("openfda.brand_name", "openfda.generic_name", "openfda.substance_name"):
            label = _query_openfda(field, name)
            if label:
                return label
    return None


def _label_to_text(label: dict) -> str:
    parts = []
    for key, title in LABEL_FIELDS:
        value = label.get(key)
        if value:
            text = " ".join(value) if isinstance(value, list) else str(value)
            parts.append(f"[{title}] {text[:MAX_CHARS_PER_FIELD]}")
    return "\n".join(parts)


def lookup(name: str, language: str) -> dict:
    """Return {"result": {...}, "source": {...}} for the medicine."""
    from backend.services.normalize import MEDICINE_SPEC, coerce
    from backend.services.prompts import medicine_prompt

    label = find_label([name])
    matched_via = "name"
    if not label:
        # Maybe it is a brand name (e.g. "Dolo 650"). Ask Gemini for the ingredient and try again.
        guess = gemini_service.normalize_medicine_name(name)
        generics = [g.strip() for g in (guess.get("generic_names") or []) if isinstance(g, str) and g.strip()][:3]
        if guess.get("is_medicine") is True and generics:
            safe = [g.replace('"', "") for g in generics]
            label = find_label(safe)
            matched_via = "ingredient"

    excerpts = _label_to_text(label) if label else ""
    system, user = medicine_prompt(name, language, excerpts)
    result = coerce(gemini_service.generate_json(system, user), MEDICINE_SPEC)

    if excerpts and label:
        openfda = label.get("openfda", {})
        source = {
            "verified": True,
            "name": "US FDA drug label (openFDA)",
            "brand_names": (openfda.get("brand_name") or [])[:3],
            "generic_names": (openfda.get("generic_name") or [])[:3],
            "label_date": str(label.get("effective_time", "")),
            "matched_via": matched_via,
        }
    else:
        source = {"verified": False, "name": "AI general knowledge (no official label found)"}
    return {"result": result, "source": source}
