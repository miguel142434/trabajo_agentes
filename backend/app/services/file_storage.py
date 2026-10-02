"""Archivos temporales con nombre interno independiente del nombre del usuario."""

from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import Settings
from app.core.exceptions import AppError


@dataclass
class StoredFile:
    path: Path
    filename: str
    file_type: str
    size_bytes: int


class FileStorage:
    def __init__(self, settings: Settings):
        self.settings = settings

    @asynccontextmanager
    async def temporary(self, upload: UploadFile):
        filename = (upload.filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
        if not filename or len(filename) > 255 or any(ord(c) < 32 for c in filename):
            raise AppError("Nombre de archivo no válido.", 422)
        suffix = Path(filename).suffix.lower()
        if suffix not in {".pdf", ".txt", ".docx"}:
            raise AppError("Formato no permitido. Usa PDF, TXT o DOCX.", 415)
        if upload.size is not None and upload.size > self.settings.max_upload_bytes:
            raise AppError("El archivo supera MAX_UPLOAD_BYTES.", 413)
        self.settings.upload_dir.mkdir(parents=True, exist_ok=True)
        path = self.settings.upload_dir / (uuid4().hex + suffix)
        size = 0
        try:
            with path.open("xb") as target:
                while block := await upload.read(1024 * 1024):
                    size += len(block)
                    if size > self.settings.max_upload_bytes:
                        raise AppError("El archivo supera MAX_UPLOAD_BYTES.", 413)
                    target.write(block)
            if size == 0:
                raise AppError("El archivo está vacío.", 422)
            yield StoredFile(path, filename, suffix[1:], size)
        finally:
            path.unlink(missing_ok=True)
