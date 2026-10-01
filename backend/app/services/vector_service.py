"""Orquesta embeddings y almacenamiento sin lógica HTTP en las rutas."""

import asyncio
from functools import lru_cache
from uuid import uuid4

from app.core.config import get_settings
from app.schemas.vector import VectorAddResponse, VectorSearchResponse
from app.services.embedding_service import EmbeddingService
from app.vectorstore.postgres import PostgresVectorStore


class VectorService:
    def __init__(self, embeddings, store):
        self.embeddings = embeddings
        self.store = store

    async def add(self, request):
        vectors = await self.embeddings.embed([chunk.content for chunk in request.chunks])
        document_id = request.document_id or uuid4()
        # Ejecutar cada transacción fuera del event loop también funciona en Windows.
        ids = await asyncio.to_thread(self.store.add, document_id, request.chunks, vectors)
        return VectorAddResponse(document_id=document_id, ids=ids, chunks_created=len(ids))

    async def search(self, request):
        vectors = await self.embeddings.embed([request.query], query=True)
        results = await asyncio.to_thread(self.store.search, vectors[0], request.k)
        return VectorSearchResponse(results=results)


@lru_cache
def get_vector_service():
    settings = get_settings()
    return VectorService(EmbeddingService(settings), PostgresVectorStore(settings))
