"""Conventions domain — thin MCP @tool wrappers."""

from __future__ import annotations

from typing import Any

from codebrain.core.di import get_container
from codebrain.core.repository import Repository
from codebrain.domains.conventions import logic


def _repo() -> Repository:
    c = get_container()
    return Repository(c.vector_store, c.embedder)


def add_convention(module: str, title: str, content: str) -> dict[str, Any]:
    """Add one convention directly to the conventions collection."""
    return logic.add_convention(module, title, content, _repo())


def search_conventions(
    query: str,
    keywords: str | list[str] | None = None,
    module_filter: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Search conventions with dense retrieval plus BM25/RRF hybrid ranking."""
    return logic.search_conventions(query, _repo(), keywords, module_filter, top_k)


def list_conventions(module: str | None = None) -> list[dict[str, Any]]:
    """List convention metadata, optionally filtered by module."""
    return logic.list_conventions(_repo(), module)


def index_convention_files(path: str | None = None) -> dict[str, Any]:
    """Index markdown convention files with YAML frontmatter."""
    return logic.index_convention_files(_repo(), path)
