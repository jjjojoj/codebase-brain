"""Local-only context gathering for task-shaped Context Packs."""

from __future__ import annotations

from pathlib import Path
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
    context_files = files or []
    recent_changes = _safe_recent_changes(context_files, repo_path, min(top_k, 5), warnings)
    co_changed_files = _safe_co_changed(context_files, repo_path, min(top_k, 5), warnings)
    blame = _safe_blame(context_files, repo_path, min(top_k, 5), warnings)
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


def _safe_co_changed(
    files: list[str],
    repo_path: str,
    limit: int,
    warnings: list[str],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for file_path in files:
        try:
            for row in git_indexer.get_co_changed(
                repo_path,
                file_path,
                limit=max(1, limit),
                max_commits=50,
            ):
                results.append({"source_file": file_path, **row})
        except Exception as exc:
            warnings.append(f"co-changed files unavailable for {file_path}: {exc}")
    return results[:limit]


def _safe_blame(
    files: list[str],
    repo_path: str,
    limit: int,
    warnings: list[str],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for file_path in files:
        try:
            target = Path(repo_path) / file_path
            if not target.is_file():
                continue
            with target.open("r", encoding="utf-8", errors="replace") as source:
                end_line = sum(1 for _, _line in zip(range(40), source))
            if end_line == 0:
                continue
            rows = git_indexer.get_blame_info(repo_path, file_path, 1, end_line)
            seen_commits: set[str] = set()
            for row in rows:
                commit_hash = str(row.get("commit_hash", ""))
                if commit_hash in seen_commits:
                    continue
                results.append({"file_path": file_path, **row})
                seen_commits.add(commit_hash)
                if len(results) >= limit:
                    return results
        except Exception as exc:
            warnings.append(f"blame unavailable for {file_path}: {exc}")
    return results
