"""Context Pack assembly for task-shaped AI coding context."""

from __future__ import annotations

from typing import Any


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
        "suggested_next_steps": _suggested_next_steps(status, warnings),
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


def _suggested_next_steps(status: dict[str, Any], warnings: list[str]) -> list[str]:
    steps: list[str] = []
    if status.get("local") == "empty":
        steps.append("run brain_index_project to index your repository")
    if status.get("graph") == "missing":
        steps.append("install or configure codebase-memory-mcp for graph context")
    if any("convention" in warning for warning in warnings):
        steps.append("index .codebrain/conventions before editing")
    return steps
