from uuid import uuid4

USER_ID = '00000000-0000-0000-0000-000000000001'
CONVERSATION_ID = '00000000-0000-0000-0000-000000000002'


class MemoryInteractions:
    """Doble de prueba explícito; nunca se usa en producción."""
    def __init__(self, persisted=False):
        self.persisted = persisted

    async def check_access(self, user_id, conversation_id):
        pass

    async def save(self, state):
        return {"user_id": state.get("user_id"), "conversation_id": state.get("conversation_id") or (
                    CONVERSATION_ID if self.persisted else None),
                "question": state["question"], "answer": state["answer"],
                "sources": state.get("sources", []), "status": state["status"], "persisted": self.persisted}
