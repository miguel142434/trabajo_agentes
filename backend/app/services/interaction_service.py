"""Registro de interacciones."""

import json
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.domain import Conversation, Message, User


class InteractionService:
    async def save(self, state):
        user_id = state.get("user_id") or "anonymous"
        conversation_id = state.get("conversation_id")
        question = state.get("question")
        answer = state.get("answer")
        sources = [source.model_dump() for source in state.get("sources", [])]
        
        async with AsyncSessionLocal() as session:
            # Validar existencia de usuario
            user = await session.get(User, user_id)
            if not user:
                user = User(id=user_id, username=user_id)
                session.add(user)
                await session.commit()
            
            # Validar o crear conversación
            if conversation_id:
                conv = await session.get(Conversation, conversation_id)
                if not conv:
                    conv = Conversation(id=conversation_id, user_id=user_id, title=question[:50])
                    session.add(conv)
                    await session.commit()
            else:
                conv = Conversation(user_id=user_id, title=question[:50])
                session.add(conv)
                await session.commit()
                conversation_id = conv.id
                
            # Persistir mensaje del usuario
            msg_user = Message(
                conversation_id=conversation_id,
                role="user",
                content=question
            )
            session.add(msg_user)
            
            # Persistir respuesta del asistente
            msg_assistant = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=answer,
                sources=json.dumps(sources)
            )
            session.add(msg_assistant)
            
            await session.commit()

        return {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "question": question,
            "answer": answer,
            "sources": sources,
            "status": state.get("status"),
            "persisted": True,
        }

