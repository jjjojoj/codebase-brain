"""Git history domain — thin MCP @tool wrappers."""

from __future__ import annotations

from typing import Any

from codebrain.config import Settings
from codebrain.core.di import get_container
from codebrain.core.repository import Repository
from codebrain.domains.history import git_indexer, logic


def _repo() -> Repository:
    c = get_container()
    return Repository(c.vector_store, c.embedder)


def search_history(
    query: str,
    file_filter: str | None = None,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """Search indexed git history by semantic similarity."""
    _require_git_history_index_enabled()
    return logic.search_history(_repo(), query, file_filter, top_k)


def get_blame(
    file_path: str,
    start_line: int,
    end_line: int,
    repo_path: str = ".",
) -> list[dict[str, Any]]:
    """Return blame metadata for a file line range."""
    return git_indexer.get_blame_info(repo_path, file_path, start_line, end_line)


def get_co_changed_files(
    file_path: str,
    limit: int = 10,
    repo_path: str = ".",
) -> list[dict[str, Any]]:
    """Return files commonly changed with file_path."""
    return git_indexer.get_co_changed(repo_path, file_path, limit)


def get_recent_changes(
    file_path: str,
    limit: int = 10,
    repo_path: str = ".",
) -> list[dict[str, str]]:
    """Return recent commits that touched file_path."""
    return git_indexer.get_recent_changes(repo_path, file_path, limit)


def index_git_history(
    repo_path: str = ".", max_commits: int = 500
) -> dict[str, int]:
    """Index recent git commit/file history into the git_history collection."""
    _require_git_history_index_enabled()
    return logic.index_git_history(_repo(), repo_path, max_commits)


def _require_git_history_index_enabled() -> None:
    settings = Settings()
    if not settings.git_history_index_enabled:
        raise RuntimeError(
            "Git history vector indexing is disabled in the stable build. "
            "Use get_blame, get_recent_changes, and get_co_changed_files for safe git context."
        )
