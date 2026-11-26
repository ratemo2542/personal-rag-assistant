from __future__ import annotations

import os
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.chunking import split_text
from app.documents import DocumentError, extract_text
from app.embeddings import EmbeddingError, SentenceTransformerEmbedder
from app.generation import GenerationError, OllamaGenerator
from app.storage import SQLiteVectorStore

app = FastAPI(
    title="Personal RAG Assistant API",
    version="0.1.0",
    description="Local-first document ingestion and source-grounded retrieval API.",
)
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
if MAX_UPLOAD_BYTES < 1:
    raise RuntimeError("MAX_UPLOAD_BYTES must be a positive integer.")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/personal_rag.sqlite3")
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
embedder = SentenceTransformerEmbedder(EMBEDDING_MODEL)
generator = OllamaGenerator(OLLAMA_BASE_URL, OLLAMA_MODEL)
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2_000)
    limit: int = Field(default=5, ge=1, le=20)


class AskRequest(SearchRequest):
    pass


def get_store() -> SQLiteVectorStore:
    return SQLiteVectorStore(DATABASE_PATH)


async def read_upload(file: UploadFile) -> tuple[str, bytes]:
    filename = file.filename or ""
    if not filename:
        await file.close()
        raise HTTPException(status_code=400, detail="A filename is required.")
    if len(filename) > 255 or "\x00" in filename:
        await file.close()
        raise HTTPException(status_code=400, detail="Filename is invalid or too long.")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the configured upload limit.")
    return filename, data


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "personal-rag-assistant"}


@app.post("/documents/preview", tags=["documents"])
async def preview_document(file: Annotated[UploadFile, File()]) -> dict[str, str | int]:
    """Extract a bounded document preview; this endpoint does not persist uploads."""
    filename, data = await read_upload(file)
    try:
        extracted = extract_text(filename, data)
    except DocumentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not extracted:
        raise HTTPException(status_code=422, detail="No extractable text was found in this file.")

    return {"filename": filename, "characters": len(extracted), "text": extracted[:20_000]}


@app.post("/documents/ingest", tags=["documents"])
async def ingest_document(file: Annotated[UploadFile, File()]) -> dict[str, str | int]:
    """Extract, chunk, embed, and persist a document in the local SQLite store."""
    filename, data = await read_upload(file)
    try:
        extracted = extract_text(filename, data)
    except DocumentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not extracted:
        raise HTTPException(status_code=422, detail="No extractable text was found in this file.")

    chunks = split_text(extracted)
    try:
        vectors = embedder.embed([chunk.text for chunk in chunks])
    except EmbeddingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if len(vectors) != len(chunks):
        raise HTTPException(status_code=503, detail="Embedding model returned an invalid result.")

    try:
        document_id = get_store().add_document(
            filename,
            [(chunk.text, vector) for chunk, vector in zip(chunks, vectors, strict=True)],
        )
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="Could not persist the document.") from exc

    return {"document_id": document_id, "filename": filename, "chunks": len(chunks)}


@app.post("/search", tags=["retrieval"])
async def search_documents(request: SearchRequest) -> dict[str, list[dict[str, str | int | float]]]:
    """Retrieve the most relevant stored passages; this endpoint does not generate answers."""
    try:
        query_vector = embedder.embed([request.query])[0]
        results = get_store().search(query_vector, limit=request.limit)
    except EmbeddingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (OSError, ValueError, IndexError) as exc:
        raise HTTPException(status_code=400, detail="Could not complete document retrieval.") from exc

    return {
        "results": [
            {
                "document_id": result.document_id,
                "filename": result.filename,
                "chunk_index": result.chunk_index,
                "text": result.text,
                "score": round(result.score, 6),
            }
            for result in results
        ]
    }



@app.post("/ask", tags=["generation"])
async def ask_documents(request: AskRequest) -> dict[str, object]:
    """Answer from retrieved passages and return the exact sources used."""
    try:
        query_vector = embedder.embed([request.query])[0]
        retrieved = get_store().search(query_vector, limit=request.limit)
    except EmbeddingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (OSError, ValueError, IndexError) as exc:
        raise HTTPException(status_code=400, detail="Could not retrieve document context.") from exc

    sources = [
        {
            "document_id": result.document_id,
            "filename": result.filename,
            "chunk_index": result.chunk_index,
            "text": result.text,
            "score": round(result.score, 6),
        }
        for result in retrieved
        if result.score >= 0.2
    ]
    if not sources:
        return {
            "answer": "I couldn't find relevant information in your documents.",
            "sources": [],
        }

    try:
        answer = await generator.answer(request.query, sources)
    except GenerationError as exc:
        raise HTTPException(
            status_code=503,
            detail="Local answer generation is unavailable. Check that Ollama is running and the model is installed.",
        ) from exc

    return {"answer": answer, "sources": sources}
