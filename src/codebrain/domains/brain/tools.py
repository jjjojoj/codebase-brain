"""Composition-first tools for AI coding clients.

These wrappers expose a small task-shaped surface instead of asking every
client to know which low-level convention, memory, git, or graph tool to call.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from codebrain.adapters.codebase_memory import CodebaseMemoryAdapter
from codebrain.config import Settings
from codebrain.core.di import get_container
from codebrain.domains.conventions import tools as convention_tools


def brain_status(repo_path: str = ".") -> dict[str, Any]:
    """Return Codebase Brain 2.0 capability status for this project."""
    container = get_container()
    settings = container.settings
    graph = _make_codebase_memory_adapter(settings)
    return {
        "ok": True,
        "name": "codebase-brain",
        "profile": "composition-first",
        "repo_path": _resolve_repo_path(repo_path),
        "graph": graph.status(),
        "knowledge": {
            "vector_store_backend": settings.vector_store_backend,
            "db_path": str(settings.resolved_db_path),
            "conventions_path": settings.default_conventions_path,
            "conventions_enabled": settings.conventions_enabled,
            "session_memory_enabled": settings.session_memory_enabled,
            "history_enabled": settings.history_enabled,
        },
        "privacy": {
            "cloud_embeddings_allowed": settings.allow_cloud_embeddings,
            "git_history_vector_index_enabled": settings.git_history_index_enabled,
        },
        "recommended_tools": [
            "brain_index_project",
            "brain_explain_symbol",
            "search_conventions",
            "recall_context",
            "get_recent_changes",
            "get_blame",
            "get_co_changed_files",
        ],
    }


def brain_index_project(
    repo_path: str = ".",
    index_conventions: bool = True,
    conventions_path: str | None = None,
    graph_mode: str = "full",
    graph_persistence: bool = False,
) -> dict[str, Any]:
    """Index the project graph and local convention files when available."""
    container = get_container()
    settings = container.settings
    resolved_repo = _resolve_repo_path(repo_path)
    graph_mode = _validate_graph_mode(graph_mode)
    graph = _make_codebase_memory_adapter(settings)
    graph_result = graph.index_repository(
        resolved_repo,
        mode=graph_mode,
        persistence=graph_persistence,
    )

    convention_result: dict[str, Any] | None = None
    if index_conventions:
        target_path = conventions_path or _default_conventions_path(settings, resolved_repo)
        convention_result = _index_conventions(target_path)

    return {
        "ok": _is_ok(graph_result) or _is_ok(convention_result),
        "status": _combined_status(graph_result, convention_result),
        "repo_path": resolved_repo,
        "graph_mode": graph_mode,
        "graph_persistence": graph_persistence,
        "graph": graph_result,
        "conventions": convention_result,
        "notes": _index_notes(graph_result, convention_result),
    }


def brain_explain_symbol(
    symbol: str,
    repo_path: str = ".",
    depth: int = 2,
    top_k: int = 5,
    include_conventions: bool = True,
) -> dict[str, Any]:
    """Explain a symbol using graph search, call tracing, and team conventions."""
    symbol = _require_text(symbol, "symbol")
    depth = _bounded_int(depth, "depth", minimum=1, maximum=5)
    top_k = _bounded_int(top_k, "top_k", minimum=1, maximum=20)

    container = get_container()
    graph = _make_codebase_memory_adapter(container.settings)
    resolved_repo = _resolve_repo_path(repo_path)
    search_result = graph.search_graph(symbol=symbol, repo_path=resolved_repo, limit=top_k)
    trace_result = graph.trace_call_path(symbol=symbol, repo_path=resolved_repo, depth=depth)

    conventions: list[dict[str, Any]] = []
    convention_error = ""
    if include_conventions:
        try:
            conventions = convention_tools.search_conventions(symbol, top_k=3)
        except Exception as exc:
            convention_error = str(exc)

    graph_ready = _is_ok(search_result) or _is_ok(trace_result)
    return {
        "ok": graph_ready or bool(conventions),
        "status": "ok" if graph_ready else "graph_missing_or_error",
        "symbol": symbol,
        "repo_path": resolved_repo,
        "graph": {
            "search": search_result,
            "call_trace": trace_result,
        },
        "conventions": conventions,
        "conventions_error": convention_error,
        "notes": _explain_notes(search_result, trace_result, conventions, convention_error),
    }


def _make_codebase_memory_adapter(settings: Settings) -> CodebaseMemoryAdapter:
    return CodebaseMemoryAdapter(
        binary=settings.codebase_memory_binary,
        timeout_sec=settings.codebase_memory_timeout_sec,
    )


def _resolve_repo_path(repo_path: str) -> str:
    return str(Path(repo_path).expanduser().resolve())


def _default_conventions_path(settings: Settings, resolved_repo: str) -> str:
    path = Path(settings.default_conventions_path).expanduser()
    if path.is_absolute():
        return str(path)
    return str(Path(resolved_repo) / path)


def _index_conventions(path: str) -> dict[str, Any]:
    try:
        return convention_tools.index_convention_files(path)
    except Exception as exc:
        return {"ok": False, "status": "error", "path": path, "error": str(exc)}


def _validate_graph_mode(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("graph_mode is required")
    mode = value.strip()
    allowed = {"full", "moderate", "fast"}
    if mode not in allowed:
        raise ValueError(f"graph_mode must be one of: {', '.join(sorted(allowed))}")
    return mode


def _require_text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _bounded_int(value: int, name: str, minimum: int, maximum: int) -> int:
    if not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _is_ok(result: dict[str, Any] | None) -> bool:
    return bool(result and result.get("ok") is True)


def _combined_status(
    graph_result: dict[str, Any],
    convention_result: dict[str, Any] | None,
) -> str:
    graph_ok = _is_ok(graph_result)
    conventions_ok = _is_ok(convention_result)
    if graph_ok and (convention_result is None or conventions_ok):
        return "ok"
    if graph_ok or conventions_ok:
        return "partial"
    return "unavailable"


def _index_notes(
    graph_result: dict[str, Any],
    convention_result: dict[str, Any] | None,
) -> list[str]:
    notes: list[str] = []
    if not _is_ok(graph_result):
        notes.append(
            "Graph indexing is unavailable; install codebase-memory-mcp or configure "
            "CODEBRAIN_CODEBASE_MEMORY_BINARY."
        )
    if convention_result is None:
        notes.append("Convention indexing was skipped.")
    elif not _is_ok(convention_result):
        notes.append("Convention indexing did not complete successfully.")
    return notes


def _explain_notes(
    search_result: dict[str, Any],
    trace_result: dict[str, Any],
    conventions: list[dict[str, Any]],
    convention_error: str,
) -> list[str]:
    notes: list[str] = []
    if not (_is_ok(search_result) or _is_ok(trace_result)):
        notes.append(
            "Graph explanation is unavailable; index the project with "
            "brain_index_project after installing codebase-memory-mcp."
        )
    if convention_error:
        notes.append(f"Convention search failed: {convention_error}")
    elif not conventions:
        notes.append("No matching conventions were found.")
    return notes
