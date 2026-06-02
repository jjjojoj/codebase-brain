"""Git history domain — pure business logic, no MCP dependencies."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from codebrain.core.repository import Repository

# Re-export git_indexer functions for convenience
from codebrain.domains.history.git_indexer import (
    get_blame_info,
    get_co_changed,
    get_file_snippet_at_commit,
    get_recent_changes,
    parse_git_log,
)


def search_history(
    repo: Repository,
    query: str,
    file_filter: str | None = None,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """Search indexed git history by semantic similarity."""
    if not query.strip():
        return []
    results = repo.search_history(query, file_filter=file_filter, top_k=top_k)
    return [_history_result(row) for row in results]


def index_git_history(
    repo: Repository,
    repo_path: str = ".",
    max_commits: int = 500,
    max_entries: int = 500,
) -> dict[str, int]:
    """Index recent git commit/file history into the git_history collection.

    max_entries caps the total indexed file-change entries, preventing runaway
    loops on projects with massive initial commits (e.g. Django's 7000+ files).
    """
    rp = Path(repo_path).expanduser().resolve()
    commits = parse_git_log(rp, max_commits)
    if not commits:
        return {"indexed_commits": 0, "indexed_entries": 0}

    indexed_entries = 0
    for commit in commits:
        changed_files = commit.get("changed_files", [])
        if not isinstance(changed_files, list):
            continue
        for file_path in changed_files:
            if not isinstance(file_path, str) or not file_path:
                continue
            code_snippet = get_file_snippet_at_commit(
                rp, str(commit["commit_hash"]), file_path
            )
            repo.insert_git_entry(
                file_path=file_path,
                commit_hash=str(commit["commit_hash"]),
                commit_msg=str(commit["commit_msg"]),
                author=str(commit["author"]),
                date=str(commit["date"]),
                code_snippet=code_snippet,
            )

            indexed_entries += 1
            if indexed_entries >= max_entries:
                break
        if indexed_entries >= max_entries:
            break

    return {"indexed_commits": len(commits), "indexed_entries": indexed_entries}


def _history_result(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "commit_hash": row.get("commit_hash", ""),
        "commit_msg": row.get("commit_msg", ""),
        "author": row.get("author", ""),
        "date": row.get("date", ""),
        "file_path": row.get("file_path", ""),
        "code_snippet": row.get("code_snippet", ""),
        "similarity": row.get("similarity"),
    }
