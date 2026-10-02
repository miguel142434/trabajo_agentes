"""Fachada compatible con la fase 6; LangGraph ejecuta ahora el flujo RAG."""

from functools import lru_cache

from app.agents.graph import build_graph
from app.core.config import get_settings
from app.schemas.rag import RAGResponse
from app.services.context_grader import ContextGrader
from app.services.interaction_service import InteractionService
from app.services.llm_service import LLMService
from app.services.rag_retriever import RAGRetriever
from app.services.vector_service import get_vector_service


class RAGService:
    def __init__(self, retriever, llm, max_context_chars=6000, *, grader=None, interactions=None):
        self.retriever = retriever
        self.llm = llm
        self.max_context_chars = max_context_chars
        self.graph = build_graph(retriever, llm, grader or ContextGrader(llm),
                                 interactions or InteractionService(), max_context_chars)

    async def answer(self, question):
        state = await self.graph.ainvoke({"question": question, "user_id": None, "conversation_id": None})
        return RAGResponse(answer=state["answer"], sources=state["sources"])


@lru_cache
def get_rag_service():
    settings = get_settings()
    llm = LLMService(settings.model_copy(update={"ollama_temperature": 0}))
    # JSON nativo de Ollama y contexto suficiente para pregunta + fragmentos.
    llm.model.format = "json"
    llm.model.num_ctx = 8192
    return RAGService(RAGRetriever(get_vector_service(), settings.rag_top_k), llm, settings.rag_max_context_chars)
