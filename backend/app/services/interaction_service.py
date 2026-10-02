"""Registro limitado a la ejecución actual. Persistencia relacional: fase 9."""

from datetime import datetime, timezone


class InteractionService:
    async def save(self, state):
        return {
            "user_id": state["user_id"],
            "conversation_id": state["conversation_id"],
            "question": state["question"],
            "answer": state["answer"],
            "sources": [source.model_dump() for source in state["sources"]],
            "status": state["status"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "persisted": False,
        }
