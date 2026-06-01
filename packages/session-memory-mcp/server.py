"""MCP server for recording and recalling AI coding session context."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
from typing import Any
from uuid import uuid4

from core.mcp_base import BrainMCP


@dataclass
class SessionState:
    """In-memory state for one active coding session."""

    session_id: str
    task: str
    start_time: str
    files: list[dict[str, str]] = field(default_factory=list)
    decisions: list[dict[str, str]] = field(default_factory=list)
    problems: list[dict[str, str]] = field(default_factory=list)


class SessionMemoryMCP(BrainMCP):
    """MCP server for session lifecycle memory and contextual recall."""

    def __init__(self) -> None:
        """Create the session-memory MCP server and register tools."""
        super().__init__("session-memory-mcp")
        self.current_session: SessionState | None = None
        self.sessions: dict[str, SessionState] = {}
        self.tool()(self.start_session)
        self.tool()(self.record_decision)
        self.tool()(self.record_problem)
        self.tool()(self.record_file_change)
        self.tool()(self.end_session)
        self.tool()(self.recall_context)

    def start_session(self, task_description: str) -> dict[str, Any]:
        """Start a new session and return similar past sessions."""
        task = task_description.strip()
        if not task:
            raise ValueError("task_description must not be empty")

        session = SessionState(
            session_id=uuid4().hex,
            task=task,
            start_time=_now(),
        )
        self.current_session = session
        self.sessions[session.session_id] = session

        related_sessions = self.recall_context(task, top_k=5)
        return {
            "session_id": session.session_id,
            "related_sessions": related_sessions,
            "suggestion": _build_suggestion(related_sessions),
        }

    def record_decision(self, decision: str, reason: str = "") -> dict[str, str]:
        """Record an architectural or implementation decision for the active session."""
        current = self._require_current_session()
        decision_text = decision.strip()
        if not decision_text:
            raise ValueError("decision must not be empty")
        current.decisions.append(
            {
                "decision": decision_text,
                "reason": reason.strip(),
                "recorded_at": _now(),
            }
        )
        return {"status": "recorded"}

    def record_problem(
        self,
        problem: str,
        solution: str,
        files: str = "",
    ) -> dict[str, str]:
        """Record a solved problem and the files involved in the active session."""
        current = self._require_current_session()
        problem_text = problem.strip()
        solution_text = solution.strip()
        if not problem_text:
            raise ValueError("problem must not be empty")
        if not solution_text:
            raise ValueError("solution must not be empty")
        current.problems.append(
            {
                "problem": problem_text,
                "solution": solution_text,
                "files": files.strip(),
                "recorded_at": _now(),
            }
        )
        return {"status": "recorded"}

    def record_file_change(
        self,
        file_path: str,
        change_type: str,
        description: str,
    ) -> dict[str, str]:
        """Track a file changed during the active session and why it changed."""
        current = self._require_current_session()
        path = file_path.strip()
        change = change_type.strip().lower()
        detail = description.strip()
        if not path:
            raise ValueError("file_path must not be empty")
        if change not in {"created", "modified", "deleted"}:
            raise ValueError("change_type must be one of: created, modified, deleted")
        if not detail:
            raise ValueError("description must not be empty")
        current.files.append(
            {
                "file_path": path,
                "change_type": change,
                "description": detail,
                "recorded_at": _now(),
            }
        )
        return {"status": "recorded"}

    def end_session(self, summary: str = "") -> dict[str, str]:
        """Persist the active session to Milvus and clear active in-memory state."""
        current = self._require_current_session()
        compiled_summary = _compile_summary(current, summary.strip())
        embedding = self.get_embedder().embed(compiled_summary)
        record_id = self.get_milvus().insert_session(
            task=current.task,
            files_modified=_serialize(current.files),
            decisions=_serialize(current.decisions),
            assumptions="",
            problems=_serialize(current.problems),
            embedding=embedding,
            id=current.session_id,
            created_at=current.start_time,
        )
        self.current_session = None
        return {"session_id": record_id, "status": "saved"}

    def recall_context(
        self,
        task_description: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Recall past sessions similar to task_description."""
        task = task_description.strip()
        if not task:
            return []
        if top_k < 1:
            raise ValueError("top_k must be greater than zero")

        embedding = self.get_embedder().embed(task)
        rows = self.get_milvus().search_sessions(embedding, top_k=top_k)
        return [_session_result(row) for row in rows]

    def _require_current_session(self) -> SessionState:
        """Return the active session or raise a user-facing error."""
        if self.current_session is None:
            raise RuntimeError("No active session. Call start_session first.")
        return self.current_session


def _session_result(row: dict[str, Any]) -> dict[str, Any]:
    """Return the public recall result shape for a stored session row."""
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
    """Build the text embedded for semantic recall."""
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
    """Create a concise suggestion from recalled session context."""
    if not related_sessions:
        return "No related sessions found. Start by recording key decisions and file changes."
    session = related_sessions[0]
    task = str(session.get("task", "")).strip()
    if not task:
        return "Review the most relevant past session before starting."
    return f"Review the most relevant past session first: {task}"


def _serialize(value: list[dict[str, str]]) -> str:
    """Serialize structured session fields for Milvus VARCHAR storage."""
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _deserialize(value: Any) -> Any:
    """Deserialize structured session fields while tolerating legacy text rows."""
    if not isinstance(value, str) or not value:
        return []
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _now() -> str:
    """Return the current UTC timestamp."""
    return datetime.now(UTC).isoformat()


def main() -> None:
    """Run the session-memory MCP server."""
    SessionMemoryMCP().run()


if __name__ == "__main__":
    main()
