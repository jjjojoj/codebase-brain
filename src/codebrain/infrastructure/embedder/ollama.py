"""Ollama embedder implementation."""

from __future__ import annotations

from codebrain.config import Settings
from codebrain.core.embedder import Embedder


class OllamaEmbedder(Embedder):
    """Ollama REST embedder."""

    DEFAULT_DIMENSION = 1024

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.model_name = self.settings.embedder_model
        self.host = self.settings.ollama_url.rstrip("/")

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
            import httpx
        except ImportError as exc:
            raise RuntimeError(
                "httpx is required for the Ollama embedding provider."
            ) from exc

        try:
            response = httpx.post(
                f"{self.host}/api/embed",
                json={"model": self.model_name, "input": texts},
                timeout=120.0,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise RuntimeError("Failed to generate embeddings with Ollama.") from exc

        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list):
            raise RuntimeError("Ollama response did not include embeddings.")
        return [[float(v) for v in vec] for vec in embeddings]

    def dimension(self) -> int:
        return self.DEFAULT_DIMENSION
