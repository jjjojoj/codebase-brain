"""Git history domain — thin MCP @tool wrappers."""

from __future__ import annotations

from typing import Any

from codebrain.config import Settings
from codebrain.core.di import get_container
from codebrain.core.repository import Repository
from codebrain.domains.brain import jobs as brain_jobs
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
    """Use for targeted line-level history after brain_context_for_task needs deeper blame."""
    return git_indexer.get_blame_info(repo_path, file_path, start_line, end_line)


def get_co_changed_files(
    file_path: str,
    limit: int = 10,
    repo_path: str = ".",
    max_commits: int = 50,
    async_mode: bool = True,
) -> dict[str, Any]:
    """Use for deeper single-file impact analysis after brain_context_for_task.

    Defaults to async_mode=True because Qoder has a ~30s hardcoded
    tool-call timeout that kills even fast git operations via MCP.
    When async, returns a job_id; poll brain_index_job_status(job_id).
    """
    def _run() -> dict[str, Any]:
        results = git_indexer.get_co_changed(repo_path, file_path, limit, max_commits)
        return {"ok": True, "results": results}

    if async_mode:
        job = brain_jobs.start_job(
            f"co-changed {file_path} (max_commits={max_commits})",
            _run,
        )
        return {
            "ok": True,
            "status": "queued",
            "job": job,
            "hint": "Poll brain_index_job_status(job_id) for results",
        }

    result = _run()
    return result


def get_recent_changes(
    file_path: str,
    limit: int = 10,
    repo_path: str = ".",
) -> list[dict[str, str]]:
    """Use for deeper single-file history after brain_context_for_task."""
    return git_indexer.get_recent_changes(repo_path, file_path, limit)


def index_git_history(
    repo_path: str = ".",
    max_commits: int = 500,
    max_entries: int = 500,
    async_mode: bool = True,
) -> dict[str, Any]:
    """Index recent git commit/file history into the git_history collection.

    Defaults to async_mode=True to avoid Qoder tool-call timeouts
    caused by sentence-transformers cold-start. When async, returns
    a job_id; poll with brain_index_job_status(job_id).
    """
    _require_git_history_index_enabled()

    def _run() -> dict[str, Any]:
        result = logic.index_git_history(_repo(), repo_path, max_commits, max_entries)
        return {"ok": True, **result}

    if async_mode:
        job = brain_jobs.start_job(
            f"git-index {repo_path} (commits={max_commits}, entries={max_entries})",
            _run,
        )
        return {
            "ok": True,
            "status": "queued",
            "job": job,
            "hint": "Poll brain_index_job_status(job_id) for results",
        }

    result = _run()
    return result


def _require_git_history_index_enabled() -> None:
    settings = Settings()
    if not settings.git_history_index_enabled:
        raise RuntimeError(
            "Git history vector indexing is disabled in the stable build. "
            "Use get_blame, get_recent_changes, and get_co_changed_files for safe git context."
        )
