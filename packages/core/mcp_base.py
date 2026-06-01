"""Shared FastMCP base wrapper for Codebase Brain servers."""

from __future__ import annotations

import logging
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from threading import Event, Thread
from time import monotonic, sleep
from typing import Any, TypeVar

from .config import Config
from .embedder import Embedder
from .milvus_client import MilvusClient

F = TypeVar("F", bound=Callable[..., Any])


class BrainMCP:
    """Base wrapper that wires FastMCP, Milvus, and embeddings together."""

    def __init__(self, name: str, config: Config | None = None) -> None:
        """Create an MCP server and initialize shared core services."""
        self.name = name
        self.config = config or Config()
        self.logger = logging.getLogger(name)
        self.mcp = self._create_fastmcp(name)
        self._milvus: MilvusClient | None = None
        self._milvus_error: str | None = None
        self._embedder: Embedder | None = None
        self._embedder_error: str | None = None
        self._watch_stop = Event()
        self._watch_thread: Thread | None = None
        self._init_milvus()
        self._register_health_tool()

    def _create_fastmcp(self, name: str) -> Any:
        """Create a FastMCP instance from the mcp package."""
        try:
            from mcp.server.fastmcp import FastMCP
        except ImportError as exc:
            raise RuntimeError(
                "mcp is required for BrainMCP. Install project dependencies first."
            ) from exc
        return FastMCP(name)

    def _init_milvus(self) -> None:
        """Initialize Milvus collections during server startup."""
        try:
            self._milvus = MilvusClient(self.config)
            self._milvus.init_collections()
        except Exception as exc:
            self.logger.exception("Milvus initialization failed")
            self._milvus = None
            self._milvus_error = str(exc)

    def _register_health_tool(self) -> None:
        """Register a basic health check tool on every server."""
        self.mcp.tool()(self.health)

    def get_milvus(self) -> MilvusClient:
        """Return the initialized Milvus client."""
        if self._milvus is None:
            detail = f": {self._milvus_error}" if self._milvus_error else "."
            raise RuntimeError(f"Milvus client is not initialized{detail}")
        return self._milvus

    def get_embedder(self) -> Embedder:
        """Return the lazily initialized embedder."""
        if self._embedder is None:
            try:
                self._embedder = Embedder(self.config)
                self._embedder_error = None
            except Exception as exc:
                self._embedder_error = str(exc)
                raise
        return self._embedder

    def tool(self, *args: Any, **kwargs: Any) -> Callable[[F], F]:
        """Register a FastMCP tool with standard error handling."""
        def decorator(func: F) -> F:
            wrapped = self.with_error_handling(func)
            return self.mcp.tool(*args, **kwargs)(wrapped)

        return decorator

    def with_error_handling(self, func: F) -> F:
        """Wrap a callable so MCP tool failures return structured errors."""
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                self.logger.exception("Tool %s failed", func.__name__)
                return {
                    "ok": False,
                    "error": str(exc),
                    "type": exc.__class__.__name__,
                }

        return wrapper  # type: ignore[return-value]

    def health(self) -> dict[str, Any]:
        """Return server health and core dependency status."""
        return {
            "ok": True,
            "name": self.name,
            "milvus": self._milvus is not None,
            "milvus_error": self._milvus_error,
            "embedder": self._embedder is not None,
            "embedder_error": self._embedder_error,
            "embedding_model": self.config.EMBEDDING_MODEL,
            "milvus_db_path": self.config.milvus_uri,
            "sync_watcher": self._watch_thread is not None and self._watch_thread.is_alive(),
        }

    def watch_sync_trigger(
        self,
        callback: Callable[[], Any],
        *,
        trigger_path: str | Path | None = None,
        debounce_seconds: float = 2.0,
        poll_seconds: float = 0.5,
    ) -> None:
        """Watch the sync-trigger file and call a callback on modification."""
        if self._watch_thread is not None and self._watch_thread.is_alive():
            raise RuntimeError("sync-trigger watcher is already running")
        path = Path(trigger_path or "~/.codebrain/.sync-trigger").expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._watch_stop.clear()
        self._watch_thread = Thread(
            target=self._watch_loop,
            args=(path, callback, debounce_seconds, poll_seconds),
            daemon=True,
            name=f"{self.name}-sync-trigger",
        )
        self._watch_thread.start()

    def stop_sync_trigger_watch(self) -> None:
        """Stop the sync-trigger watcher if it is running."""
        self._watch_stop.set()
        if self._watch_thread is not None:
            self._watch_thread.join(timeout=2.0)
        self._watch_thread = None

    def _watch_loop(
        self,
        path: Path,
        callback: Callable[[], Any],
        debounce_seconds: float,
        poll_seconds: float,
    ) -> None:
        """Poll the sync-trigger file and debounce callback execution."""
        last_mtime = path.stat().st_mtime if path.exists() else None
        last_callback_at = 0.0
        while not self._watch_stop.is_set():
            try:
                current_mtime = path.stat().st_mtime if path.exists() else None
                changed = current_mtime is not None and current_mtime != last_mtime
                ready = monotonic() - last_callback_at >= debounce_seconds
                if changed and ready:
                    last_mtime = current_mtime
                    last_callback_at = monotonic()
                    callback()
                elif changed:
                    last_mtime = current_mtime
            except Exception:
                self.logger.exception("sync-trigger callback failed")
            sleep(poll_seconds)

    def run(self, transport: str = "stdio") -> None:
        """Run the MCP server."""
        self.mcp.run(transport=transport)
