from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.schemas.document import DocumentInfo, DocumentUploadResponse
from app.services.document_service import DocumentService, get_document_service

router = APIRouter(prefix="/documents", tags=["Documents"])
Service = Annotated[DocumentService, Depends(get_document_service)]


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(service: Service, file: UploadFile = File(...)):
    return await service.upload(file)


@router.get("", response_model=list[DocumentInfo])
async def list_documents(service: Service, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    return await service.list_documents(limit, offset)
