"""Embeddings locales; valida dimensiones y errores antes de persistir."""

import asyncio
import math

import httpx
from langchain_ollama import OllamaEmbeddings
from ollama import ResponseError

from app.core.config import Settings
from app.core.exceptions import AppError


class EmbeddingService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = OllamaEmbeddings(
            model=settings.ollama_embedding_model,
            base_url=str(settings.ollama_base_url),
            client_kwargs={"timeout": settings.ollama_timeout},
        )

    async def embed(self, texts: list[str], *, query: bool = False) -> list[list[float]]:
        # Nomic requiere distinguir consultas y documentos durante la recuperación.
        if self.settings.ollama_embedding_model.split(":")[0] == "nomic-embed-text":
            prefix = "search_query: " if query else "search_document: "
            texts = [prefix + text for text in texts]
        try:
            async with asyncio.timeout(self.settings.ollama_timeout):
                vectors = await self.model.aembed_documents(texts)
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise AppError("Ollama excedió el tiempo de espera al generar embeddings.", 504) from exc
        except (ConnectionError, httpx.RequestError) as exc:
            raise AppError("No se pudo comunicar con Ollama para generar embeddings.", 503) from exc
        except ResponseError as exc:
            if exc.status_code == 404:
                raise AppError(
                    f"Modelo de embeddings no disponible. Ejecuta: ollama pull {self.settings.ollama_embedding_model}",
                    503,
                ) from exc
            raise AppError("Ollama no pudo generar los embeddings.", 502) from exc

        if len(vectors) != len(texts):
            raise AppError("Ollama devolvió una cantidad de embeddings incorrecta.", 502)
        for vector in vectors:
            if len(vector) != self.settings.embedding_dimension:
                raise AppError("La dimensión del modelo no coincide con EMBEDDING_DIMENSION.", 409)
            if not all(math.isfinite(value) for value in vector) or not any(vector):
                raise AppError("Ollama devolvió un vector vacío, nulo o no finito.", 502)
        return vectors
