"""Tests for config module."""

from codebrain.config import Settings


def test_settings_defaults() -> None:
    """Settings should have sensible defaults."""
    s = Settings()
    assert s.embedder_provider == "sentence-transformers"
    assert s.vector_store_backend == "sqlite"
    assert s.conventions_enabled is True
    assert s.session_memory_enabled is True
    assert s.history_enabled is True


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
