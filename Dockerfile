# Used for online hosting (Render, Hugging Face Spaces, etc.).
# It installs the Tesseract OCR program (English + Hindi + Telugu + Tamil) and starts MediAI with gunicorn.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin tesseract-ocr-tel tesseract-ocr-tam \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV HOST=0.0.0.0
# Hosting platforms provide the PORT variable; 10000 is Render's default.
CMD gunicorn app:app --bind 0.0.0.0:${PORT:-10000} --workers 2 --threads 4 --timeout 120
