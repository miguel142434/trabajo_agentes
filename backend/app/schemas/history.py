"""Esquemas Pydantic para el historial de conversaciones."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


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
    title: Optional[str] = Field(default=None, max_length=255)


class ConversationCreate(ConversationBase):
    pass


class ConversationResponse(ConversationBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse] = Field(default_factory=list)


class DocumentHistoryResponse(BaseModel):
    id: str
    user_id: str
    filename: str
    file_type: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

