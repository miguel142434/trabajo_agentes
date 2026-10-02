from app.schemas.rag import RAGSource
from app.services.llm_service import LLMError


def format_sources(source_ids, matches):
    sources = []
    seen = set()
    for number in source_ids:
        if number > len(matches):
            raise LLMError("El modelo devolvió una referencia que no pertenece al contexto.")
        if number in seen:
            continue
        seen.add(number)
        match = matches[number - 1]
        sources.append(RAGSource(document=match.filename, page=match.page, chunk_index=match.chunk_index))
    return sources
