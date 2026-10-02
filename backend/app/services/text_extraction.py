"""Extracción local de texto; no realiza OCR ni inventa páginas de DOCX/TXT."""

from dataclasses import dataclass
from zipfile import ZipFile

from docx import Document
from docx.table import Table
from pypdf import PdfReader

from app.core.config import Settings
from app.core.exceptions import AppError
from app.services.file_storage import StoredFile


@dataclass
class TextSection:
    text: str
    page: int | None = None


class TextExtraction:
    def __init__(self, settings: Settings):
        self.settings = settings

    def extract(self, file: StoredFile) -> list[TextSection]:
        try:
            sections = []
            total = 0
            for section in self._read(file):
                if "\x00" in section.text:
                    raise AppError("El archivo contiene texto binario o caracteres nulos.", 422)
                section.text = section.text.strip()
                total += len(section.text)
                if total > self.settings.max_document_chars:
                    raise AppError("El texto extraído supera MAX_DOCUMENT_CHARS.", 413)
                if section.text:
                    sections.append(section)
            if not sections:
                raise AppError("El documento no contiene texto extraíble. Los PDF escaneados requieren OCR, no incluido en esta fase.", 422)
            return sections
        except AppError:
            raise
        except Exception as exc:
            raise AppError("No se pudo extraer el texto. Revisa que el archivo sea válido; TXT debe estar codificado en UTF-8.", 422) from exc

    def _read(self, file):
        if file.file_type == "txt":
            yield TextSection(file.path.read_text(encoding="utf-8-sig"))
        elif file.file_type == "pdf":
            with file.path.open("rb") as stream:
                if not stream.read(5) == b"%PDF-":
                    raise AppError("El archivo no es un PDF válido.", 422)
                stream.seek(0)
                reader = PdfReader(stream)
                if reader.is_encrypted:
                    raise AppError("No se admiten PDF protegidos por contraseña.", 422)
                for number, page in enumerate(reader.pages, start=1):
                    yield TextSection(page.extract_text() or "", number)
        else:
            with ZipFile(file.path) as archive:
                if sum(info.file_size for info in archive.infolist()) > self.settings.max_upload_bytes * 20:
                    raise AppError("El DOCX descomprimido supera el límite permitido.", 413)
            document = Document(file.path)
            for block in document.iter_inner_content():
                if isinstance(block, Table):
                    for row in block.rows:
                        yield TextSection(" | ".join(cell.text for cell in row.cells))
                else:
                    yield TextSection(block.text)
