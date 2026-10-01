"""Configuración centralizada de la aplicación con Pydantic Settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Todas las variables de entorno de la aplicación.

    Pydantic Settings las carga automáticamente desde el proceso y,
    si existe, desde el archivo .env ubicado en la raíz del repositorio.
    """

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
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
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # ------------------------------------------------------------------
    # Ollama / LLM (Fase 2)
    # ------------------------------------------------------------------
    ollama_base_url: HttpUrl = "http://localhost:11434"
    ollama_model: str = Field(default="qwen3:8b", min_length=1)
    ollama_temperature: float = Field(default=0, ge=0, le=2, allow_inf_nan=False)
    ollama_timeout: float = Field(default=120, gt=0, allow_inf_nan=False)

    # Embeddings y PostgreSQL (fase 4).
    ollama_embedding_model: str = Field(default="nomic-embed-text", min_length=1)
    embedding_dimension: int = Field(default=768, ge=1, le=16000)
    postgres_host: str = "localhost"
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_db: str = "ragdb"
    postgres_user: str = "raguser"
    postgres_password: str = Field(default="ragpassword", repr=False)
    database_url: str | None = Field(default=None, repr=False)
    postgres_connect_timeout: int = Field(default=5, ge=1)
    postgres_statement_timeout: int = Field(default=30000, ge=1)
    vector_table: str = Field(default="document_chunks", pattern=r"^[a-z][a-z0-9_]{0,62}$")


@lru_cache
def get_settings() -> Settings:
    """Devuelve la instancia de Settings (singleton por proceso)."""
    return Settings()
