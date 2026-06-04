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
    """Start a new session and return similar past sessions."""
    return logic.start_session(_repo(), task_description)


def record_decision(decision: str, reason: str = "") -> dict[str, str]:
    """Record an architectural or implementation decision for the active session."""
    return logic.record_decision(decision, reason)


def record_problem(problem: str, solution: str, files: str = "") -> dict[str, str]:
    """Record a solved problem and the files involved in the active session."""
    return logic.record_problem(problem, solution, files)


def record_file_change(
    file_path: str, change_type: str, description: str
) -> dict[str, str]:
    """Track a file changed during the active session and why it changed."""
    return logic.record_file_change(file_path, change_type, description)


def end_session(summary: str = "") -> dict[str, str]:
    """Persist the active session to storage and clear active in-memory state."""
    return logic.end_session(_repo(), summary)


def recall_context(task_description: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Use after brain_context_for_task when deeper past-session recall is needed."""
    return logic.recall_context(_repo(), task_description, top_k)
