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
    """Use only to save an explicit, durable team rule approved by the user or team.

    Do not convert temporary task decisions, guesses, or existing code behavior
    into conventions automatically.
    """
    return logic.add_convention(module, title, content, _repo())


def search_conventions(
    query: str,
    keywords: str | list[str] | None = None,
    module_filter: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Use only when Context Pack lacks enough detail about relevant team rules."""
    return logic.search_conventions(query, _repo(), keywords, module_filter, top_k)


def list_conventions(module: str | None = None) -> list[dict[str, Any]]:
    """Use for convention maintenance or diagnostics, not routine coding tasks."""
    return logic.list_conventions(_repo(), module)


def index_convention_files(path: str | None = None) -> dict[str, Any]:
    """Automatically use after approved convention Markdown files are added or changed."""
    c = get_container()
    return logic.index_convention_files(_repo(), path or c.settings.default_conventions_path)
