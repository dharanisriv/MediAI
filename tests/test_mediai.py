"""
Automatic tests for MediAI.   Run them with:   python -m unittest discover -s tests -v

The AI (Gemini) is replaced by a fake, so these tests need NO internet and NO API key.
They check that validation, safety rules, file handling and every endpoint behave correctly.
"""
import io
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw  # noqa: E402

from backend import create_app  # noqa: E402
from backend.config import Config  # noqa: E402
from backend.services import safety_service  # noqa: E402

FAKE_REPORT = {
    "report_type": "blood test", "plain_summary": "Simple summary.",
    "lab_values": [{"test": "Hemoglobin", "purpose": "Measures oxygen-carrying protein", "value": "10.2",
                    "unit": "g/dL", "reference_range": "12-15", "flag": "LOW", "meaning": "May be low."}],
    "medical_terms": [], "key_findings": ["Hemoglobin is below the printed range"],
    "what_it_may_generally_indicate": ["Can be linked to several causes"], "answer_to_user_question": "",
    "questions_for_doctor": ["What could cause this?"], "readability_note": "",
}
FAKE_SYMPTOMS = {
    "symptom_summary": "Mild cough.", "possible_explanations": [{"name": "Common cold", "why_it_may_fit": "Often causes cough."}],
    "self_care": ["Rest", "Drink fluids"],
    "when_to_see_doctor": {"urgency": "self_care_ok", "urgency_label": "Self-care may be enough", "reasoning": "Mild.", "warning_signs_to_watch": ["High fever"]},
    "questions_for_doctor": ["How long should this last?"], "emergency_suspected": False, "emergency_reason": "",
}


def make_text_image(text="Hemoglobin 10.2 g/dL Reference 12.0 - 15.0 LOW", size=(1100, 200)):
    img = Image.new("RGB", size, "white")
    ImageDraw.Draw(img).text((20, 80), text, fill="black")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return buf


