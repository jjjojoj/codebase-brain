"""Session memory domain — thin MCP @tool wrappers."""

from __future__ import annotations

from typing import Any

from codebrain.core.di import get_container
from codebrain.core.repository import Repository
from codebrain.domains.session_memory import logic


def _repo() -> Repository:
    c = get_container()
    return Repository(c.vector_store, c.embedder)


def start_session(task_description: str) -> dict[str, Any]:
    """Automatically call once after Context Pack for complex or cross-session work.

    Use for multi-step tasks where decisions, solved problems, or file changes
    should survive the current conversation. Skip trivial, read-only, or one-step tasks.
    """
    return logic.start_session(_repo(), task_description)


def record_decision(decision: str, reason: str = "") -> dict[str, str]:
    """Automatically record a finalized meaningful decision in the active session.

    Call when an implementation or architecture choice is accepted and its reason
    is known. Do not record tentative ideas, obvious mechanics, or unresolved options.
    """
    return logic.record_decision(decision, reason)


def record_problem(problem: str, solution: str, files: str = "") -> dict[str, str]:
    """Automatically record a solved non-obvious problem in the active session.

    Call after root cause and verified solution are known. Do not record unresolved
    speculation, routine errors, or failed attempts as final solutions.
    """
    return logic.record_problem(problem, solution, files)


def record_file_change(
    file_path: str, change_type: str, description: str
) -> dict[str, str]:
    """Automatically record each meaningful file change in the active session.

    Call after a source, test, configuration, or documentation change is complete
    and its purpose is clear. Skip generated files, formatting-only churn, and trivial edits.
    """
    return logic.record_file_change(file_path, change_type, description)


def end_session(summary: str = "") -> dict[str, str]:
    """Automatically call once when complex work is complete or being handed off.

    Call after relevant tests and final meaningful records. Summarize outcomes,
    remaining risks, and follow-up work. Do not call mid-task.
    """
    return logic.end_session(_repo(), summary)


def recall_context(task_description: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Use only when Context Pack lacks enough past-session detail for the task."""
    return logic.recall_context(_repo(), task_description, top_k)
