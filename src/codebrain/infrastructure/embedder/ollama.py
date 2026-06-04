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
        self.batch_size = self.settings.ollama_batch_size

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

        results: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start:start + self.batch_size]
            try:
                response = httpx.post(
                    f"{self.host}/api/embed",
                    json={"model": self.model_name, "input": batch},
                    timeout=120.0,
                )
                response.raise_for_status()
                payload = response.json()
            except Exception as exc:
                raise RuntimeError("Failed to generate embeddings with Ollama.") from exc

            if not isinstance(payload, dict):
                raise RuntimeError("Ollama response was not a JSON object.")
            embeddings = payload.get("embeddings")
            if not isinstance(embeddings, list):
                raise RuntimeError("Ollama response did not include embeddings.")
            if len(embeddings) != len(batch):
                raise RuntimeError(
                    "Ollama response embedding count did not match the input batch."
                )
            results.extend([[float(v) for v in vec] for vec in embeddings])
        return results

    def dimension(self) -> int:
        return self.DEFAULT_DIMENSION
