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
    embedder_device: str = "cpu"
    ollama_url: str = "http://localhost:11434"

    # Vector store
    vector_store_backend: str = "sqlite"
    db_path: str = ".codebrain/codebrain.db"
    milvus_uri: str = ".codebrain/milvus_lite.db"
    milvus_token: str | None = None
    milvus_collection_prefix: str = "codebrain"

    # Domains
    conventions_enabled: bool = True
    session_memory_enabled: bool = True
    history_enabled: bool = True
    git_history_index_enabled: bool = False

    # External code graph adapter
    codebase_memory_binary: str = "codebase-memory-mcp"
    codebase_memory_timeout_sec: int = 120

    # Project
    default_project: str = ""
    default_conventions_path: str = ".codebrain/conventions"
    index_max_file_size_mb: int = 5

    @property
    def resolved_db_path(self) -> Path:
        """Return the expanded database path."""
        return Path(self.db_path).expanduser().resolve()

    def ensure_data_dirs(self) -> None:
        """Create local data directories needed by embedded services."""
        self.resolved_db_path.parent.mkdir(parents=True, exist_ok=True)
