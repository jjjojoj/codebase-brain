"""Session memory domain — pure business logic, no MCP dependencies."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from codebrain.core.repository import Repository


@dataclass
class SessionState:
    """In-memory state for one active coding session."""
    session_id: str
    task: str
    start_time: str
    files: list[dict[str, str]] = field(default_factory=list)
    decisions: list[dict[str, str]] = field(default_factory=list)
    problems: list[dict[str, str]] = field(default_factory=list)


# In-memory session registry (one active session per server process)
_current_session: SessionState | None = None
_sessions: dict[str, SessionState] = {}


def start_session(repo: Repository, task_description: str) -> dict[str, Any]:
    global _current_session
    task = task_description.strip()
    if not task:
        raise ValueError("task_description must not be empty")

    session = SessionState(
        session_id=uuid4().hex,
        task=task,
        start_time=_now(),
    )
    _current_session = session
    _sessions[session.session_id] = session

    related_sessions = recall_context(repo, task, top_k=5)
    return {
        "session_id": session.session_id,
        "related_sessions": related_sessions,
        "suggestion": _build_suggestion(related_sessions),
    }


def record_decision(decision: str, reason: str = "") -> dict[str, str]:
    current = _require_current_session()
    decision_text = decision.strip()
    if not decision_text:
        raise ValueError("decision must not be empty")
    current.decisions.append({
        "decision": decision_text,
        "reason": reason.strip(),
        "recorded_at": _now(),
    })
    return {"status": "recorded"}


def record_problem(problem: str, solution: str, files: str = "") -> dict[str, str]:
    current = _require_current_session()
    problem_text = problem.strip()
    solution_text = solution.strip()
    if not problem_text:
        raise ValueError("problem must not be empty")
    if not solution_text:
        raise ValueError("solution must not be empty")
    current.problems.append({
        "problem": problem_text,
        "solution": solution_text,
        "files": files.strip(),
        "recorded_at": _now(),
    })
    return {"status": "recorded"}


def record_file_change(
    file_path: str, change_type: str, description: str
) -> dict[str, str]:
    current = _require_current_session()
    path = file_path.strip()
    change = change_type.strip().lower()
    detail = description.strip()
    if not path:
        raise ValueError("file_path must not be empty")
    if change not in {"created", "modified", "deleted"}:
        raise ValueError("change_type must be one of: created, modified, deleted")
    if not detail:
        raise ValueError("description must not be empty")
    current.files.append({
        "file_path": path,
        "change_type": change,
        "description": detail,
        "recorded_at": _now(),
    })
    return {"status": "recorded"}


def end_session(repo: Repository, summary: str = "") -> dict[str, str]:
    global _current_session
    current = _require_current_session()
    compiled_summary = _compile_summary(current, summary.strip())
    record_id = repo.insert_session(
        task=current.task,
        files_modified=_serialize(current.files),
        decisions=_serialize(current.decisions),
        assumptions="",
        problems=_serialize(current.problems),
        record_id=current.session_id,
        created_at=current.start_time,
        summary=summary.strip(),
    )
    _current_session = None
    return {"session_id": record_id, "status": "saved"}


def recall_context(
    repo: Repository, task_description: str, top_k: int = 5
) -> list[dict[str, Any]]:
    task = task_description.strip()
    if not task:
        return []
    if top_k < 1:
        raise ValueError("top_k must be greater than zero")
    rows = repo.search_sessions(task, top_k=top_k)
    return [_session_result(row) for row in rows]


def get_current_session_id() -> str | None:
    if _current_session is not None:
        return _current_session.session_id
    return None


# ----------------------------------------------------------------- Helpers

def _require_current_session() -> SessionState:
    if _current_session is None:
        raise RuntimeError("No active session. Call start_session first.")
    return _current_session


def _session_result(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": row.get("id", ""),
        "task": row.get("task", ""),
        "files_modified": _deserialize(row.get("files_modified", "")),
        "decisions": _deserialize(row.get("decisions", "")),
        "problems": _deserialize(row.get("problems", "")),
        "created_at": row.get("created_at", ""),
        "relevance_score": row.get("similarity"),
    }


def _compile_summary(session: SessionState, summary: str) -> str:
    sections = [
        f"Task: {session.task}",
        f"Started: {session.start_time}",
        f"Files changed: {_serialize(session.files)}",
        f"Decisions: {_serialize(session.decisions)}",
        f"Problems solved: {_serialize(session.problems)}",
    ]
    if summary:
        sections.append(f"Summary: {summary}")
    return "\n\n".join(sections)


def _build_suggestion(related_sessions: list[dict[str, Any]]) -> str:
    if not related_sessions:
        return "No related sessions found. Start by recording key decisions and file changes."
    session = related_sessions[0]
    task = str(session.get("task", "")).strip()
    if not task:
        return "Review the most relevant past session before starting."
    return f"Review the most relevant past session first: {task}"


def _serialize(value: list[dict[str, str]]) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _deserialize(value: Any) -> Any:
    if not isinstance(value, str) or not value:
        return []
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _now() -> str:
    return datetime.now(UTC).isoformat()
