from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TextChunk:
    index: int
    start: int
    end: int
    text: str


def split_text(text: str, chunk_size: int = 1_000, overlap: int = 150) -> list[TextChunk]:
    """Split text into bounded, overlapping character chunks with source offsets.

    The function preserves original character offsets so retrieved passages can
    later be traced back to their source document.
    """
    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    chunks: list[TextChunk] = []
    start = 0
    length = len(text)

    while start < length:
        hard_end = min(start + chunk_size, length)
        end = hard_end

        if hard_end < length:
            boundary = text.rfind(" ", start + chunk_size // 2, hard_end)
            if boundary > start:
                end = boundary

        content = text[start:end].strip()
        if content:
            leading_trim = len(text[start:end]) - len(text[start:end].lstrip())
            trailing_trim = len(text[start:end]) - len(text[start:end].rstrip())
            actual_start = start + leading_trim
            actual_end = end - trailing_trim
            chunks.append(
                TextChunk(
                    index=len(chunks),
                    start=actual_start,
                    end=actual_end,
                    text=text[actual_start:actual_end],
                )
            )

        if end >= length:
            break
        next_start = max(start + 1, end - overlap)
        start = next_start

    return chunks
