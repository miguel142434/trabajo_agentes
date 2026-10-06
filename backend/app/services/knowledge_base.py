"""Base de conocimiento global precargada desde `backend/knowledge_base/`.

Los archivos de esa carpeta se versionan en el repositorio, de modo que cualquier
persona que ejecute la aplicación obtiene la misma base sin descargarla aparte.
Al arrancar se sincroniza la carpeta con PostgreSQL:

* archivos nuevos o modificados (huella SHA-256) se indexan de nuevo;
* archivos sin cambios y con el mismo modelo de embeddings se omiten;
* documentos globales cuyo archivo se eliminó de la carpeta se borran.

Los documentos que suben los usuarios se suman a esta base: cada búsqueda
combina los fragmentos del usuario con los globales.
"""

import asyncio
import hashlib
import logging
from pathlib import Path

from starlette.concurrency import run_in_threadpool

from app.core.config import Settings
from app.services.document_service import DocumentService
from app.services.file_storage import ALLOWED_SUFFIXES

logger = logging.getLogger(__name__)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


class KnowledgeBaseSeeder:
    def __init__(self, settings: Settings, documents: DocumentService):
        self.settings = settings
        self.documents = documents
        self.store = documents.store

    def files(self) -> list[Path]:
        directory = self.settings.knowledge_base_dir
        if not directory.is_dir():
            return []
        return sorted(
            path for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() in ALLOWED_SUFFIXES
        )

    async def sync(self) -> dict[str, int]:
        """Sincroniza la carpeta con la base de datos y devuelve un resumen."""
        summary = {"indexed": 0, "unchanged": 0, "removed": 0}
        if not self.settings.knowledge_base_dir.is_dir():
            # No se borra nada: una ruta mal configurada no debe vaciar la base global.
            logger.warning("No existe la carpeta de la base global: %s", self.settings.knowledge_base_dir)
            return summary
        files = self.files()
        for path in files:
            content_hash = await run_in_threadpool(file_sha256, path)
            if await run_in_threadpool(self.store.global_document_is_current, path.name, content_hash):
                summary["unchanged"] += 1
                continue
            result = await self.documents.index_global(path, content_hash)
            summary["indexed"] += 1
            logger.info("Base global: %s indexado (%d fragmentos).", path.name, result.chunks_created)
        summary["removed"] = await run_in_threadpool(
            self.store.prune_global_documents, [path.name for path in files],
        )
        return summary

    async def sync_with_retries(self, attempts: int = 5, delay: float = 10) -> None:
        """Ejecuta `sync` tolerando que PostgreSQL u Ollama aún no estén listos."""
        for attempt in range(1, attempts + 1):
            try:
                summary = await self.sync()
                logger.info(
                    "Base de conocimiento global sincronizada: %(indexed)d indexados, "
                    "%(unchanged)d sin cambios, %(removed)d eliminados.", summary,
                )
                return
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - no debe tumbar la aplicación
                logger.warning(
                    "No se pudo sincronizar la base global (intento %d/%d): %s",
                    attempt, attempts, exc,
                )
                if attempt < attempts:
                    await asyncio.sleep(delay * attempt)
        logger.error("La base de conocimiento global no se cargó; se reintentará en el próximo arranque.")
