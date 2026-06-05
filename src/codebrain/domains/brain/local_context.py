"""Local-only context gathering for task-shaped Context Packs."""

from __future__ import annotations

import time
from typing import Any

from codebrain.core.repository import Repository
from codebrain.domains.conventions import logic as convention_logic
from codebrain.domains.history import git_indexer
from codebrain.domains.session_memory import logic as session_logic

_HISTORY_CONTEXT_TIMEOUT_SECONDS = 6.0
_RECENT_CHANGES_TIMEOUT_SECONDS = 4.0
_CO_CHANGED_TIMEOUT_SECONDS = 4.0
_BLAME_ATTRIBUTION_TIMEOUT_SECONDS = 2.0


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
    started = time.perf_counter()
    conventions_started = time.perf_counter()
    conventions = _safe_search_conventions(repository, task, min(top_k, 3), warnings)
    conventions_seconds = round(time.perf_counter() - conventions_started, 3)
    if repository is not None and not conventions:
        warnings.append("no matching conventions found; index .codebrain/conventions if needed")
    sessions_started = time.perf_counter()
    sessions = _safe_recall_sessions(repository, task, min(top_k, 3), warnings)
    sessions_seconds = round(time.perf_counter() - sessions_started, 3)
    context_files = files or []
    history_started = time.perf_counter()
    history = _safe_history_context(context_files, repo_path, min(top_k, 5), warnings)
    history_seconds = round(time.perf_counter() - history_started, 3)
    recent_changes = history["recent_changes"]
    co_changed_files = history["co_changed_files"]
    blame = history["blame"]
    return {
        "status": {
            "conventions": "ready" if conventions else "empty",
            "history": "ready" if any([recent_changes, co_changed_files, blame]) else "empty",
            "memory": "ready" if sessions else "empty",
        },
        "context_files": context_files,
        "critical_conventions": conventions,
        "recent_changes": recent_changes,
        "co_changed_files": co_changed_files,
        "blame": blame,
        "similar_sessions": sessions,
        "warnings": warnings,
        "timings": {
            "conventions_seconds": conventions_seconds,
            "sessions_seconds": sessions_seconds,
            "history_seconds": history_seconds,
            "recent_changes_seconds": history_seconds,
            "co_changed_seconds": 0.0,
            "blame_seconds": 0.0,
            "total_seconds": round(time.perf_counter() - started, 3),
        },
    }


def select_context_files(
    files: list[str],
    graph: dict[str, Any] | None,
    *,
    limit: int = 3,
) -> list[str]:
    """Select explicit files first, then source files inferred from graph results."""
    candidates = [*files]
    for symbol in (graph or {}).get("related_symbols", []):
        if isinstance(symbol, dict):
            candidates.append(str(symbol.get("file_path", "")))
    selected: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = candidate.strip().replace("\\", "/")
        if normalized and normalized not in seen:
            selected.append(normalized)
            seen.add(normalized)
        if len(selected) >= limit:
            break
    return selected


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
    if not files:
        return []


def _safe_history_context(
    files: list[str],
    repo_path: str,
    limit: int,
    warnings: list[str],
) -> dict[str, list[dict[str, Any]]]:
    empty: dict[str, list[dict[str, Any]]] = {
        "recent_changes": [],
        "co_changed_files": [],
        "blame": [],
    }
    if not files:
        return empty
    try:
        rows = git_indexer.get_history_context_for_files(
            repo_path,
            files,
            limit=limit,
            max_commits=50,
            timeout_sec=_HISTORY_CONTEXT_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        warnings.append(f"history context unavailable: {exc}")
        return empty
    if not any(rows.values()):
        warnings.append("history context unavailable or timed out")
    return rows
    try:
        rows = git_indexer.get_recent_changes_for_files(
            repo_path,
            files,
            limit=limit,
            timeout_sec=_RECENT_CHANGES_TIMEOUT_SECONDS,
        )
        if not rows:
            warnings.append("recent changes unavailable or timed out")
        return rows
    except Exception as exc:
        warnings.append(f"recent changes unavailable: {exc}")
        return []


def _safe_co_changed(
    files: list[str],
    repo_path: str,
    limit: int,
    warnings: list[str],
) -> list[dict[str, Any]]:
    if not files:
        return []
    try:
        rows = git_indexer.get_co_changed_for_files(
            repo_path,
            files,
            limit=max(1, limit),
            max_commits=50,
            timeout_sec=_CO_CHANGED_TIMEOUT_SECONDS,
        )
        if not rows:
            warnings.append("co-changed files unavailable or timed out")
        return rows[:limit]
    except Exception as exc:
        warnings.append(f"co-changed files unavailable: {exc}")
        return []


def _safe_blame(
    files: list[str],
    repo_path: str,
    limit: int,
    warnings: list[str],
) -> list[dict[str, Any]]:
    if not files:
        return []
    try:
        rows = git_indexer.get_last_change_for_files(
            repo_path,
            files,
            max_commits=50,
            timeout_sec=_BLAME_ATTRIBUTION_TIMEOUT_SECONDS,
        )
        if not rows:
            warnings.append("blame attribution unavailable or timed out")
        return rows[:limit]
    except Exception as exc:
        warnings.append(f"blame attribution unavailable: {exc}")
        return []


def _round_robin(groups: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Interleave sampled regions so the beginning cannot consume the result budget."""
    results: list[dict[str, Any]] = []
    max_length = max((len(group) for group in groups), default=0)
    for index in range(max_length):
        for group in groups:
            if index < len(group):
                results.append(group[index])
    return results


def _blame_ranges(line_count: int, budget: int = 40) -> list[tuple[int, int]]:
    """Sample a file across its beginning, middle, and end within a line budget."""
    if line_count <= 0:
        return []
    if line_count <= budget:
        return [(1, line_count)]

    first_size = budget // 3 + budget % 3
    middle_size = budget // 3
    last_size = budget // 3
    middle_start = max(first_size + 1, (line_count - middle_size) // 2 + 1)
    return [
        (1, first_size),
        (middle_start, middle_start + middle_size - 1),
        (line_count - last_size + 1, line_count),
    ]
