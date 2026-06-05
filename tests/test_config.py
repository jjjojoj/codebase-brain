"""Tests for config module."""

import pytest

from codebrain.config import Settings
from codebrain.core.di import Container


def test_settings_defaults(monkeypatch) -> None:
    """Settings should have sensible defaults."""
    for name in (
        "CODEBRAIN_EMBEDDER_PROVIDER",
        "CODEBRAIN_EMBEDDER_DEVICE",
        "CODEBRAIN_OLLAMA_BATCH_SIZE",
        "CODEBRAIN_CODEBASE_MEMORY_SEARCH_TIMEOUT_SEC",
        "CODEBRAIN_CODEBASE_MEMORY_REPO_ALIASES",
        "CODEBRAIN_VECTOR_STORE_BACKEND",
        "CODEBRAIN_CONVENTIONS_ENABLED",
        "CODEBRAIN_SESSION_MEMORY_ENABLED",
        "CODEBRAIN_HISTORY_ENABLED",
        "CODEBRAIN_GIT_HISTORY_INDEX_ENABLED",
        "CODEBRAIN_DEFAULT_CONVENTIONS_PATH",
        "CODEBRAIN_MILVUS_URI",
        "CODEBRAIN_MILVUS_COLLECTION_PREFIX",
    ):
        monkeypatch.delenv(name, raising=False)

    s = Settings(_env_file=None)
    assert s.embedder_provider == "sentence-transformers"
    assert s.embedder_device == "cpu"
    assert s.ollama_batch_size == 32
    assert s.codebase_memory_search_timeout_sec == 15
    assert s.codebase_memory_repo_aliases == ""
    assert s.vector_store_backend == "sqlite"
    assert s.conventions_enabled is True
    assert s.session_memory_enabled is True
    assert s.history_enabled is True
    assert s.git_history_index_enabled is False
    assert s.default_conventions_path == ".codebrain/conventions"
    assert s.milvus_uri == ".codebrain/milvus_lite.db"
    assert s.milvus_collection_prefix == "codebrain"


def test_settings_env_prefix() -> None:
    """Settings should use CODEBRAIN_ prefix for env vars."""
    s = Settings()
    assert s.model_config["env_prefix"] == "CODEBRAIN_"


def test_settings_resolved_db_path() -> None:
    """resolved_db_path should expand user and resolve."""
    s = Settings(db_path=".codebrain/test.db")
    p = s.resolved_db_path
    assert p.name == "test.db"
    assert ".codebrain" in str(p)


def test_settings_custom_values() -> None:
    """Custom values should override defaults."""
    s = Settings(
        embedder_provider="ollama",
        vector_store_backend="sqlite",
        embedder_model="custom-model",
    )
    assert s.embedder_provider == "ollama"
    assert s.vector_store_backend == "sqlite"
    assert s.embedder_model == "custom-model"


def test_settings_milvus_values() -> None:
    """Milvus config should be explicit and env-compatible."""
    s = Settings(
        vector_store_backend="milvus",
        milvus_uri="http://localhost:19530",
        milvus_token="token",
        milvus_collection_prefix="team_brain",
    )
    assert s.vector_store_backend == "milvus"
    assert s.milvus_uri == "http://localhost:19530"
    assert s.milvus_token == "token"
    assert s.milvus_collection_prefix == "team_brain"


def test_openai_embeddings_are_not_supported() -> None:
    """Cloud embeddings should not be reachable through configuration."""
    settings = Settings(embedder_provider="openai")
    container = Container(settings)
    with pytest.raises(ValueError, match="Supported providers"):
        _ = container.embedder


@pytest.mark.parametrize("batch_size", [0, 257])
def test_ollama_batch_size_is_bounded(batch_size: int) -> None:
    with pytest.raises(ValueError):
        Settings(ollama_batch_size=batch_size)
