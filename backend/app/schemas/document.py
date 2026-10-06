from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    filename: str
    chunks_created: int
    status: Literal["processed"] = "processed"


class DocumentInfo(DocumentUploadResponse):
    file_type: str
    size_bytes: int
    created_at: datetime
    embedding_model: str
    # True para la base de conocimiento global, compartida por todos los usuarios.
    is_global: bool = False
