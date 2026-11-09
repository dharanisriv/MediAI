"""
Tests for backend/services/gemini_service.py using a FAKE Google SDK (no internet, no key).
They prove that model fallback, retries, friendly errors and JSON repair behave as designed.
"""
import os
import sys
import types as pytypes
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services import gemini_service  # noqa: E402
from backend.utils.errors import AIServiceError  # noqa: E402


class FakeAPIError(Exception):
    def __init__(self, code, message="boom"):
        super().__init__(f"{code} {message}")
        self.code = code


class FakeResponse:
    def __init__(self, text):
        self.text = text


def install_fake_sdk(behaviour):
    """behaviour(model) -> text, or raises. Returns the list that records the models tried."""
    tried, configs = [], []

    class Models:
        def generate_content(self, model, contents, config):
            tried.append(model)
            configs.append(config)
            return FakeResponse(behaviour(model))

    class Client:
        def __init__(self, api_key=None, http_options=None):
            self.models = Models()

    class GenerateContentConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    genai = pytypes.ModuleType("google.genai")
    genai.Client = Client
    types = pytypes.ModuleType("google.genai.types")
    types.HttpOptions = lambda timeout=None: {"timeout": timeout}
    types.GenerateContentConfig = GenerateContentConfig
    types.Part = pytypes.SimpleNamespace(from_bytes=lambda data, mime_type: ("part", mime_type, len(data)))
    genai.types = types
    google = pytypes.ModuleType("google")
    google.genai = genai
    mods = {"google": google, "google.genai": genai, "google.genai.types": types}
    return mods, tried, configs


ENV = {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "model-A", "GEMINI_FALLBACK_MODELS": "model-B,model-C"}


class GeminiServiceTests(unittest.TestCase):
    def setUp(self):
        gemini_service._client = None
        gemini_service._client_key = None
        gemini_service._working_model = None
        self.sleep = patch("backend.services.gemini_service.time.sleep").start()
        self.env = patch.dict(os.environ, ENV).start()
        self.addCleanup(patch.stopall)

    def run_with(self, behaviour, fn=None):
        mods, tried, configs = install_fake_sdk(behaviour)
        with patch.dict(sys.modules, mods):
            result = (fn or (lambda: gemini_service.generate_json("sys", "hello")))()
        return result, tried, configs

    def test_json_ok_and_no_temperature_sent(self):
        result, tried, configs = self.run_with(lambda m: '{"a": 1}')
        self.assertEqual(result, {"a": 1})
        self.assertEqual(tried, ["model-A"])
        self.assertNotIn("temperature", configs[0].kwargs)  # newer Gemini models ignore/reject it
        self.assertEqual(configs[0].kwargs["response_mime_type"], "application/json")

    def test_fenced_json_is_parsed(self):
        result, _, _ = self.run_with(lambda m: '```json\n{"ok": true}\n```')
        self.assertEqual(result, {"ok": True})

    def test_model_not_found_falls_back_and_remembers(self):
        def behaviour(model):
            if model == "model-A":
                raise FakeAPIError(404, "models/model-A is not found")
            return '{"from": "%s"}' % model

        mods, tried, _ = install_fake_sdk(behaviour)
        with patch.dict(sys.modules, mods):
            first = gemini_service.generate_json("s", "x")
            second = gemini_service.generate_json("s", "x")
        self.assertEqual(first, {"from": "model-B"})
        self.assertEqual(tried, ["model-A", "model-B", "model-B"])  # second call goes straight to model-B

    def test_all_models_missing_gives_friendly_error(self):
        def behaviour(model):
            raise FakeAPIError(404, "model not found")
        with self.assertRaises(AIServiceError) as ctx:
            self.run_with(behaviour)
        self.assertIn("GEMINI_MODEL", ctx.exception.message)

    def test_overloaded_is_retried_once(self):
        calls = {"n": 0}

        def behaviour(model):
            calls["n"] += 1
            if calls["n"] == 1:
                raise FakeAPIError(503, "overloaded")
            return '{"ok": 1}'

        result, tried, _ = self.run_with(behaviour)
        self.assertEqual(result, {"ok": 1})
        self.assertEqual(tried, ["model-A", "model-A"])
        self.sleep.assert_called_once()

    def test_quota_error_message_and_status(self):
        def behaviour(model):
            raise FakeAPIError(429, "RESOURCE_EXHAUSTED quota")
        with self.assertRaises(AIServiceError) as ctx:
            self.run_with(behaviour)
        self.assertEqual(ctx.exception.status, 429)
        self.assertIn("quota", ctx.exception.message.lower())

    def test_bad_key_message(self):
        def behaviour(model):
            raise FakeAPIError(403, "API key not valid")
        with self.assertRaises(AIServiceError) as ctx:
            self.run_with(behaviour)
        self.assertIn("API key", ctx.exception.message)

    def test_timeout_message(self):
        class ReadTimeout(Exception):
            pass

        def behaviour(model):
            raise ReadTimeout("The read operation timed out")
        with self.assertRaises(AIServiceError) as ctx:
            self.run_with(behaviour)
        self.assertIn("too long", ctx.exception.message)

    def test_invalid_json_then_valid_is_retried(self):
        answers = iter(["this is not json", '{"fixed": true}'])
        result, tried, _ = self.run_with(lambda m: next(answers))
        self.assertEqual(result, {"fixed": True})
        self.assertEqual(len(tried), 2)

    def test_invalid_json_twice_fails_cleanly(self):
        with self.assertRaises(AIServiceError):
            self.run_with(lambda m: "nope")

    def test_empty_answer_fails_cleanly(self):
        with self.assertRaises(AIServiceError) as ctx:
            self.run_with(lambda m: "   ")
        self.assertIn("did not return", ctx.exception.message)

    def test_missing_key(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            with self.assertRaises(AIServiceError) as ctx:
                gemini_service.generate_json("s", "x")
        self.assertIn("GEMINI_API_KEY", ctx.exception.message)

    def test_missing_sdk(self):
        with patch.dict(sys.modules, {"google.genai": None}):
            with self.assertRaises(AIServiceError) as ctx:
                gemini_service.generate_json("s", "x")
        self.assertIn("google-genai", ctx.exception.message)

    def test_transcribe_uses_image_part(self):
        mods, tried, _ = install_fake_sdk(lambda m: "Hemoglobin 10.2")
        with patch.dict(sys.modules, mods):
            text = gemini_service.transcribe_media(b"\xff\xd8\xff", "image/jpeg")
        self.assertEqual(text, "Hemoglobin 10.2")


if __name__ == "__main__":
    unittest.main()
