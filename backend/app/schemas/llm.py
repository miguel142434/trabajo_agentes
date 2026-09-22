"""Contrato del endpoint de prueba del LLM."""

from pydantic import BaseModel, ConfigDict, Field


class LLMRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    prompt: str = Field(min_length=1, max_length=16000)


class LLMResponse(BaseModel):
    response: str
