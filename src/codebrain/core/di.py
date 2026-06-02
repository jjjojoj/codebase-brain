"""Dependency injection container for CodeBrain."""

from __future__ import annotations

from codebrain.config import Settings
from codebrain.core.embedder import Embedder
from codebrain.core.vector_store import AbstractVectorStore, SqliteVectorStore


class Container:
    """Simple DI container. Lazy-initializes expensive services."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._embedder: Embedder | None = None
        self._vector_store: AbstractVectorStore | None = None

    @property
    def embedder(self) -> Embedder:
        if self._embedder is None:
            self._embedder = self._build_embedder()
        return self._embedder

    @property
    def vector_store(self) -> AbstractVectorStore:
        if self._vector_store is None:
            self._vector_store = self._build_vector_store()
        return self._vector_store

    def _build_embedder(self) -> Embedder:
        provider = self.settings.embedder_provider
        if provider == "sentence-transformers":
            from codebrain.infrastructure.embedder.sentence_transformer import (
                SentenceTransformerEmbedder,
            )
            return SentenceTransformerEmbedder(self.settings)
        if provider == "ollama":
            from codebrain.infrastructure.embedder.ollama import OllamaEmbedder
            return OllamaEmbedder(self.settings)
        raise ValueError(
            f"Unknown local embedder provider: {provider}. "
            "Supported providers: sentence-transformers, ollama."
        )

    def _build_vector_store(self) -> AbstractVectorStore:
        backend = self.settings.vector_store_backend
        if backend == "sqlite":
            # Determine dimension from embedder
            try:
                dim = self.embedder.dimension()
            except Exception:
                dim = 384
            self.settings.ensure_data_dirs()
            return SqliteVectorStore(
                db_path=self.settings.resolved_db_path,
                dimension=dim,
            )
        if backend == "milvus":
            try:
                dim = self.embedder.dimension()
            except Exception:
                dim = 384
            from codebrain.infrastructure.vector_store.milvus import MilvusVectorStore
            return MilvusVectorStore(
                uri=self.settings.milvus_uri,
                token=self.settings.milvus_token,
                collection_prefix=self.settings.milvus_collection_prefix,
                dimension=dim,
            )
        raise ValueError(f"Unknown vector store backend: {backend}")


# Module-level singleton, initialized in server.py
_container: Container | None = None


def init_container(settings: Settings) -> Container:
    global _container
    _container = Container(settings)
    return _container


def get_container() -> Container:
    if _container is None:
        raise RuntimeError("Container not initialized. Call init_container() first.")
    return _container
