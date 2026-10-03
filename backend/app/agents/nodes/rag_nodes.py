"""Nodos con dependencias inyectadas; cada uno devuelve cambios al AgentState."""

import logging
from time import perf_counter

from pydantic import ValidationError

from app.agents.state import AgentState
from app.core.exceptions import AppError
from app.schemas.rag import GroundedAnswer, RAGRequest, REFUSAL
from app.services.llm_service import LLMError
from app.services.rag_prompt import build_prompt
from app.services.rag_sources import format_sources

logger = logging.getLogger(__name__)


class RAGNodes:
    def __init__(self, retriever, llm, grader, interactions, max_context_chars, *, single_pass=False):
        self.retriever = retriever
        self.llm = llm
        self.grader = grader
        self.interactions = interactions
        self.max_context_chars = max_context_chars
        self.single_pass = single_pass

    def receive_question(self, state: AgentState):
        # Reiniciar los datos derivados: no compartir respuestas entre consultas.
        return {"user_id": state.get("user_id"), "conversation_id": state.get("conversation_id"),
                "retrieved_documents": [], "context_score": 0.0, "context_sufficient": False,
                "answer": "", "sources": [], "selected_documents": [], "prompt": [],
                "interaction": {}, "prepared_answer": None, "status": "received"}

    def validate_question(self, state: AgentState):
        try:
            question = RAGRequest(question=state.get("question", "")).question
        except ValidationError as exc:
            raise AppError("La pregunta debe contener entre 1 y 2000 caracteres.", 422) from exc
        return {"question": question, "status": "validated"}

    async def retrieve_context(self, state: AgentState):
        started = perf_counter()
        documents = await self.retriever.retrieve(state["question"])
        logger.info("retrieve_context: %s fragmentos, elapsed=%.2fs", len(documents), perf_counter() - started)
        return {"retrieved_documents": documents, "status": "retrieved"}

    async def grade_context(self, state: AgentState):
        started = perf_counter()
        prompt, selected = build_prompt(state["question"], state["retrieved_documents"], self.max_context_chars)
        # Evaluar exactamente el contexto limitado que recibirá el generador.
        prepared = None
        sufficient = False
        if selected and self.single_pass:
            result = await self.grader.grade_with_answer(prompt)
            sufficient = result.sufficient and result.answer != REFUSAL and bool(result.source_ids)
            if sufficient:
                prepared = result.model_dump(exclude={"sufficient"})
        elif selected:
            sufficient = await self.grader.grade(prompt)
        score = max((1.0 - doc.distance for doc in selected), default=0.0)
        logger.info("grade_context: sufficient=%s, context_score=%.4f, single_pass=%s, elapsed=%.2fs",
                    sufficient, score, self.single_pass, perf_counter() - started)
        return {"prompt": prompt, "selected_documents": selected, "context_score": score,
                "context_sufficient": sufficient, "prepared_answer": prepared, "status": "graded"}

    async def generate_answer(self, state: AgentState):
        logger.info("Ruta del agente: generate_answer")
        try:
            if state.get("prepared_answer") is not None:
                # Reutilización exclusiva de esta petición; no es caché entre usuarios.
                generated = GroundedAnswer.model_validate(state["prepared_answer"])
            else:
                raw = await self.llm.generate(state["prompt"])
                generated = GroundedAnswer.model_validate_json(raw)
        except ValidationError as exc:
            raise LLMError("El modelo no devolvió una respuesta RAG con formato válido.") from exc
        if generated.answer == REFUSAL or not generated.source_ids:
            return {"status": "needs_rejection"}
        return {"answer": generated.answer,
                "sources": format_sources(generated.source_ids, state["selected_documents"]),
                "status": "answered"}

    def reject_question(self, state: AgentState):
        logger.info("Ruta del agente: reject_question")
        return {"answer": REFUSAL, "sources": [], "status": "rejected"}

    async def save_interaction(self, state: AgentState):
        interaction = await self.interactions.save(state)
        logger.info("save_interaction: status=%s, persisted=%s", state["status"], interaction["persisted"])
        return {"interaction": interaction}
