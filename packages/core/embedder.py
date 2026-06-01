"""Embedding provider strategies for Codebase Brain."""

from __future__ import annotations

from typing import Any, Protocol

from .config import Config


class EmbeddingProvider(Protocol):
    """Common embedding provider interface."""

    def embed(self, text: str) -> list[float]:
        """Embed a single text string."""

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of text strings."""


class SentenceTransformerEmbedder:
    """Local SentenceTransformer embedder using BAAI/bge-m3 by default."""

    DIMENSION = 1024

    def __init__(self, config: Config | None = None) -> None:
        """Load the configured SentenceTransformer model."""
        self.config = config or Config()
        self.model_name = self.config.EMBEDDING_MODEL
        self._model: Any | None = None
        self._load_model()

    def _load_model(self) -> None:
        """Load the local embedding model and raise a helpful error on failure."""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required for local embeddings. "
                "Install project dependencies before using this provider."
            ) from exc

        try:
            self._model = SentenceTransformer(self.model_name)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load embedding model {self.model_name!r}."
            ) from exc

    def embed(self, text: str) -> list[float]:
        """Embed a single text string."""
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of text strings."""
        if self._model is None:
            raise RuntimeError("Embedding model is not loaded.")
        _validate_texts(texts)
        if not texts:
            return []

        try:
            embeddings = self._model.encode(
                texts,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
        except Exception as exc:
            raise RuntimeError("Failed to generate embeddings.") from exc

        return _coerce_vectors(embeddings.tolist(), self.DIMENSION)


class OllamaEmbedder:
    """Local Ollama REST embedder using bge-m3 by default."""

    DIMENSION = 1024

    def __init__(self, config: Config | None = None) -> None:
        """Configure the Ollama embedding endpoint."""
        self.config = config or Config()
        self.model_name = self.config.EMBEDDING_MODEL
        self.host = self.config.OLLAMA_HOST.rstrip("/")

    def embed(self, text: str) -> list[float]:
        """Embed a single text string."""
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of text strings through Ollama."""
        _validate_texts(texts)
        if not texts:
            return []
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
        return _coerce_vectors(embeddings, self.DIMENSION)


class OpenAIEmbedder:
    """OpenAI embedder using text-embedding-3-small with 1024 dimensions."""

    DIMENSION = 1024

    def __init__(self, config: Config | None = None) -> None:
        """Configure the OpenAI embedding client."""
        self.config = config or Config()
        self.model_name = self.config.OPENAI_EMBEDDING_MODEL
        if not self.config.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI embeddings.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "openai is required for the OpenAI embedding provider."
            ) from exc
        self._client = OpenAI(api_key=self.config.OPENAI_API_KEY)

    def embed(self, text: str) -> list[float]:
        """Embed a single text string."""
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of text strings through OpenAI."""
        _validate_texts(texts)
        if not texts:
            return []
        try:
            response = self._client.embeddings.create(
                model=self.model_name,
                input=texts,
                dimensions=self.DIMENSION,
            )
        except Exception as exc:
            raise RuntimeError("Failed to generate embeddings with OpenAI.") from exc

        vectors = [item.embedding for item in response.data]
        return _coerce_vectors(vectors, self.DIMENSION)


class Embedder:
    """Facade that selects the configured embedding provider strategy."""

    DIMENSION = 1024

    def __init__(self, config: Config | None = None) -> None:
        """Create the configured embedding provider."""
        self.config = config or Config()
        self.provider_name = self.config.EMBEDDING_PROVIDER
        self.provider = self._create_provider(self.provider_name)

    def _create_provider(self, provider_name: str) -> EmbeddingProvider:
        """Instantiate an embedding provider by name."""
        if provider_name == "sentence_transformers":
            return SentenceTransformerEmbedder(self.config)
        if provider_name == "ollama":
            return OllamaEmbedder(self.config)
        if provider_name == "openai":
            return OpenAIEmbedder(self.config)
        raise ValueError(
            "EMBEDDING_PROVIDER must be one of: "
            "sentence_transformers, ollama, openai"
        )

    def embed(self, text: str) -> list[float]:
        """Embed a single text string."""
        return self.provider.embed(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of text strings."""
        return self.provider.embed_batch(texts)


def _validate_texts(texts: list[str]) -> None:
    """Validate text batch input."""
    if not isinstance(texts, list) or not all(isinstance(text, str) for text in texts):
        raise TypeError("texts must be a list of strings")


def _coerce_vectors(vectors: list[Any], dimension: int) -> list[list[float]]:
    """Coerce provider output to typed float vectors with expected dimensions."""
    coerced: list[list[float]] = []
    for vector in vectors:
        if len(vector) != dimension:
            raise RuntimeError(
                f"Expected {dimension}-dimensional embeddings, got {len(vector)}."
            )
        coerced.append([float(value) for value in vector])
    return coerced
