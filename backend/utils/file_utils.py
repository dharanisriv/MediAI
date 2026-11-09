"""Safe reading of uploaded files. Files are kept IN MEMORY only - nothing is written to disk."""
from pathlib import Path

from werkzeug.utils import secure_filename

from backend.config import Config
from backend.utils.errors import ValidationError

# The first bytes of a real file identify its type. We check them so that a
# renamed file (for example virus.exe renamed to report.pdf) is rejected.
_MAGIC = {
    "pdf": [b"%PDF-"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "webp": [b"RIFF"],
}


def read_upload(file_storage):
    """Validate an uploaded file and return (bytes, extension)."""
    filename = secure_filename(file_storage.filename or "")
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in Config.ALLOWED_EXTENSIONS:
        raise ValidationError("This file type is not supported. Please upload a JPG, PNG, WEBP, PDF or TXT file.")

    max_bytes = Config.MAX_UPLOAD_MB * 1024 * 1024
    data = file_storage.stream.read(max_bytes + 1)  # read one byte extra to detect "too big"
    if not data:
        raise ValidationError("The uploaded file is empty.")
    if len(data) > max_bytes:
        raise ValidationError(f"The file is too large. Maximum size is {Config.MAX_UPLOAD_MB} MB.")

    if ext in _MAGIC:
        if not any(data.startswith(sig) for sig in _MAGIC[ext]):
            raise ValidationError("The file content does not match its type. Please upload a genuine file.")
        if ext == "webp" and data[8:12] != b"WEBP":
            raise ValidationError("The file content does not match its type. Please upload a genuine file.")
    elif b"\x00" in data[:2048] and not data.startswith((b"\xff\xfe", b"\xfe\xff")):
        raise ValidationError("This does not look like a plain text file.")
    return data, ext
