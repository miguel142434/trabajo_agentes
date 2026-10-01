"""Contratos de prueba para almacenar y buscar fragmentos manuales."""

from uuid import UUID
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChunkInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    content: str = Field(min_length=1, max_length=8000)
    filename: str = Field(default="manual.txt", min_length=1, max_length=255)
    page: int | None = Field(default=None, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VectorAddRequest(BaseModel):
    document_id: UUID | None = None
    chunks: list[ChunkInput] = Field(min_length=1, max_length=50)


class VectorAddResponse(BaseModel):
    document_id: UUID
    ids: list[UUID]
    chunks_created: int


class VectorSearchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(min_length=1, max_length=8000)
    k: int = Field(default=4, ge=1, le=50)


class VectorMatch(BaseModel):
    id: UUID
    document_id: UUID
    filename: str
    page: int | None
    chunk_index: int
    content: str
    metadata: dict[str, Any]
    distance: float


class VectorSearchResponse(BaseModel):
    results: list[VectorMatch]
