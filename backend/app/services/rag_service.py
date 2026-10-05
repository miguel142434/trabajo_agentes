"""Fachada compatible con la fase 6; LangGraph ejecuta ahora el flujo RAG."""

from functools import lru_cache

from app.agents.graph import build_graph
from app.core.config import get_settings
from app.schemas.rag import RAGResponse, ChatResponse
from app.services.context_grader import ContextGrader, ContextAnswer
from app.services.interaction_service import InteractionService
from app.services.llm_service import LLMService
from app.services.rag_retriever import RAGRetriever
from app.services.vector_service import get_vector_service


class RAGService:
    def __init__(self, retriever, llm, max_context_chars=6000, *, grader=None, interactions=None, single_pass=False, min_relevance_score=0.65):
        self.retriever = retriever
        self.llm = llm
        self.max_context_chars = max_context_chars
        self.interactions = interactions or InteractionService()
        self.graph = build_graph(retriever, llm, grader or ContextGrader(llm),
                                 self.interactions, max_context_chars,
                                 single_pass=single_pass, min_relevance_score=min_relevance_score)

    async def answer(self, question, user_id=None, conversation_id=None):
        await self.interactions.check_access(user_id, conversation_id)
        state = await self.graph.ainvoke({"question": question, "user_id": user_id, "conversation_id": conversation_id})
        if state["interaction"]["persisted"]:
            return ChatResponse(answer=state["answer"], sources=state["sources"],
                                conversation_id=state["interaction"]["conversation_id"])
        return RAGResponse(answer=state["answer"], sources=state["sources"])


@lru_cache
def get_rag_service():
    settings = get_settings()
    llm = LLMService(settings.model_copy(update={"ollama_temperature": 0}))
    # JSON nativo de Ollama y contexto suficiente para pregunta + fragmentos.
    llm.model.format = ContextAnswer.model_json_schema() if settings.rag_single_pass else "json"
    llm.model.num_ctx = 8192
    llm.model.num_predict = settings.rag_max_output_tokens
    llm.model.keep_alive = settings.rag_keep_alive
    return RAGService(RAGRetriever(get_vector_service(), settings.rag_top_k), llm,
                      settings.rag_max_context_chars, single_pass=settings.rag_single_pass,
                      min_relevance_score=settings.rag_min_relevance_score)

