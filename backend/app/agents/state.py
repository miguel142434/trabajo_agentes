from typing import TypedDict

from langchain_core.messages import BaseMessage

from app.schemas.rag import RAGSource
from app.schemas.vector import VectorMatch


class AgentState(TypedDict, total=False):
    user_id: str | None
    conversation_id: str | None
    question: str
    retrieved_documents: list[VectorMatch]
    context_score: float
    context_sufficient: bool
    prompt: list[BaseMessage]
    selected_documents: list[VectorMatch]
    answer: str
    sources: list[RAGSource]
    status: str
    interaction: dict
