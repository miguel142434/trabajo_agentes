"""Generación asíncrona con Ollama, independiente de HTTP/FastAPI."""

import asyncio
import logging
from time import perf_counter
from functools import lru_cache

import httpx
from langchain_ollama import ChatOllama
from langchain_core.messages import BaseMessage
from ollama import ResponseError

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Error controlado del proveedor del modelo."""


class LLMUnavailableError(LLMError):
    pass


class LLMModelNotFoundError(LLMError):
    pass


class LLMTimeoutError(LLMError):
    pass


class LLMService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = ChatOllama(
            base_url=str(settings.ollama_base_url),
            model=settings.ollama_model,
            temperature=settings.ollama_temperature,
            # Qwen3 devuelve directamente la respuesta en este endpoint de prueba.
            reasoning=False,
            client_kwargs={"timeout": settings.ollama_timeout},
        )

    async def generate(self, prompt: str | list[BaseMessage]) -> str:
        started = perf_counter()
        try:
            # También limita la duración total si Ollama sigue enviando tokens.
            async with asyncio.timeout(self.settings.ollama_timeout):
                message = await self.model.ainvoke(prompt)
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise LLMTimeoutError("Ollama excedió el tiempo de espera configurado.") from exc
        except (ConnectionError, httpx.ConnectError) as exc:
            raise LLMUnavailableError(
                "No se pudo conectar con Ollama. Verifica que esté ejecutándose y OLLAMA_BASE_URL."
            ) from exc
        except ResponseError as exc:
            if exc.status_code == 404:
                raise LLMModelNotFoundError(
                    f"El modelo '{self.settings.ollama_model}' no está disponible. "
                    f"Descárgalo con: ollama pull {self.settings.ollama_model}"
                ) from exc
            raise LLMError("Ollama no pudo generar la respuesta.") from exc
        except httpx.RequestError as exc:
            raise LLMUnavailableError("Se interrumpió la comunicación con Ollama.") from exc

        if message.response_metadata.get("done_reason") == "length":
            raise LLMError("El modelo alcanzó el límite de salida. Aumenta RAG_MAX_OUTPUT_TOKENS para preguntas extensas.")
        if not isinstance(message.content, str) or not message.content.strip():
            raise LLMError("Ollama devolvió una respuesta vacía o no válida.")
        metrics = message.response_metadata
        logger.info(
            "LLM model=%s elapsed=%.2fs load=%.2fs prompt_eval=%.2fs generation=%.2fs input_tokens=%s output_tokens=%s",
            self.settings.ollama_model, perf_counter() - started,
            (metrics.get("load_duration") or 0) / 1e9,
            (metrics.get("prompt_eval_duration") or 0) / 1e9,
            (metrics.get("eval_duration") or 0) / 1e9,
            metrics.get("prompt_eval_count"), metrics.get("eval_count"),
        )
        return message.content


@lru_cache
def get_llm_service() -> LLMService:
    return LLMService(get_settings())
