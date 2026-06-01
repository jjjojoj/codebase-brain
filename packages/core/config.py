"""Configuration for the Codebase Brain core package."""

from __future__ import annotations

import os
from pathlib import Path
from threading import Lock


class Config:
    """Singleton configuration loaded from environment variables."""

    _instance: Config | None = None
    _lock: Lock = Lock()

    DEFAULT_MILVUS_DB_PATH = "~/.codebrain/milvus.db"
    DEFAULT_EMBEDDING_PROVIDER = "sentence_transformers"
    DEFAULT_EMBEDDING_MODEL = "BAAI/bge-m3"
    DEFAULT_OLLAMA_HOST = "http://localhost:11434"
    DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

    MILVUS_DB_PATH: str
    EMBEDDING_PROVIDER: str
    EMBEDDING_MODEL: str
    OLLAMA_HOST: str
    OPENAI_API_KEY: str | None
    OPENAI_EMBEDDING_MODEL: str

    def __new__(cls) -> Config:
        """Return the process-wide configuration instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        """Load supported settings from environment variables."""
        self.MILVUS_DB_PATH = os.getenv(
            "MILVUS_DB_PATH",
            self.DEFAULT_MILVUS_DB_PATH,
        )
        self.EMBEDDING_PROVIDER = self._resolve_embedding_provider()
        self.EMBEDDING_MODEL = os.getenv(
            "EMBEDDING_MODEL",
            self.DEFAULT_EMBEDDING_MODEL,
        )
        self.OLLAMA_HOST = os.getenv(
            "OLLAMA_HOST",
            self.DEFAULT_OLLAMA_HOST,
        )
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.OPENAI_EMBEDDING_MODEL = os.getenv(
            "OPENAI_EMBEDDING_MODEL",
            self.DEFAULT_OPENAI_EMBEDDING_MODEL,
        )

    def _resolve_embedding_provider(self) -> str:
        """Resolve embedding provider from env vars with auto-detection."""
        provider = os.getenv("EMBEDDING_PROVIDER")
        if provider:
            return provider
        if os.getenv("OPENAI_API_KEY"):
            return "openai"
        if os.getenv("OLLAMA_HOST"):
            return "ollama"
        return self.DEFAULT_EMBEDDING_PROVIDER

    @property
    def milvus_uri(self) -> str:
        """Return the expanded Milvus Lite database path."""
        path = Path(self.MILVUS_DB_PATH).expanduser()
        return str(path)

    def ensure_data_dirs(self) -> None:
        """Create local data directories needed by embedded services."""
        Path(self.milvus_uri).parent.mkdir(parents=True, exist_ok=True)
