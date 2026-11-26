from __future__ import annotations

from io import BytesIO
from zipfile import BadZipFile, ZipFile

import fitz
from docx import Document

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


class DocumentError(ValueError):
    """Raised when an uploaded document cannot be safely processed."""


def extract_text(filename: str, data: bytes) -> str:
    """Extract text from supported document formats without writing uploads to disk."""
    from pathlib import PurePath

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
                return "\n".join(page.get_text() for page in pdf).strip()
        except Exception as exc:
            raise DocumentError("Could not read this PDF.") from exc

    try:
        with ZipFile(BytesIO(data)) as archive:
            if "word/document.xml" not in archive.namelist():
                raise DocumentError("The DOCX file is missing its document content.")
        document = Document(BytesIO(data))
        return "\n".join(p.text for p in document.paragraphs).strip()
    except (BadZipFile, KeyError, OSError) as exc:
        raise DocumentError("Could not read this DOCX file.") from exc
