import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from app.core.config import Settings
from app.services.document_service import DocumentService
from app.services.knowledge_base import KnowledgeBaseSeeder, file_sha256
from tests.document_fixtures import pdf_bytes

REPO_KNOWLEDGE_BASE = Path(__file__).resolve().parents[1] / "knowledge_base"


class KnowledgeBaseSeederTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        with patch.dict(os.environ, {}, clear=True):
            self.settings = Settings(_env_file=None, knowledge_base_dir=self.directory,
                                     upload_dir=self.directory / "uploads", chunk_size=80, chunk_overlap=10)
        async def embed(texts):
            return [[1.0, 0.0] for _ in texts]
        self.embeddings = Mock(embed=AsyncMock(side_effect=embed))
        self.store = Mock()
        self.store.global_document_is_current.return_value = False
        self.store.prune_global_documents.return_value = 0
        self.seeder = KnowledgeBaseSeeder(self.settings, DocumentService(self.settings, self.embeddings, self.store))

    async def test_indexes_supported_files_as_global_and_prunes_the_rest(self):
        (self.directory / "mundiales.pdf").write_bytes(pdf_bytes(["Uruguay gano el primer Mundial en 1930."]))
        (self.directory / "notas.txt").write_text("Brasil tiene cinco titulos mundiales.", encoding="utf-8")
        (self.directory / "README.md").write_text("ignorado", encoding="utf-8")

        summary = await self.seeder.sync()

        self.assertEqual(summary, {"indexed": 2, "unchanged": 0, "removed": 0})
        self.store.add.assert_not_called()
        documents = [call.kwargs["document"] for call in self.store.replace_global_document.call_args_list]
        self.assertEqual([d["filename"] for d in documents], ["mundiales.pdf", "notas.txt"])
        self.assertEqual(documents[0]["content_hash"], file_sha256(self.directory / "mundiales.pdf"))
        pdf_chunks = self.store.replace_global_document.call_args_list[0].args[1]
        self.assertTrue(all(chunk.page == 1 for chunk in pdf_chunks))
        self.store.prune_global_documents.assert_called_once_with(["mundiales.pdf", "notas.txt"])

    async def test_unchanged_files_are_not_reembedded(self):
        (self.directory / "notas.txt").write_text("Brasil tiene cinco titulos mundiales.", encoding="utf-8")
        self.store.global_document_is_current.return_value = True

        summary = await self.seeder.sync()

        self.assertEqual(summary["unchanged"], 1)
        self.embeddings.embed.assert_not_awaited()
        self.store.replace_global_document.assert_not_called()

    async def test_missing_directory_never_deletes_global_documents(self):
        self.settings.knowledge_base_dir = self.directory / "no-existe"
        self.assertEqual(await self.seeder.sync(), {"indexed": 0, "unchanged": 0, "removed": 0})
        self.store.prune_global_documents.assert_not_called()

    async def test_retries_do_not_raise(self):
        (self.directory / "notas.txt").write_text("texto", encoding="utf-8")
        self.store.global_document_is_current.side_effect = RuntimeError("PostgreSQL caido")
        with patch("app.services.knowledge_base.asyncio.sleep", new=AsyncMock()) as sleep:
            await self.seeder.sync_with_retries(attempts=3, delay=0)
        self.assertEqual(self.store.global_document_is_current.call_count, 3)
        self.assertEqual(sleep.await_count, 2)


class RepositoryKnowledgeBaseTests(unittest.TestCase):
    def test_default_directory_ships_with_the_world_cup_document(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None)
        self.assertEqual(settings.knowledge_base_dir, REPO_KNOWLEDGE_BASE)
        self.assertTrue((REPO_KNOWLEDGE_BASE / "Mundiales_documento_RAG.pdf").is_file())
