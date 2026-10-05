from app.core.security import get_current_user
from tests.auth_helpers import USER_ID, CONVERSATION_ID, MemoryInteractions
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import AppError
from app.main import app
from app.services.document_service import DocumentService, get_document_service
from tests.document_fixtures import docx_bytes, pdf_bytes


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        with patch.dict(os.environ, {}, clear=True):
            self.settings = Settings(_env_file=None, upload_dir=Path(self.temp.name), chunk_size=80, chunk_overlap=10)
        async def embed(texts):
            return [[1.0, 0.0] for _ in texts]
        self.embeddings = Mock(embed=AsyncMock(side_effect=embed))
        self.store = Mock()
        self.store.list_documents.return_value = []
        self.service = DocumentService(self.settings, self.embeddings, self.store)
        app.dependency_overrides[get_document_service] = lambda: self.service
        app.dependency_overrides[get_current_user] = lambda: USER_ID
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def upload(self, name, data):
        return self.client.post("/api/documents/upload", files={"file": (name, data, "application/octet-stream")})

    def assert_clean(self):
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_txt_upload_metadata_and_safe_name(self):
        result = self.upload("../../deportes.TXT", "Un torneo ficticio de fútbol. " .encode("utf-8") * 30)
        self.assertEqual(result.status_code, 201, result.text)
        self.assertEqual(result.json()["filename"], "deportes.TXT")
        self.assertEqual(result.json()["status"], "processed")
        chunks = self.store.add.call_args.args[1]
        self.assertGreater(len(chunks), 1)
        for index, chunk in enumerate(chunks):
            self.assertLessEqual(len(chunk.content), 80)
            self.assertEqual(chunk.metadata, {
                "document_id": result.json()["document_id"], "filename": "deportes.TXT",
                "file_type": "txt", "page": None, "chunk_index": index,
            })
        self.assert_clean()

    def test_pdf_preserves_page_numbers(self):
        result = self.upload("reglamento.pdf", pdf_bytes(["", "La carrera ficticia tiene veinte vueltas."]))
        self.assertEqual(result.status_code, 201, result.text)
        chunks = self.store.add.call_args.args[1]
        self.assertTrue(all(chunk.page == 2 and chunk.metadata["page"] == 2 for chunk in chunks))
        self.assert_clean()

    def test_docx_paragraphs_and_tables(self):
        result = self.upload("carrera.docx", docx_bytes())
        self.assertEqual(result.status_code, 201, result.text)
        text = " ".join(chunk.content for chunk in self.store.add.call_args.args[1])
        self.assertIn("Cometa", text)
        self.assertIn("Elena Rayo", text)
        self.assert_clean()

    def test_invalid_files(self):
        for name, data, code in [
            ("video.mp4", b"bytes", 415), ("empty.txt", b"", 422),
            ("blank.txt", b" \n\t", 422), ("binary.txt", b"\x00abc", 422),
            ("encoding.txt", b"\xff", 422), ("fake.pdf", b"not a pdf", 422),
            ("fake.docx", b"not a docx", 422), ("blank.pdf", pdf_bytes([""]), 422),
            ("encrypted.pdf", pdf_bytes(["Sports"], encrypted=True), 422),
        ]:
            with self.subTest(name=name):
                result = self.upload(name, data)
                self.assertEqual(result.status_code, code, result.text)
                self.assert_clean()
        self.store.add.assert_not_called()
        self.embeddings.embed.assert_not_awaited()

    def test_file_size_limit(self):
        self.settings.max_upload_bytes = 5
        self.assertEqual(self.upload("large.txt", b"123456").status_code, 413)
        self.assert_clean()
        self.store.add.assert_not_called()

    def test_extracted_text_limit(self):
        self.settings.max_document_chars = 3
        self.assertEqual(self.upload("large.txt", b"123456").status_code, 413)
        self.assert_clean()

    def test_embedding_failure_cleans_temporary_and_never_writes(self):
        self.embeddings.embed.side_effect = AppError("Ollama no disponible", 503)
        result = self.upload("deporte.txt", b"Un torneo deportivo ficticio.")
        self.assertEqual(result.status_code, 503)
        self.store.add.assert_not_called()
        self.assert_clean()

    def test_database_failure_cleans_temporary(self):
        self.store.add.side_effect = AppError("PostgreSQL no disponible", 503)
        self.assertEqual(self.upload("deporte.txt", b"Un torneo ficticio.").status_code, 503)
        self.assert_clean()

    def test_embeddings_are_batched(self):
        result = self.upload("largo.txt", b"a" * 4000)
        self.assertEqual(result.status_code, 201, result.text)
        self.assertGreater(self.embeddings.embed.await_count, 1)
        self.assertTrue(all(len(call.args[0]) <= 32 for call in self.embeddings.embed.await_args_list))
        self.assert_clean()

    def test_later_embedding_batch_failure_never_writes(self):
        self.embeddings.embed.side_effect = [[[1.0, 0.0]] * 32, AppError("Timeout", 504)]
        result = self.upload("largo.txt", b"a" * 4000)
        self.assertEqual(result.status_code, 504)
        self.assertEqual(self.embeddings.embed.await_count, 2)
        self.store.add.assert_not_called()
        self.assert_clean()

    def test_chunk_count_limit(self):
        self.settings.max_document_chunks = 1
        result = self.upload("largo.txt", b"a" * 400)
        self.assertEqual(result.status_code, 413)
        self.embeddings.embed.assert_not_awaited()
        self.store.add.assert_not_called()
        self.assert_clean()

    def test_list_pagination_and_missing_file(self):
        result = self.client.get("/api/documents?limit=10&offset=20")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), [])
        self.store.list_documents.assert_called_with(10, 20, user_id=USER_ID)
        self.assertEqual(self.client.get("/api/documents?limit=0").status_code, 422)
        self.assertEqual(self.client.post("/api/documents/upload").status_code, 422)

    def test_invalid_chunk_configuration(self):
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, chunk_size=100, chunk_overlap=100)
