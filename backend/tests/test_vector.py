from app.core.security import get_current_user
from tests.auth_helpers import USER_ID, CONVERSATION_ID, MemoryInteractions
"""Pruebas sin servicios externos para la capa vectorial."""

import os
import unittest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
from ollama import ResponseError
from pydantic import ValidationError
from psycopg import OperationalError

from app.core.config import Settings
from app.core.exceptions import AppError
from app.main import app
from app.services.embedding_service import EmbeddingService
from app.services.vector_service import VectorService, get_vector_service
from app.vectorstore.postgres import PostgresVectorStore


class EmbeddingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        with patch.dict(os.environ, {}, clear=True):
            self.service = EmbeddingService(Settings(_env_file=None, embedding_dimension=3))
        self.service.model = Mock(aembed_documents=AsyncMock(return_value=[[1.0, 0.0, 0.0]]))

    async def test_nomic_prefixes_and_dimension(self):
        self.assertEqual(await self.service.embed(["texto"]), [[1, 0, 0]])
        self.service.model.aembed_documents.assert_awaited_with(["search_document: texto"])
        await self.service.embed(["pregunta"], query=True)
        self.service.model.aembed_documents.assert_awaited_with(["search_query: pregunta"])
        self.service.settings.ollama_embedding_model = "otro-modelo"
        await self.service.embed(["texto"])
        self.service.model.aembed_documents.assert_awaited_with(["texto"])

    async def test_invalid_vectors(self):
        for vectors, status in [([], 502), ([[1, 0]], 409), ([[0, 0, 0]], 502), ([[float("nan"), 0, 1]], 502)]:
            self.service.model.aembed_documents.return_value = vectors
            with self.subTest(vectors=vectors), self.assertRaises(AppError) as error:
                await self.service.embed(["texto"])
            self.assertEqual(error.exception.status_code, status)

    async def test_ollama_failures(self):
        for failure, status in [
            (ConnectionError(), 503), (httpx.ReadTimeout("timeout"), 504),
            (ResponseError("missing", status_code=404), 503),
            (ResponseError("failed", status_code=500), 502),
        ]:
            self.service.model.aembed_documents.side_effect = failure
            with self.subTest(failure=failure), self.assertRaises(AppError) as error:
                await self.service.embed(["texto"])
            self.assertEqual(error.exception.status_code, status)


class VectorEndpointTests(unittest.TestCase):
    def setUp(self):
        self.embeddings = Mock(embed=AsyncMock(return_value=[[1.0, 0.0, 0.0]]))
        self.store = Mock()
        self.store.add.return_value = [uuid4()]
        self.store.search.return_value = []
        service = VectorService(self.embeddings, self.store)
        app.dependency_overrides[get_vector_service] = lambda: service
        app.dependency_overrides[get_current_user] = lambda: USER_ID
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def test_add_contract(self):
        document_id = uuid4()
        response = self.client.post("/api/vector/test-add", json={
            "document_id": str(document_id),
            "chunks": [{"content": "Un gato", "filename": "gatos.txt", "page": 2, "metadata": {"tema": "animales"}}],
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["document_id"], str(document_id))
        self.assertEqual(response.json()["chunks_created"], 1)
        self.assertEqual(self.store.add.call_args.args[1][0].metadata, {"tema": "animales"})

    def test_search_empty_and_top_k(self):
        response = self.client.post("/api/vector/test-search", json={"query": "gato", "k": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"results": []})
        self.store.search.assert_called_once_with([1, 0, 0], 2, user_id=USER_ID)
        self.embeddings.embed.assert_awaited_with(["gato"], query=True)

    def test_embedding_failure_never_writes(self):
        self.embeddings.embed.side_effect = AppError("No disponible", 503)
        response = self.client.post("/api/vector/test-add", json={"chunks": [{"content": "texto"}]})
        self.assertEqual(response.status_code, 503)
        self.store.add.assert_not_called()

    def test_database_error(self):
        self.store.search.side_effect = AppError("PostgreSQL no disponible", 503)
        response = self.client.post("/api/vector/test-search", json={"query": "gato"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("PostgreSQL", response.json()["detail"])

    def test_invalid_requests(self):
        for route, body in [
            ("test-add", {"chunks": []}),
            ("test-add", {"chunks": [{"content": " "}]}),
            ("test-add", {"chunks": [{"content": "texto", "page": 0}]}),
            ("test-search", {"query": " "}),
            ("test-search", {"query": "gato", "k": 0}),
            ("test-search", {"query": "gato", "k": 51}),
        ]:
            self.assertEqual(self.client.post(f"/api/vector/{route}", json=body).status_code, 422)
        self.embeddings.embed.assert_not_awaited()


class StoreTests(unittest.TestCase):
    def test_connection_failure(self):
        with patch.dict(os.environ, {}, clear=True):
            store = PostgresVectorStore(Settings(_env_file=None))
        with patch("app.vectorstore.postgres.Connection.connect", side_effect=OperationalError("secret")):
            with self.assertRaises(AppError) as error:
                store.search([1, 0], 1)
        self.assertEqual(error.exception.status_code, 503)
        self.assertNotIn("secret", error.exception.message)

    def test_table_name_validation(self):
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, vector_table="chunks; DROP TABLE users")
