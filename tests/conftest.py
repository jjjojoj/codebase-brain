"""Shared test fixtures for CodeBrain."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from codebrain.config import Settings
from codebrain.core.di import Container, init_container
from codebrain.core.embedder import Embedder
from codebrain.core.repository import Repository
from codebrain.core.vector_store import SqliteVectorStore


# ----------------------------------------------------------------- Fixtures


@pytest.fixture
def temp_db_path() -> str:
    """Temporary SQLite DB path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def test_settings(temp_db_path: str) -> Settings:
    """Settings pointing at a temp DB."""
    return Settings(
        db_path=temp_db_path,
        embedder_provider="sentence-transformers",
        embedder_model="all-MiniLM-L6-v2",
    )


@pytest.fixture
def mock_embedder() -> Embedder:
    """Fake embedder that returns fixed-dimension random vectors."""

    class FakeEmbedder(Embedder):
        def embed(self, text: str) -> list[float]:
            import hashlib
            h = hashlib.sha256(text.encode()).digest()
            return [float(b) / 255.0 for b in h[:32]]  # 32-dim for speed

        def embed_batch(self, texts: list[str]) -> list[list[float]]:
            return [self.embed(t) for t in texts]

        def dimension(self) -> int:
            return 32

    return FakeEmbedder()


@pytest.fixture
def sqlite_store(temp_db_path: str) -> SqliteVectorStore:
    """SQLite vector store for testing."""
    store = SqliteVectorStore(db_path=temp_db_path, dimension=32)
    yield store
    store.close()


@pytest.fixture
def repository(sqlite_store: SqliteVectorStore, mock_embedder: Embedder) -> Repository:
    """Repository wired to SQLite store and mock embedder."""
    return Repository(sqlite_store, mock_embedder)


@pytest.fixture
def container(test_settings: Settings) -> Container:
    """Initialized DI container for testing."""
    return init_container(test_settings)
