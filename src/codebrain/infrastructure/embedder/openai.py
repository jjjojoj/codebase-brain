"""OpenAI embedder implementation."""

from __future__ import annotations

from codebrain.config import Settings
from codebrain.core.embedder import Embedder


class OpenAIEmbedder(Embedder):
    """OpenAI embedder using text-embedding-3-small (or configured model)."""

    DEFAULT_DIMENSION = 1536

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.model_name = self.settings.openai_embedding_model
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI embeddings.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "openai is required for the OpenAI embedding provider."
            ) from exc
        self._client = OpenAI(api_key=self.settings.openai_api_key)
        self._dim = None

    def embed(self, text: str) -> list[float]:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not all(isinstance(t, str) for t in texts):
            raise TypeError("texts must be a list of strings")

        try:
            response = self._client.embeddings.create(
                model=self.model_name,
                input=texts,
            )
        except Exception as exc:
            raise RuntimeError("Failed to generate embeddings with OpenAI.") from exc

        vectors = [item.embedding for item in response.data]
        if vectors and not self._dim:
            self._dim = len(vectors[0])
        return vectors

    def dimension(self) -> int:
        if self._dim is not None:
            return self._dim
        return self.DEFAULT_DIMENSION
