"""Pydantic Settings for CodeBrain (CODEBRAIN_ env prefix)."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from env vars, .env file, and defaults."""

    model_config = SettingsConfigDict(
        env_prefix="CODEBRAIN_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Embedder
    embedder_provider: str = "sentence-transformers"
    embedder_model: str = "all-MiniLM-L6-v2"
    openai_api_key: str | None = None
    ollama_url: str = "http://localhost:11434"
    openai_embedding_model: str = "text-embedding-3-small"

    # Vector store
    vector_store_backend: str = "sqlite"
    db_path: str = ".codebrain/codebrain.db"

    # Domains
    conventions_enabled: bool = True
    session_memory_enabled: bool = True
    history_enabled: bool = True

    # Project
    default_project: str = ""
    index_max_file_size_mb: int = 5

    @property
    def resolved_db_path(self) -> Path:
        """Return the expanded database path."""
        return Path(self.db_path).expanduser().resolve()

    def ensure_data_dirs(self) -> None:
        """Create local data directories needed by embedded services."""
        self.resolved_db_path.parent.mkdir(parents=True, exist_ok=True)
