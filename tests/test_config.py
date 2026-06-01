"""Tests for config module."""

import pytest

from codebrain.config import Settings
from codebrain.core.di import Container


def test_settings_defaults() -> None:
    """Settings should have sensible defaults."""
    s = Settings()
    assert s.embedder_provider == "sentence-transformers"
    assert s.vector_store_backend == "sqlite"
    assert s.conventions_enabled is True
    assert s.session_memory_enabled is True
    assert s.history_enabled is True
    assert s.allow_cloud_embeddings is False
    assert s.git_history_index_enabled is False
    assert s.default_conventions_path == ".codebrain/conventions"


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


def test_openai_embeddings_disabled_by_default() -> None:
    """Cloud embeddings should fail closed unless explicitly enabled."""
    settings = Settings(embedder_provider="openai", openai_api_key="dummy")
    container = Container(settings)
    with pytest.raises(RuntimeError, match="OpenAI embeddings are disabled"):
        _ = container.embedder
