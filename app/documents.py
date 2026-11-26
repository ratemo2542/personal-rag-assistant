from __future__ import annotations

from io import BytesIO
from pathlib import PurePath
from zipfile import BadZipFile, ZipFile

import fitz
from docx import Document

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_DOCX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_PDF_PAGES = 500


class DocumentError(ValueError):
    """Raised when an uploaded document cannot be safely processed."""


def extract_text(filename: str, data: bytes) -> str:
    """Extract text from supported formats without writing untrusted uploads to disk."""
    suffix = PurePath(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise DocumentError("Unsupported file type. Use PDF, DOCX, TXT, or Markdown.")
    if not data:
        raise DocumentError("The uploaded file is empty.")

    if suffix in {".txt", ".md"}:
        try:
            return data.decode("utf-8-sig").strip()
        except UnicodeDecodeError as exc:
            raise DocumentError("Text files must use UTF-8 encoding.") from exc

    if suffix == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise DocumentError("The file does not appear to be a valid PDF.")
        try:
            with fitz.open(stream=data, filetype="pdf") as pdf:
                if len(pdf) > MAX_PDF_PAGES:
                    raise DocumentError("PDF exceeds the 500-page processing limit.")
                return "\n".join(page.get_text() for page in pdf).strip()
        except DocumentError:
            raise
        except Exception as exc:
            raise DocumentError("Could not read this PDF.") from exc

    try:
        with ZipFile(BytesIO(data)) as archive:
            names = archive.namelist()
            if "word/document.xml" not in names:
                raise DocumentError("The DOCX file is missing its document content.")
            uncompressed_size = sum(info.file_size for info in archive.infolist())
            if uncompressed_size > MAX_DOCX_UNCOMPRESSED_BYTES:
                raise DocumentError("DOCX expands beyond the 50 MB processing limit.")
        document = Document(BytesIO(data))
        return "\n".join(paragraph.text for paragraph in document.paragraphs).strip()
    except DocumentError:
        raise
    except (BadZipFile, KeyError, OSError, ValueError) as exc:
        raise DocumentError("Could not read this DOCX file.") from exc
