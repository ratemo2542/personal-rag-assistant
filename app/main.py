from __future__ import annotations

import os

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.documents import DocumentError, extract_text

app = FastAPI(
    title="Personal RAG Assistant API",
    version="0.1.0",
    description="Local-first document ingestion foundation for a source-grounded assistant.",
)
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "personal-rag-assistant"}


@app.post("/documents/preview", tags=["documents"])
async def preview_document(file: UploadFile = File(...)) -> dict[str, str | int]:
    """Extract a bounded document preview; this endpoint does not persist uploads."""
    filename = file.filename or ""
    if not filename:
        raise HTTPException(status_code=400, detail="A filename is required.")

    data = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the configured upload limit.")

    try:
        extracted = extract_text(filename, data)
    except DocumentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not extracted:
        raise HTTPException(status_code=422, detail="No extractable text was found in this file.")

    return {"filename": filename, "characters": len(extracted), "text": extracted[:20_000]}
