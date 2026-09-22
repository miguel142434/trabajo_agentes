"""Configuración de Ollama; el entorno tiene prioridad sobre el .env raíz."""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    ollama_base_url: HttpUrl = "http://localhost:11434"
    ollama_model: str = Field(default="qwen3:8b", min_length=1)
    ollama_temperature: float = Field(default=0, ge=0, le=2, allow_inf_nan=False)
    ollama_timeout: float = Field(default=120, gt=0, allow_inf_nan=False)


@lru_cache
def get_settings() -> Settings:
    values = {**dotenv_values(ENV_FILE, encoding="utf-8-sig"), **os.environ}
    return Settings(**{
        name: values[name.upper()]
        for name in Settings.model_fields
        if values.get(name.upper()) is not None
    })
