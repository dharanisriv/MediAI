"""
Reading text out of uploaded reports.

  .txt  -> just decode the text
  .pdf  -> pypdf extracts the text layer; if the PDF is a scan (no text), Gemini vision reads it
  image -> Tesseract OCR if installed and the result looks good; otherwise Gemini vision reads it

Files are handled in memory only. Images are re-encoded, which also removes hidden metadata (like GPS location).
"""
import io
import logging
import os
import shutil
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from backend.config import Config
from backend.services import gemini_service
from backend.utils.errors import ValidationError

log = logging.getLogger("mediai")
Image.MAX_IMAGE_PIXELS = 50_000_000  # protects against "decompression bomb" images

_WINDOWS_TESSERACT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


def tesseract_available() -> bool:
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        return False
    cmd = os.getenv("TESSERACT_CMD")
    return bool(cmd and Path(cmd).exists()) or bool(shutil.which("tesseract")) or _WINDOWS_TESSERACT.exists()


def _prepare_image(data: bytes) -> bytes:
    """Check the image is real, fix rotation, shrink big photos, and return clean JPEG bytes."""
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.load()
            img = ImageOps.exif_transpose(img).convert("RGB")
            img.thumbnail((2200, 2200))
            out = io.BytesIO()
            img.save(out, "JPEG", quality=90)
            return out.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise ValidationError("This image could not be read. Please upload a clear JPG, PNG or WEBP photo.")


def _tesseract_read(jpeg_bytes: bytes):
    """Return (text, average_confidence) or ("", 0) if Tesseract is not usable."""
    if not tesseract_available():
        return "", 0.0
    import pytesseract

    cmd = os.getenv("TESSERACT_CMD")
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd
    elif not shutil.which("tesseract") and _WINDOWS_TESSERACT.exists():
        pytesseract.pytesseract.tesseract_cmd = str(_WINDOWS_TESSERACT)
    try:
        installed = pytesseract.get_languages(config="")
        langs = "+".join(l for l in ("eng", "hin", "tel", "tam") if l in installed) or "eng"
        data = pytesseract.image_to_data(
            Image.open(io.BytesIO(jpeg_bytes)), lang=langs, output_type=pytesseract.Output.DICT, timeout=40
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("Tesseract failed: %s", type(exc).__name__)
        return "", 0.0

    lines, confidences = {}, []
    for i, word in enumerate(data["text"]):
        if not word.strip():
            continue
        conf = float(data["conf"][i])
        if conf < 0:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(word)
        confidences.append(conf)
    text = "\n".join(" ".join(words) for words in lines.values())
    return text, (sum(confidences) / len(confidences) if confidences else 0.0)


def _decode_text_file(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16"):
        try:
            return data.decode(encoding)
        except UnicodeError:
            continue
    return data.decode("latin-1", errors="replace")


def extract_text(data: bytes, ext: str) -> dict:
    """Return {"text": ..., "method": ..., "warnings": [...]} for an uploaded file."""
    warnings = []

    if ext == "txt":
        return {"text": _decode_text_file(data), "method": "text-file", "warnings": warnings}

    if ext == "pdf":
        try:
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted and not reader.decrypt(""):
                raise ValidationError("This PDF is password-protected. Please remove the password and upload it again.")
            pages = reader.pages[: Config.MAX_PDF_PAGES]
            if len(reader.pages) > Config.MAX_PDF_PAGES:
                warnings.append(f"Only the first {Config.MAX_PDF_PAGES} pages were read.")
            text = "\n\n".join((page.extract_text() or "") for page in pages).strip()
        except ValidationError:
            raise
        except (PyPdfError, ValueError, OSError, KeyError):
            raise ValidationError("This PDF could not be read. It may be damaged. Try uploading a photo of the report instead.")
        if len(text) >= 50:
            return {"text": text, "method": "pdf-text", "warnings": warnings}
        # Scanned PDF (pictures only): let Gemini read it.
        if Config.OCR_ENGINE == "tesseract":
            raise ValidationError("This PDF has no selectable text. Upload it as an image, or set OCR_ENGINE=auto.")
        warnings.append("This PDF looks scanned, so the AI read the pages visually. Please check the extracted text.")
        return {"text": gemini_service.transcribe_media(data, "application/pdf"), "method": "pdf-ai-vision", "warnings": warnings}

    # ---- images (jpg / jpeg / png / webp) ----
    jpeg = _prepare_image(data)
    engine = Config.OCR_ENGINE
    if engine in ("auto", "tesseract"):
        text, confidence = _tesseract_read(jpeg)
        good = len(text.strip()) >= 60 and confidence >= 65
        if good or engine == "tesseract":
            if not good:
                warnings.append("The local OCR result looks low quality. Please check the extracted text carefully.")
            if text.strip():
                return {"text": text, "method": "image-tesseract", "warnings": warnings}
            raise ValidationError("No readable text was found in this image. Try a clearer, well-lit photo.")
    warnings.append("The AI read the image visually. Please check the extracted text for mistakes.")
    return {"text": gemini_service.transcribe_media(jpeg, "image/jpeg"), "method": "image-ai-vision", "warnings": warnings}