class MediAITests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()
        # reset rate limiter between tests
        from backend.utils import rate_limit
        rate_limit._hits.clear()

    # ---------- pages & health ----------
    def test_pages_are_served(self):
        for page in ("/", "/index.html", "/dashboard.html", "/report.html", "/symptoms.html",
                     "/medicines.html", "/summary.html", "/about.html", "/disclaimer.html",
                     "/css/style.css", "/js/app.js", "/js/i18n.js"):
            self.assertEqual(self.client.get(page).status_code, 200, page)

    def test_health_never_leaks_key(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "SECRET-123"}):
            data = self.client.get("/api/health").get_json()
        self.assertTrue(data["gemini_key_configured"])
        self.assertNotIn("SECRET-123", str(data))

    def test_unknown_api_is_json_404(self):
        r = self.client.get("/api/nope")
        self.assertEqual(r.status_code, 404)
        self.assertFalse(r.get_json()["ok"])

    # ---------- safety ----------
    def test_safety_check_emergency_all_languages(self):
        samples = {"en": "severe chest pain", "hi": "सीने में तेज़ दर्द", "te": "ఛాతీలో నొప్పి", "ta": "நெஞ்சு வலி"}
        for lang, text in samples.items():
            r = self.client.post("/api/safety/check", json={"text": text, "language": lang}).get_json()
            self.assertTrue(r["emergency"]["emergency"], lang)
            self.assertIn("112", r["emergency"]["message"])

    def test_safety_check_calm_text(self):
        r = self.client.post("/api/safety/check", json={"text": "mild cough for two days", "language": "en"}).get_json()
        self.assertIsNone(r["emergency"])

    def test_negation(self):
        self.assertEqual(safety_service.detect_red_flags("no chest pain"), [])
        self.assertTrue(safety_service.detect_red_flags("no fever but chest pain"))

    def test_self_harm_adds_helpline(self):
        r = self.client.post("/api/safety/check", json={"text": "I want to die", "language": "en"}).get_json()
        self.assertIn("14416", " ".join(r["emergency"]["extra"]))

    # ---------- symptoms ----------
    def test_symptoms_emergency_skips_ai(self):
        with patch("backend.services.gemini_service.generate_json") as ai:
            r = self.client.post("/api/symptoms/analyze", json={
                "language": "en", "area": "chest", "symptoms": ["Chest pain or pressure"], "severity": "severe"}).get_json()
            ai.assert_not_called()  # the emergency warning must NOT wait for the AI
        self.assertTrue(r["emergency"]["emergency"])
        self.assertIsNone(r["result"])

    def test_symptoms_normal(self):
        with patch("backend.services.gemini_service.generate_json", return_value=dict(FAKE_SYMPTOMS)):
            r = self.client.post("/api/symptoms/analyze", json={
                "language": "hi", "area": "throat", "symptoms": ["Sore throat"], "description": "mild",
                "severity": "mild", "age": "25"}).get_json()
        self.assertTrue(r["ok"])
        self.assertIsNone(r["emergency"])
        self.assertEqual(r["result"]["when_to_see_doctor"]["urgency"], "self_care_ok")
        self.assertIn("112", r["disclaimer"])

    def test_symptoms_ai_can_raise_emergency(self):
        fake = dict(FAKE_SYMPTOMS, emergency_suspected=True, emergency_reason="Could be serious")
        with patch("backend.services.gemini_service.generate_json", return_value=fake):
            r = self.client.post("/api/symptoms/analyze", json={
                "language": "en", "area": "general", "symptoms": ["Fatigue"], "severity": "moderate"}).get_json()
        self.assertTrue(r["emergency"]["emergency"])
        self.assertEqual(r["emergency"]["source"], "ai")
        self.assertIsNone(r["result"])

    def test_symptoms_validation(self):
        bad = [
            {"language": "fr", "area": "head", "symptoms": ["x"]},
            {"language": "en", "area": "knee", "symptoms": ["x"]},
            {"language": "en", "area": "head"},
            {"language": "en", "area": "head", "symptoms": ["x"], "age": "200"},
            {"language": "en", "area": "head", "symptoms": ["x"], "severity": "extreme"},
            {"language": "en", "area": "head", "description": "x" * 3000},
        ]
        for payload in bad:
            r = self.client.post("/api/symptoms/analyze", json=payload)
            self.assertEqual(r.status_code, 400, payload)

    def test_malformed_ai_output_is_repaired(self):
        with patch("backend.services.gemini_service.generate_json", return_value={"self_care": "just rest", "when_to_see_doctor": "oops"}):
            r = self.client.post("/api/symptoms/analyze", json={"language": "en", "area": "head", "symptoms": ["Headache"]}).get_json()
        self.assertEqual(r["result"]["self_care"], ["just rest"])
        self.assertEqual(r["result"]["when_to_see_doctor"]["urgency"], "see_doctor_soon")

    # ---------- report ----------
    def _post_report(self, data):
        return self.client.post("/api/report/analyze", data=data, content_type="multipart/form-data")

    def test_report_pasted_text(self):
        with patch("backend.services.gemini_service.generate_json", return_value=dict(FAKE_REPORT)):
            r = self._post_report({"language": "en", "text": "Hemoglobin 10.2 g/dL (12-15) L", "question": "Is this bad?"}).get_json()
        self.assertTrue(r["ok"])
        self.assertEqual(r["result"]["lab_values"][0]["flag"], "low")  # "LOW" is normalised
        self.assertIn("Hemoglobin", r["extracted_text"])

    def test_report_requires_input(self):
        self.assertEqual(self._post_report({"language": "en"}).status_code, 400)

    def test_report_txt_upload(self):
        with patch("backend.services.gemini_service.generate_json", return_value=dict(FAKE_REPORT)):
            r = self._post_report({"language": "te", "file": (io.BytesIO(b"WBC 11000 /cumm (4000-11000) Normal range"), "r.txt")}).get_json()
        self.assertEqual(r["extraction_methods"], ["text-file"])

    def test_report_rejects_bad_files(self):
        r = self._post_report({"language": "en", "file": (io.BytesIO(b"MZ\x90\x00 exe"), "virus.exe")})
        self.assertEqual(r.status_code, 400)
        r = self._post_report({"language": "en", "file": (io.BytesIO(b"this is not a pdf at all, just text"), "fake.pdf")})
        self.assertEqual(r.status_code, 400)
        r = self._post_report({"language": "en", "file": (io.BytesIO(b"not an image really"), "fake.png")})
        self.assertEqual(r.status_code, 400)

    def test_report_too_large(self):
        big = io.BytesIO(b"%PDF-" + b"0" * (Config.MAX_UPLOAD_MB * 1024 * 1024 + 10))
        r = self._post_report({"language": "en", "file": (big, "big.pdf")})
        self.assertIn(r.status_code, (400, 413))

    def test_report_image_uses_ai_vision_when_ocr_poor(self):
        # A blank-ish image: Tesseract finds nothing, so the AI vision fallback is used.
        blank = io.BytesIO()
        Image.new("RGB", (400, 200), "white").save(blank, "PNG")
        blank.seek(0)
        with patch("backend.services.gemini_service.transcribe_media", return_value="Glucose fasting 98 mg/dL 70-100") as t, \
             patch("backend.services.gemini_service.generate_json", return_value=dict(FAKE_REPORT)):
            r = self._post_report({"language": "en", "file": (blank, "scan.png")}).get_json()
        t.assert_called_once()
        self.assertEqual(r["extraction_methods"], ["image-ai-vision"])

    def test_report_image_with_text_runs(self):
        from backend.services import ocr_service
        if not ocr_service.tesseract_available():
            self.skipTest("Tesseract not installed")
        with patch("backend.services.gemini_service.transcribe_media", return_value="AI fallback text for this report image") as t, \
             patch("backend.services.gemini_service.generate_json", return_value=dict(FAKE_REPORT)):
            r = self._post_report({"language": "en", "file": (make_text_image(), "lab.png")}).get_json()
        self.assertTrue(r["ok"])
        self.assertIn(r["extraction_methods"][0], ("image-tesseract", "image-ai-vision"))

    def test_report_pdf_text(self):
        pdf = _make_pdf("Hemoglobin 10.2 g/dL Reference range 12.0 to 15.0 g/dL Low")
        with patch("backend.services.gemini_service.generate_json", return_value=dict(FAKE_REPORT)):
            r = self._post_report({"language": "en", "file": (io.BytesIO(pdf), "r.pdf")}).get_json()
        self.assertEqual(r["extraction_methods"], ["pdf-text"])
        self.assertIn("Hemoglobin", r["extracted_text"])

    # ---------- medicines ----------
    def test_medicine_grounded_in_label(self):
        label = {"openfda": {"brand_name": ["TYLENOL"], "generic_name": ["ACETAMINOPHEN"]},
                 "indications_and_usage": ["temporarily reduces fever"], "warnings": ["Liver warning"], "effective_time": "20240101"}
        fake = {"identified": True, "medicine_name": "Paracetamol", "generic_name": "acetaminophen", "common_uses": ["Fever"]}
        with patch("backend.services.medicine_service._query_openfda", return_value=label), \
             patch("backend.services.gemini_service.generate_json", return_value=fake) as ai:
            r = self.client.post("/api/medicines/search", json={"name": "Paracetamol", "language": "en"}).get_json()
        self.assertTrue(r["source"]["verified"])
        self.assertIn("[Uses]", ai.call_args[0][1])  # label text really was given to the AI
        self.assertNotIn("dosage", ai.call_args[0][0].split("SOURCE MODE")[1].lower().replace("do not give any dose", ""))

    def test_medicine_not_in_database_is_marked_unverified(self):
        fake = {"identified": True, "medicine_name": "Dolo 650", "common_uses": ["Fever"]}
        with patch("backend.services.medicine_service._query_openfda", return_value=None), \
             patch("backend.services.gemini_service.generate_json", side_effect=[{"is_medicine": False, "generic_names": []}, fake]):
            r = self.client.post("/api/medicines/search", json={"name": "Dolo 650", "language": "en"}).get_json()
        self.assertFalse(r["source"]["verified"])

    def test_medicine_brand_to_generic(self):
        label = {"openfda": {"generic_name": ["ACETAMINOPHEN"]}, "indications_and_usage": ["fever"]}
        calls = []

        def fake_query(field, name):
            calls.append(name)
            return label if name == "acetaminophen" else None

        with patch("backend.services.medicine_service._query_openfda", side_effect=fake_query), \
             patch("backend.services.gemini_service.generate_json",
                   side_effect=[{"is_medicine": True, "generic_names": ["paracetamol", "acetaminophen"]}, {"identified": True}]):
            r = self.client.post("/api/medicines/search", json={"name": "Crocin", "language": "en"}).get_json()
        self.assertTrue(r["source"]["verified"])
        self.assertEqual(r["source"]["matched_via"], "ingredient")

    def test_medicine_validation(self):
        for name in ("", "a", "x" * 200, "drop table; --<script>"):
            r = self.client.post("/api/medicines/search", json={"name": name, "language": "en"})
            self.assertEqual(r.status_code, 400, name)

    # ---------- summary ----------
    def test_summary(self):
        fake = {"basic_information": "Age 30", "medical_history": "Not provided", "important_concerns": ["x"]}
        with patch("backend.services.gemini_service.generate_json", return_value=fake):
            r = self.client.post("/api/summary/generate", json={"language": "ta", "age": 30, "symptoms": "cough"}).get_json()
        self.assertEqual(r["result"]["basic_information"], "Age 30")
        self.assertIsNone(r["emergency"])

    def test_summary_shows_emergency_banner_but_still_summarises(self):
        with patch("backend.services.gemini_service.generate_json", return_value={"basic_information": "x"}):
            r = self.client.post("/api/summary/generate", json={"language": "en", "symptoms": "crushing chest pain"}).get_json()
        self.assertTrue(r["emergency"]["emergency"])
        self.assertIn("result", r)

    def test_summary_empty_rejected(self):
        self.assertEqual(self.client.post("/api/summary/generate", json={"language": "en"}).status_code, 400)

    # ---------- AI errors & limits ----------
    def test_missing_api_key_gives_friendly_error(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            r = self.client.post("/api/summary/generate", json={"language": "en", "symptoms": "cough"})
        self.assertEqual(r.status_code, 500)
        self.assertIn("GEMINI_API_KEY", r.get_json()["error"])

    def test_rate_limit(self):
        with patch.object(Config, "RATE_LIMIT_PER_MINUTE", 3), \
             patch("backend.services.gemini_service.generate_json", return_value={"basic_information": "x"}):
            codes = [self.client.post("/api/summary/generate", json={"language": "en", "symptoms": "cough"}).status_code for _ in range(5)]
        self.assertEqual(codes, [200, 200, 200, 429, 429])


def _make_pdf(text):
    """Build a tiny one-page PDF containing `text` (no extra libraries needed)."""
    stream = f"BT /F1 12 Tf 50 750 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return out


if __name__ == "__main__":
    unittest.main()
