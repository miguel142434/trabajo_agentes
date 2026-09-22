"""Pruebas del contrato HTTP y errores del proveedor, sin descargar modelos."""

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
        self.service = LLMService(Settings(ollama_timeout=1))
        app.dependency_overrides[get_llm_service] = lambda: self.service
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
        self.assertEqual(self.client.get("/docs").status_code, 200)
        self.assertIn("/api/test-llm", self.client.get("/openapi.json").json()["paths"])


class SettingsTests(unittest.TestCase):
    def tearDown(self):
        get_settings.cache_clear()

    def test_env_file_and_environment_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("OLLAMA_MODEL=qwen3:4b\nOLLAMA_TEMPERATURE=0.5\n", encoding="utf-8")
            with patch("app.core.config.ENV_FILE", env_file), patch.dict(os.environ, {"OLLAMA_MODEL": "qwen3:8b"}, clear=True):
                get_settings.cache_clear()
                settings = get_settings()
                self.assertEqual(settings.ollama_model, "qwen3:8b")
                self.assertEqual(settings.ollama_temperature, 0.5)

    def test_invalid_settings(self):
        for settings in [{"ollama_timeout": 0}, {"ollama_temperature": -1}, {"ollama_model": " "}, {"ollama_base_url": "invalid"}]:
            with self.subTest(settings=settings), self.assertRaises(ValidationError):
                Settings(**settings)


if __name__ == "__main__":
    unittest.main()
