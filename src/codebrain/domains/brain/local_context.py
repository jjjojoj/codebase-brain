"""Local-only context gathering for task-shaped Context Packs."""

from __future__ import annotations

from typing import Any

from codebrain.core.repository import Repository
from codebrain.domains.conventions import logic as convention_logic
from codebrain.domains.history import git_indexer
from codebrain.domains.session_memory import logic as session_logic


def gather_local_context(
    *,
    task: str,
    files: list[str] | None = None,
    repo_path: str = ".",
    top_k: int = 5,
    repository: Repository | None = None,
) -> dict[str, Any]:
    """Gather conventions, session memory, and Git read-only signals."""
    warnings: list[str] = []
    if repository is None:
        warnings.append("repository unavailable for local vector context")
    conventions = _safe_search_conventions(repository, task, min(top_k, 3), warnings)
    if repository is not None and not conventions:
        warnings.append("no matching conventions found; index .codebrain/conventions if needed")
    sessions = _safe_recall_sessions(repository, task, min(top_k, 3), warnings)
    recent_changes = _safe_recent_changes(files or [], repo_path, min(top_k, 5), warnings)
    return {
        "status": {
            "conventions": "ready" if conventions else "empty",
            "history": "ready" if recent_changes else "empty",
            "memory": "ready" if sessions else "empty",
        },
        "critical_conventions": conventions,
        "recent_changes": recent_changes,
        "similar_sessions": sessions,
        "warnings": warnings,
    }


def _safe_search_conventions(
    repository: Repository | None,
    task: str,
    top_k: int,
    warnings: list[str],
) -> list[dict[str, Any]]:
    if repository is None:
        return []
    try:
        return convention_logic.search_conventions(task, repository, top_k=top_k)
    except Exception as exc:
        warnings.append(f"convention search unavailable: {exc}")
        return []


def _safe_recall_sessions(
    repository: Repository | None,
    task: str,
    top_k: int,
    warnings: list[str],
) -> list[dict[str, Any]]:
    if repository is None:
        return []
    try:
        return session_logic.recall_context(repository, task, top_k=top_k)
    except Exception as exc:
        warnings.append(f"session memory unavailable: {exc}")
        return []


def _safe_recent_changes(
    files: list[str],
    repo_path: str,
    limit: int,
    warnings: list[str],
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for file_path in files:
        if len(changes) >= limit:
            break
        try:
            for change in git_indexer.get_recent_changes(
                repo_path,
                file_path,
                limit=max(1, limit - len(changes)),
            ):
                changes.append({"file_path": file_path, **change})
                if len(changes) >= limit:
                    break
        except Exception as exc:
            warnings.append(f"recent changes unavailable for {file_path}: {exc}")
    return changes
