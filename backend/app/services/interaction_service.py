"""Historial transaccional y verificación de propietario."""
import json
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.core.database import AsyncSessionLocal
from app.core.exceptions import AppError
from app.models.domain import Conversation, Message, User, get_utc_now

async def ensure_user(session, user_id):
    await session.execute(insert(User).values(id=user_id, username=user_id)
                          .on_conflict_do_nothing(index_elements=[User.id]))

class InteractionService:
    def __init__(self, sessions=AsyncSessionLocal):
        self.sessions = sessions

    async def check_access(self, user_id, conversation_id):
        if not user_id:
            raise AppError("Se requiere un usuario autenticado.", 401)
        if conversation_id:
            async with self.sessions() as session:
                conv = await session.scalar(select(Conversation.id).where(
                    Conversation.id == conversation_id, Conversation.user_id == user_id))
                if conv is None:
                    raise AppError("Conversación no encontrada.", 404)

    async def save(self, state):
        user_id = state.get("user_id")
        if not user_id:
            raise AppError("Se requiere un usuario autenticado.", 401)
        conversation_id = state.get("conversation_id")
        sources = [source.model_dump() for source in state.get("sources", [])]
        async with self.sessions() as session, session.begin():
            await ensure_user(session, user_id)
            if conversation_id:
                conv = await session.scalar(select(Conversation).where(
                    Conversation.id == conversation_id, Conversation.user_id == user_id).with_for_update())
                if conv is None:
                    raise AppError("Conversación no encontrada.", 404)
            else:
                conv = Conversation(user_id=user_id, title=state["question"][:50])
                session.add(conv)
                await session.flush()
                conversation_id = conv.id
            session.add_all([
                Message(conversation_id=conversation_id, role="user", content=state["question"]),
                Message(conversation_id=conversation_id, role="assistant", content=state["answer"],
                        sources=json.dumps(sources, ensure_ascii=False)),
            ])
            conv.updated_at = get_utc_now()
        return {"user_id": user_id, "conversation_id": conversation_id,
                "question": state["question"], "answer": state["answer"], "sources": sources,
                "status": state.get("status"), "persisted": True}
