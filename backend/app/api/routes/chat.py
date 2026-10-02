from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.rag import RAGRequest, RAGResponse
from app.services.rag_service import RAGService, get_rag_service

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/rag", response_model=RAGResponse)
async def chat_rag(body: RAGRequest, service: Annotated[RAGService, Depends(get_rag_service)]):
    return await service.answer(body.question)
