"""Endpoints para el historial de conversaciones."""

from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import DBDependency
from app.core.security import get_current_user
from app.models.domain import Conversation, User
from app.schemas.history import ConversationDetailResponse, ConversationResponse, ConversationCreate

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("", response_model=List[ConversationResponse])
async def get_conversations(db: DBDependency, user_id: str = Depends(get_current_user)) -> List[ConversationResponse]:
    """Obtiene la lista de conversaciones del usuario."""
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(conversation_id: str, db: DBDependency, user_id: str = Depends(get_current_user)) -> ConversationDetailResponse:
    """Obtiene el detalle de una conversación junto con sus mensajes."""
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id, Conversation.user_id == user_id)
    )
    result = await db.execute(stmt)
    conv = result.scalar_one_or_none()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")
        
    return conv


@router.post("", response_model=ConversationResponse)
async def create_conversation(data: ConversationCreate, db: DBDependency, user_id: str = Depends(get_current_user)) -> ConversationResponse:
    """Crea una nueva conversación vacía."""
    # Aseguramos que el usuario exista
    user = await db.get(User, user_id)
    if not user:
        user = User(id=user_id, username=user_id)
        db.add(user)
        await db.flush()

    conv = Conversation(
        user_id=user_id,
        title=data.title or "Nueva conversación"
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


