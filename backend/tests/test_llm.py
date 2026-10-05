from app.core.security import get_current_user
from tests.auth_helpers import USER_ID, CONVERSATION_ID, MemoryInteractions
"""Pruebas del contrato HTTP y errores del proveedor, sin descargar modelos."""

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock

import httpx
from fastapi.testclient import TestClient
from langchain_ollama import ChatOllama
from ollama import ResponseError
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.main import app
from app.services.llm_service import LLMService, get_llm_service


class LLMEndpointTests(unittest.TestCase):
    def setUp(self):
        startup = patch("app.main.init_db", new=AsyncMock())
        startup.start()
        self.addCleanup(startup.stop)
        self.env_patch = patch.dict(os.environ, {}, clear=True)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.service = LLMService(Settings(_env_file=None, ollama_timeout=1))
        app.dependency_overrides[get_llm_service] = lambda: self.service
        app.dependency_overrides[get_current_user] = lambda: USER_ID
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()

    def test_success_through_chatollama(self):
        async def respond(request):
            import json

            payload = json.loads(request.content)
            self.assertEqual(payload["model"], "qwen3:8b")
            self.assertEqual(payload["messages"][0]["content"], "Hola")
            self.assertEqual(payload["options"]["temperature"], 0)
            return httpx.Response(200, json={
                "model": "qwen3:8b",
                "message": {"role": "assistant", "content": "Hola desde Qwen"},
                "done": True,
            })

        self.service.model = ChatOllama(
            model="qwen3:8b", temperature=0, reasoning=False,
            async_client_kwargs={"transport": httpx.MockTransport(respond)},
        )
        result = self.client.post("/api/test-llm", json={"prompt": "Hola"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {"response": "Hola desde Qwen"})

    def test_provider_errors(self):
        cases = [
            (ConnectionError("offline"), 503, "conectar"),
            (httpx.ConnectError("offline"), 503, "conectar"),
            (ResponseError("model not found", status_code=404), 503, "ollama pull qwen3:8b"),
            (httpx.ReadTimeout("slow"), 504, "tiempo"),
            (ResponseError("internal error", status_code=500), 502, "generar"),
            (httpx.RemoteProtocolError("broken stream"), 503, "interrumpió"),
        ]
        for error, status, detail in cases:
            with self.subTest(error=error), patch.object(ChatOllama, "ainvoke", side_effect=error):
                result = self.client.post("/api/test-llm", json={"prompt": "Hola"})
                self.assertEqual(result.status_code, status)
                self.assertIn(detail, result.json()["detail"])

    def test_total_timeout(self):
        async def slow(*args, **kwargs):
            await asyncio.sleep(1)

        self.service.settings.ollama_timeout = 0.01
        with patch.object(ChatOllama, "ainvoke", side_effect=slow):
            result = self.client.post("/api/test-llm", json={"prompt": "Hola"})
        self.assertEqual(result.status_code, 504)

    def test_invalid_prompts(self):
        for body in [{}, {"prompt": ""}, {"prompt": "   "}, {"prompt": 1}, {"prompt": "a" * 16001}]:
            with self.subTest(body=str(body)[:80]), patch.object(ChatOllama, "ainvoke") as invoke:
                self.assertEqual(self.client.post("/api/test-llm", json=body).status_code, 422)
                invoke.assert_not_called()

    def test_empty_response(self):
        from langchain_core.messages import AIMessage

        with patch.object(ChatOllama, "ainvoke", return_value=AIMessage(content="")):
            self.assertEqual(self.client.post("/api/test-llm", json={"prompt": "Hola"}).status_code, 502)

    def test_health_and_docs(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})
        self.assertEqual(self.client.get("/api/health").json(), {"status": "ok"})
        self.assertEqual(self.client.get("/docs").status_code, 200)
        self.assertIn("/api/test-llm", self.client.get("/openapi.json").json()["paths"])

    def test_unexpected_error_is_hidden(self):
        with TestClient(app, raise_server_exceptions=False) as client:
            with patch.object(ChatOllama, "ainvoke", side_effect=RuntimeError("private data")):
                response = client.post("/api/test-llm", json={"prompt": "Hola"})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Error interno del servidor."})

    def test_cors_preflight(self):
        from app.main import create_app

        settings = Settings(_env_file=None, cors_origins=["http://localhost:5173"])
        with patch("app.main.get_settings", return_value=settings):
            test_app = create_app()
        with TestClient(test_app) as client:
            for origin, expected in [("http://localhost:5173", 200), ("https://example.invalid", 400)]:
                response = client.options("/api/test-llm", headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type",
                })
                self.assertEqual(response.status_code, expected)
                if expected == 200:
                    self.assertEqual(response.headers["access-control-allow-origin"], origin)
                else:
                    self.assertNotIn("access-control-allow-origin", response.headers)


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.env_patch = patch.dict(os.environ, {}, clear=True)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def tearDown(self):
        get_settings.cache_clear()

    def test_env_file_and_environment_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("OLLAMA_MODEL=qwen3:4b\nOLLAMA_TEMPERATURE=0.5\n", encoding="utf-8")
            with patch.dict(Settings.model_config, {"env_file": env_file}), patch.dict(os.environ, {"OLLAMA_MODEL": "qwen3:8b"}, clear=True):
                get_settings.cache_clear()
                settings = get_settings()
                self.assertEqual(settings.ollama_model, "qwen3:8b")
                self.assertEqual(settings.ollama_temperature, 0.5)

    def test_invalid_settings(self):
        for settings in [{"ollama_timeout": 0}, {"ollama_timeout": float("inf")}, {"ollama_temperature": float("nan")}, {"ollama_temperature": -1}, {"ollama_model": " "}, {"ollama_base_url": "invalid"}]:
            with self.subTest(settings=settings), self.assertRaises(ValidationError):
                Settings(_env_file=None, **settings)

    def test_env_path_independent_of_working_directory(self):
        env_file = Path(Settings.model_config["env_file"])
        self.assertTrue(env_file.is_absolute())
        self.assertEqual(env_file, Path(__file__).resolve().parents[2] / ".env")

    def test_cors_from_environment(self):
        with patch.dict(os.environ, {"CORS_ORIGINS": '["http://localhost:5173","http://localhost:3000"]'}):
            settings = Settings(_env_file=None)
        self.assertEqual(settings.cors_origins, ["http://localhost:5173", "http://localhost:3000"])


if __name__ == "__main__":
    unittest.main()
