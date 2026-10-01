"""Configuración centralizada de la aplicación con Pydantic Settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Todas las variables de entorno de la aplicación.

    Pydantic Settings las carga automáticamente desde el proceso y,
    si existe, desde el archivo .env ubicado en la raíz del repositorio.
    """

    model_config = SettingsConfigDict(
        env_file="../.env",       # relativo al directorio de trabajo (backend/)
        env_file_encoding="utf-8-sig",
        case_sensitive=False,
        extra="ignore",
        str_strip_whitespace=True,
    )

    # ------------------------------------------------------------------
    # Aplicación
    # ------------------------------------------------------------------
    app_title: str = "RAG Agent API"
    app_version: str = "0.2.0"
    log_level: str = Field(default="INFO", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    cors_origins: list[str] = ["http://localhost:5173"]

    # ------------------------------------------------------------------
    # Ollama / LLM (Fase 2)
    # ------------------------------------------------------------------
    ollama_base_url: HttpUrl = "http://localhost:11434"
    ollama_model: str = Field(default="qwen3:8b", min_length=1)
    ollama_temperature: float = Field(default=0, ge=0, le=2)
    ollama_timeout: float = Field(default=120, gt=0)


@lru_cache
def get_settings() -> Settings:
    """Devuelve la instancia de Settings (singleton por proceso)."""
    return Settings()
