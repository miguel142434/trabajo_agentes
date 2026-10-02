from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import Settings
from app.core.exceptions import AppError
from app.schemas.vector import ChunkInput


class ChunkingService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap,
            length_function=len,
        )

    def split(self, sections, document_id, filename, file_type):
        # DOCX conserva párrafos/tablas en orden; PDF conserva límites de página.
        if file_type != "pdf":
            from app.services.text_extraction import TextSection
            sections = [TextSection("\n\n".join(section.text for section in sections))]
        chunks = []
        for section in sections:
            for text in self.splitter.split_text(section.text):
                if not text.strip():
                    continue
                index = len(chunks)
                if index >= self.settings.max_document_chunks:
                    raise AppError("El documento supera MAX_DOCUMENT_CHUNKS.", 413)
                chunks.append(ChunkInput(content=text, filename=filename, page=section.page, metadata={
                    "document_id": str(document_id), "filename": filename,
                    "file_type": file_type, "page": section.page, "chunk_index": index,
                }))
        if not chunks:
            raise AppError("No se pudieron generar fragmentos de texto.", 422)
        return chunks
