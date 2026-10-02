from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


REFUSAL = "No tengo suficiente información en mi base de conocimiento para responder esa pregunta."


class RAGRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=2000)


class RAGSource(BaseModel):
    document: str
    page: int | None
    chunk_index: int


class RAGResponse(BaseModel):
    answer: str
    sources: list[RAGSource]


class GroundedAnswer(BaseModel):
    """Salida interna; los números solo pueden referirse al contexto enviado."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    answer: str = Field(min_length=1)
    source_ids: list[Annotated[int, Field(strict=True, ge=1)]]
