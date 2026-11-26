from __future__ import annotations

import json
import math
import sqlite3
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SearchResult:
    document_id: str
    filename: str
    chunk_index: int
    text: str
    score: float


class SQLiteVectorStore:
    """Small local vector store backed by SQLite for a single-user installation."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        if self.database_path == ":memory:":
            raise ValueError("Use a file-backed SQLite database for persistent storage.")
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    UNIQUE(document_id, chunk_index)
                );
                CREATE INDEX IF NOT EXISTS idx_chunks_document_id
                    ON chunks(document_id);
                """
            )

    def add_document(
        self,
        filename: str,
        chunks: Sequence[tuple[str, Sequence[float]]],
    ) -> str:
        if not filename.strip():
            raise ValueError("filename must not be empty")
        if not chunks:
            raise ValueError("at least one chunk is required")
        dimensions = {len(vector) for _, vector in chunks}
        if len(dimensions) != 1 or 0 in dimensions:
            raise ValueError("all embeddings must have the same non-zero dimensions")
        if any(not math.isfinite(float(value)) for _, vector in chunks for value in vector):
            raise ValueError("embeddings must contain only finite numbers")

        document_id = str(uuid.uuid4())
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO documents (id, filename) VALUES (?, ?)",
                (document_id, filename),
            )
            connection.executemany(
                """
                INSERT INTO chunks (id, document_id, chunk_index, content, embedding)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        str(uuid.uuid4()),
                        document_id,
                        index,
                        content,
                        json.dumps([float(value) for value in vector]),
                    )
                    for index, (content, vector) in enumerate(chunks)
                ],
            )
        return document_id

    def search(self, query_embedding: Sequence[float], limit: int = 5) -> list[SearchResult]:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if not query_embedding or any(not math.isfinite(float(v)) for v in query_embedding):
            raise ValueError("query embedding must contain finite values")
        query_norm = math.sqrt(sum(float(value) ** 2 for value in query_embedding))
        if query_norm == 0:
            raise ValueError("query embedding must not be a zero vector")

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT chunks.document_id, documents.filename, chunks.chunk_index,
                       chunks.content, chunks.embedding
                FROM chunks
                JOIN documents ON documents.id = chunks.document_id
                """
            ).fetchall()

        results: list[SearchResult] = []
        for row in rows:
            vector = json.loads(row["embedding"])
            if len(vector) != len(query_embedding):
                continue
            vector_norm = math.sqrt(sum(value * value for value in vector))
            if vector_norm == 0:
                continue
            dot = sum(float(a) * float(b) for a, b in zip(query_embedding, vector, strict=True))
            score = dot / (query_norm * vector_norm)
            results.append(
                SearchResult(
                    document_id=row["document_id"],
                    filename=row["filename"],
                    chunk_index=row["chunk_index"],
                    text=row["content"],
                    score=score,
                )
            )
        return sorted(results, key=lambda item: item.score, reverse=True)[:limit]

    def list_documents(self) -> list[dict[str, str | int]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT documents.id, documents.filename, documents.created_at,
                       COUNT(chunks.id) AS chunk_count
                FROM documents
                LEFT JOIN chunks ON chunks.document_id = documents.id
                GROUP BY documents.id
                ORDER BY documents.created_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_document(self, document_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            return cursor.rowcount > 0
