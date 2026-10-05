"""Endpoints para el historial de conversaciones."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import DBDependency
from app.core.security import get_current_user
from app.models.domain import Conversation
from app.services.interaction_service import ensure_user
from app.schemas.history import ConversationDetailResponse, ConversationResponse, ConversationCreate

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("", response_model=List[ConversationResponse])
async def get_conversations(db: DBDependency, user_id: str = Depends(get_current_user),
                            limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)) -> List[ConversationResponse]:
    """Obtiene la lista de conversaciones del usuario."""
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .limit(limit).offset(offset)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(conversation_id: UUID, db: DBDependency, user_id: str = Depends(get_current_user)) -> ConversationDetailResponse:
    """Obtiene el detalle de una conversación junto con sus mensajes."""
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == str(conversation_id), Conversation.user_id == user_id)
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
    await ensure_user(db, user_id)

    conv = Conversation(
        user_id=user_id,
        title=data.title or "Nueva conversación"
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


