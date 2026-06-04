"""Context Pack assembly for task-shaped AI coding context."""

from __future__ import annotations

import re
from typing import Any


_TASK_CHECKLIST = {
    r"\b(export|csv|report)\b": "ensure deterministic ordering (e.g. .order_by('id'))",
    r"\bmanagement\s+command\b": "check requires_system_checks = [] for read-only commands",
    r"\b(exceptions?|error|handle|handling|try)\b": "avoid broad Exception unless intentionally documented",
    r"\b(api|fastapi)\b": "check response model, docstring, and version metadata",
}


def assemble_context_pack(
    *,
    task: str,
    local: dict[str, Any] | None,
    graph: dict[str, Any] | None,
) -> dict[str, Any]:
    """Merge local and graph context into one degraded-safe Context Pack."""
    local = local or {}
    graph = graph or _missing_graph_context()

    critical_conventions = _as_list(local.get("critical_conventions"))
    related_symbols = _as_list(graph.get("related_symbols"))
    recent_changes = _as_list(local.get("recent_changes"))
    similar_sessions = _as_list(local.get("similar_sessions"))
    warnings = [
        *_as_list(local.get("warnings")),
        *_as_list(graph.get("warnings")),
    ]
    if not any([critical_conventions, related_symbols, recent_changes, similar_sessions]):
        warnings.append("context pack has no results")

    local_status = _as_dict(local.get("status"))
    status = {
        "local": _local_status(local),
        **local_status,
        "graph": graph.get("status", "missing"),
    }

    return {
        "task": task,
        "status": status,
        "critical_conventions": critical_conventions,
        "related_symbols": related_symbols,
        "recent_changes": recent_changes,
        "similar_sessions": similar_sessions,
        "warnings": warnings,
        "suggested_next_steps": _suggested_next_steps(
            task,
            status,
            warnings,
            critical_conventions=critical_conventions,
            recent_changes=recent_changes,
            similar_sessions=similar_sessions,
        ),
    }


def _missing_graph_context() -> dict[str, Any]:
    return {
        "status": "missing",
        "related_symbols": [],
        "warnings": ["graph sidecar not available"],
    }


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _local_status(local: dict[str, Any]) -> str:
    if any(_as_list(local.get(key)) for key in (
        "critical_conventions",
        "recent_changes",
        "similar_sessions",
    )):
        return "ready"
    return "empty"


def _suggested_next_steps(
    task: str,
    status: dict[str, Any],
    warnings: list[str],
    *,
    critical_conventions: list[Any],
    recent_changes: list[Any],
    similar_sessions: list[Any],
) -> list[str]:
    steps: list[str] = []
    steps.extend(_task_checklist(task))
    if status.get("local") == "empty":
        steps.append(
            "run brain_sync_project(force=true), then poll brain_index_job_status(job_id)"
        )
    if not any([critical_conventions, recent_changes, similar_sessions]):
        steps.append(
            "no context found for this task; try broader keywords or index conventions first"
        )
    if status.get("graph") == "missing":
        steps.append("install or configure codebase-memory-mcp for graph context")
    if any("convention" in warning for warning in warnings):
        steps.append("index .codebrain/conventions before editing")
    return steps


def _task_checklist(task: str) -> list[str]:
    lowered = task.lower()
    return [
        suggestion
        for pattern, suggestion in _TASK_CHECKLIST.items()
        if re.search(pattern, lowered)
    ]
