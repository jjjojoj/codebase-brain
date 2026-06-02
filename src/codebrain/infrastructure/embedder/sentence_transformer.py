"""SentenceTransformer embedder implementation."""

from __future__ import annotations

from typing import Any

from codebrain.config import Settings
from codebrain.core.embedder import Embedder


class SentenceTransformerEmbedder(Embedder):
    """Local SentenceTransformer embedder.

    Uses all-MiniLM-L6-v2 (384-dim) by default, configurable via settings.
    """

    DEFAULT_DIMENSION = 384

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.model_name = self.settings.embedder_model
        self._model: Any | None = None

    def _load_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required for local embeddings. "
                "Install with: pip install -e '.[local]', or set "
                "CODEBRAIN_EMBEDDER_PROVIDER=ollama for an approved local Ollama service."
            ) from exc
        self._model = SentenceTransformer(self.model_name)

    def _ensure_loaded(self) -> None:
        if self._model is None:
            self._load_model()

    def embed(self, text: str) -> list[float]:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not all(isinstance(t, str) for t in texts):
            raise TypeError("texts must be a list of strings")
        self._ensure_loaded()
        if self._model is None:
            raise RuntimeError("Embedding model is not loaded.")
        embeddings = self._model.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True
        )
        return [list(vec) for vec in embeddings.tolist()]

    def dimension(self) -> int:
        if self._model is not None:
            try:
                return self._model.get_embedding_dimension()
            except Exception:
                try:
                    return self._model.get_sentence_embedding_dimension()
                except Exception:
                    pass
        return self.DEFAULT_DIMENSION
