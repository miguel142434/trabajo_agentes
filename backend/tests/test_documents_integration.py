import asyncio
from app.core.security import get_current_user
from tests.auth_helpers import USER_ID
import os
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from psycopg import Connection, sql

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.main import app
from app.schemas.vector import ChunkInput
from app.services.document_service import DocumentService, get_document_service
from app.services.embedding_service import EmbeddingService
from app.services.vector_service import VectorService, get_vector_service
from app.vectorstore.postgres import PostgresVectorStore
from tests.document_fixtures import docx_bytes, pdf_bytes


@unittest.skipUnless(os.environ.get("TEST_VECTOR_INTEGRATION") == "1", "Requiere PostgreSQL y Ollama reales")
class DocumentIntegrationTests(unittest.TestCase):
    def test_upload_all_formats_search_list_and_atomicity(self):
        suffix = uuid4().hex
        with tempfile.TemporaryDirectory() as directory:
            settings = get_settings().model_copy(update={
                "vector_table": "test_chunks_" + suffix,
                "document_table": "test_docs_" + suffix,
                "upload_dir": Path(directory),
            })
            store = PostgresVectorStore(settings)
            embeddings = EmbeddingService(settings)
            app.dependency_overrides[get_document_service] = lambda: DocumentService(settings, embeddings, store)
            app.dependency_overrides[get_vector_service] = lambda: VectorService(embeddings, store)
            app.dependency_overrides[get_current_user] = lambda: USER_ID
            try:
                with TestClient(app, backend_options={"loop_factory": asyncio.SelectorEventLoop}) as client:
                    self.assertEqual(client.get("/api/documents").json(), [])
                    ids = []
                    for filename, data in [
                        ("futbol.txt", b"Datos ficticios para pruebas: el club Aurora gano la Copa Horizonte de futbol."),
                        ("circuito.docx", docx_bytes()),
                        ("natacion.pdf", pdf_bytes(["La nadadora ficticia Luna Azul gano la Copa Coral de natacion."])),
                    ]:
                        response = client.post("/api/documents/upload", files={"file": (filename, data)})
                        self.assertEqual(response.status_code, 201, response.text)
                        ids.append(response.json()["document_id"])
                    # El listado usa un servicio nuevo y conexiones nuevas.
                    app.dependency_overrides[get_document_service] = lambda: DocumentService(settings, embeddings, PostgresVectorStore(settings))
                    listing = client.get("/api/documents")
                    self.assertEqual(listing.status_code, 200, listing.text)
                    self.assertEqual({d["document_id"] for d in listing.json()}, set(ids))
                    self.assertEqual({d["file_type"] for d in listing.json()}, {"pdf", "txt", "docx"})
                    search = client.post("/api/vector/test-search", json={"query": "Que club gano la Copa Horizonte de futbol?", "k": 1})
                    self.assertEqual(search.status_code, 200, search.text)
                    match = search.json()["results"][0]
                    self.assertEqual(match["filename"], "futbol.txt")
                    self.assertEqual(match["metadata"]["document_id"], ids[0])
                    self.assertEqual(match["metadata"]["file_type"], "txt")
                    print("\nDOCUMENTOS REALES:", listing.json(), flush=True)
                    print("BUSQUEDA DEPORTIVA:", search.json(), flush=True)

                with self.assertRaises(AppError):
                    store.add(uuid4(), [ChunkInput(content="bad vector")], [[1, 0]],
                              document={"filename": "fallo.txt", "file_type": "txt", "size_bytes": 10})
                self.assertEqual(len(store.list_documents(user_id=USER_ID)), 3)
                with store.connection() as conn:
                    row = conn.execute(sql.SQL("SELECT count(*) AS n FROM {}").format(store.table)).fetchone()
                    self.assertEqual(row["n"], 3)
                self.assertEqual(list(Path(directory).iterdir()), [])
            finally:
                app.dependency_overrides.clear()
                with Connection.connect(store._conninfo(), connect_timeout=5) as conn:
                    for table in [settings.document_table, settings.vector_table]:
                        conn.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier("public", table)))
