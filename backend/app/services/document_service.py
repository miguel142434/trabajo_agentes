"""Pipeline de carga: temporal, extracción, chunks, embeddings y persistencia."""

from functools import lru_cache
from uuid import uuid4

from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.schemas.document import DocumentUploadResponse
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.file_storage import FileStorage
from app.services.text_extraction import TextExtraction
from app.vectorstore.postgres import PostgresVectorStore


class DocumentService:
    def __init__(self, settings, embeddings, store):
        self.storage = FileStorage(settings)
        self.extraction = TextExtraction(settings)
        self.chunking = ChunkingService(settings)
        self.embeddings = embeddings
        self.store = store

    async def upload(self, upload, *, user_id=None):
        document_id = uuid4()
        async with self.storage.temporary(upload) as file:
            sections = await run_in_threadpool(self.extraction.extract, file)
            chunks = await run_in_threadpool(
                self.chunking.split, sections, document_id, file.filename, file.file_type,
            )
            vectors = []
            for offset in range(0, len(chunks), 32):
                vectors.extend(await self.embeddings.embed([c.content for c in chunks[offset:offset + 32]]))
            # Un único commit publica tanto el documento como todos sus fragmentos.
            await run_in_threadpool(self.store.add, document_id, chunks, vectors, document={
                "filename": file.filename, "file_type": file.file_type, "size_bytes": file.size_bytes,
            }, user_id=user_id)
            return DocumentUploadResponse(document_id=document_id, filename=file.filename, chunks_created=len(chunks))

    async def list_documents(self, limit, offset, *, user_id=None):
        return await run_in_threadpool(self.store.list_documents, limit, offset, user_id=user_id)


@lru_cache
def get_document_service():
    settings = get_settings()
    return DocumentService(settings, EmbeddingService(settings), PostgresVectorStore(settings))
