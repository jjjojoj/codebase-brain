"""Local-only context gathering for task-shaped Context Packs."""

from __future__ import annotations

from typing import Any

from codebrain.domains.conventions import tools as convention_tools
from codebrain.domains.history import tools as history_tools
from codebrain.domains.session_memory import tools as session_tools


def gather_local_context(
    *,
    task: str,
    files: list[str] | None = None,
    repo_path: str = ".",
    top_k: int = 5,
) -> dict[str, Any]:
    """Gather conventions, session memory, and Git read-only signals."""
    warnings: list[str] = []
    conventions = _safe_search_conventions(task, min(top_k, 3), warnings)
    if not conventions:
        warnings.append("no matching conventions found; index .codebrain/conventions if needed")
    sessions = _safe_recall_sessions(task, min(top_k, 3), warnings)
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
    task: str,
    top_k: int,
    warnings: list[str],
) -> list[dict[str, Any]]:
    try:
        return convention_tools.search_conventions(task, top_k=top_k)
    except Exception as exc:
        warnings.append(f"convention search unavailable: {exc}")
        return []


def _safe_recall_sessions(
    task: str,
    top_k: int,
    warnings: list[str],
) -> list[dict[str, Any]]:
    try:
        return session_tools.recall_context(task, top_k=top_k)
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
            for change in history_tools.get_recent_changes(
                file_path,
                limit=max(1, limit - len(changes)),
                repo_path=repo_path,
            ):
                changes.append({"file_path": file_path, **change})
                if len(changes) >= limit:
                    break
        except Exception as exc:
            warnings.append(f"recent changes unavailable for {file_path}: {exc}")
    return changes
