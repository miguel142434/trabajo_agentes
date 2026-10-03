"""Esquemas Pydantic para el historial de conversaciones."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class MessageBase(BaseModel):
    role: str
    content: str
    sources: Optional[str] = None


class MessageResponse(MessageBase):
    id: str
    conversation_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationBase(BaseModel):
    title: Optional[str] = None


class ConversationCreate(ConversationBase):
    pass


class ConversationResponse(ConversationBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse] = []


class DocumentHistoryResponse(BaseModel):
    id: str
    user_id: str
    filename: str
    file_type: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

