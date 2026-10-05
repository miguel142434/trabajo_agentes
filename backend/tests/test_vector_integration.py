import asyncio
from app.core.security import get_current_user
from tests.auth_helpers import USER_ID
"""Prueba optativa real: TEST_VECTOR_INTEGRATION=1; usa una tabla temporal propia."""

import os
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from psycopg import Connection, sql

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.main import app
from app.schemas.vector import ChunkInput
from app.services.embedding_service import EmbeddingService
from app.services.vector_service import VectorService, get_vector_service
from app.vectorstore.postgres import PostgresVectorStore


@unittest.skipUnless(os.environ.get("TEST_VECTOR_INTEGRATION") == "1", "Requiere Ollama y PostgreSQL reales")
class VectorIntegrationTests(unittest.TestCase):
    def test_semantic_search_persistence_and_dimension_guard(self):
        table = "test_chunks_" + uuid4().hex
        settings = get_settings().model_copy(update={"vector_table": table})
        store = PostgresVectorStore(settings)
        app.dependency_overrides[get_vector_service] = lambda: VectorService(EmbeddingService(settings), store)
        app.dependency_overrides[get_current_user] = lambda: USER_ID
        try:
            with TestClient(app, backend_options={"loop_factory": asyncio.SelectorEventLoop}) as client:
                empty = client.post("/api/vector/test-search", json={"query": "animales"})
                self.assertEqual(empty.status_code, 200, empty.text)
                self.assertEqual(empty.json()["results"], [])
                response = client.post("/api/vector/test-add", json={"chunks": [
                    {"content": "Los gatos son animales domésticos que ronronean y cazan ratones.", "filename": "gatos.txt", "page": 1, "metadata": {"tema": "animales"}},
                    {"content": "PostgreSQL es una base de datos relacional que permite consultar tablas mediante SQL.", "filename": "datos.txt"},
                    {"content": "Para preparar pan se mezcla harina, agua y levadura y se hornea la masa.", "filename": "pan.txt"},
                ]})
                self.assertEqual(response.status_code, 201, response.text)
                self.assertEqual(response.json()["chunks_created"], 3)
                # Nuevo servicio y conexiones: los datos deben venir de PostgreSQL.
                app.dependency_overrides[get_vector_service] = lambda: VectorService(EmbeddingService(settings), PostgresVectorStore(settings))
                search = client.post("/api/vector/test-search", json={"query": "¿Qué mascota ronronea y atrapa ratones?", "k": 2})
                self.assertEqual(search.status_code, 200, search.text)
                results = search.json()["results"]
                self.assertEqual(len(results), 2)
                self.assertEqual(results[0]["filename"], "gatos.txt")
                self.assertEqual(results[0]["metadata"], {"tema": "animales"})
                self.assertEqual(results[0]["page"], 1)
                self.assertLessEqual(results[0]["distance"], results[1]["distance"])
                print("\nEVIDENCIA REAL:", search.json(), flush=True)

            # Un lote con un vector inválido debe revertirse completo.
            with self.assertRaises(AppError):
                store.add(uuid4(), [ChunkInput(content="válido"), ChunkInput(content="inválido")],
                          [[1.0] * settings.embedding_dimension, [1.0, 0.0]])

            with store.connection() as conn:
                row = conn.execute(sql.SQL("SELECT count(*) AS count, min(vector_dims(embedding)) AS dims FROM {}").format(store.table)).fetchone()
                self.assertEqual(row, {"count": 3, "dims": settings.embedding_dimension})
            other_model = PostgresVectorStore(settings.model_copy(update={"ollama_embedding_model": "modelo-distinto"}))
            self.assertEqual(other_model.search([1.0] * settings.embedding_dimension, 4), [])
            wrong = PostgresVectorStore(settings.model_copy(update={"embedding_dimension": 3}))
            with self.assertRaises(AppError) as error:
                wrong.search([1, 0, 0], 1)
            self.assertEqual(error.exception.status_code, 409)
        finally:
            app.dependency_overrides.clear()
            # Eliminar solo la tabla de prueba cuyo nombre se generó en esta ejecución.
            with Connection.connect(store._conninfo(), connect_timeout=settings.postgres_connect_timeout) as conn:
                conn.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier("public", table)))
