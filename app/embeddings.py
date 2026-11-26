from __future__ import annotations

from collections.abc import Sequence


class EmbeddingError(RuntimeError):
    """Raised when the configured embedding model cannot create vectors."""


class SentenceTransformerEmbedder:
    """Lazy local embedding adapter; model weights are downloaded on first use."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise EmbeddingError(
                    "Install the optional local embedding dependencies with "
                    "pip install -e .[embeddings]."
                ) from exc
            try:
                self._model = SentenceTransformer(self.model_name)
            except Exception as exc:
                raise EmbeddingError("The local embedding model could not be loaded.") from exc
        return self._model

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts or any(not text.strip() for text in texts):
            raise ValueError("texts must contain non-empty strings")
        model = self._load_model()
        try:
            vectors = model.encode(list(texts), normalize_embeddings=True)
            return [[float(value) for value in vector] for vector in vectors]
        except Exception as exc:
            raise EmbeddingError("The embedding model failed to encode the text.") from exc
