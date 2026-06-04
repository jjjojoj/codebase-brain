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
from codebrain.core.repository import Repository
from codebrain.domains.brain import context_pack, graph_context, indexing, jobs, local_context
from codebrain.domains.conventions import tools as convention_tools


def brain_context_for_task(
    task: str,
    repo_path: str = ".",
    files: list[str] | None = None,
    symbols: list[str] | None = None,
    top_k: int = 5,
    async_mode: bool = True,
) -> dict[str, Any]:
    """Automatically call first before planning, editing, reviewing, or debugging code.

    Automatically combines graph symbols, conventions, session memory, recent
    changes, co-changed files, and blame samples. Provide files or symbols when
    known; otherwise relevant source files are inferred from graph results. Poll
    the returned job automatically. Do not make the user request low-level tools first.
    """
    task = _require_text(task, "task")
    top_k = _bounded_int(top_k, "top_k", minimum=1, maximum=20)
    resolved_repo = _resolve_repo_path(repo_path)
    files = _clean_text_list(files)
    symbols = _clean_text_list(symbols)

    def target() -> dict[str, Any]:
        return _build_context_pack(
            task=task,
            repo_path=resolved_repo,
            files=files,
            symbols=symbols,
            top_k=top_k,
        )

    if async_mode:
        job = jobs.start_job(f"context-pack {task[:80]}", target)
        return {
            "ok": True,
            "status": "queued",
            "job": job,
            "hint": "Poll brain_index_job_status(job_id) for the Context Pack",
        }
    return target()


def _build_context_pack(
    *,
    task: str,
    repo_path: str,
    files: list[str],
    symbols: list[str],
    top_k: int,
) -> dict[str, Any]:
    """Build one Context Pack after inputs have been validated."""
    container = get_container()
    graph = graph_context.gather_graph_context(
        task=task,
        symbols=symbols,
        repo_path=repo_path,
        top_k=top_k,
        adapter=_make_codebase_memory_adapter(container.settings),
    )
    context_files = local_context.select_context_files(files, graph, limit=min(top_k, 3))
    local = local_context.gather_local_context(
        task=task,
        files=context_files,
        repo_path=repo_path,
        top_k=top_k,
        repository=_make_repository(),
    )
    return context_pack.assemble_context_pack(task=task, local=local, graph=graph)


def brain_status(repo_path: str = ".") -> dict[str, Any]:
    """Use only for setup or diagnostics, not as a substitute for task context."""
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
            "milvus": {
                "status": _milvus_status(settings),
                "uri": settings.milvus_uri,
                "collection_prefix": settings.milvus_collection_prefix,
            },
        },
        "resources": container.resource_status(),
        "privacy": {
            "embedding_policy": "local_only",
            "supported_embedding_providers": ["sentence-transformers", "ollama"],
            "git_history_vector_index_enabled": settings.git_history_index_enabled,
        },
        "primary_tool": "brain_context_for_task",
        "recommended_tools": [
            "brain_context_for_task",
            "brain_index_project",
            "brain_sync_status",
            "brain_sync_project",
            "brain_index_job_status",
            "brain_explain_symbol",
        ],
        "deep_dive_tools": [
            "search_conventions",
            "recall_context",
            "get_recent_changes",
            "get_blame",
            "get_co_changed_files",
        ],
    }


def brain_sync_status(
    repo_path: str = ".",
    include_patterns: str | list[str] | None = None,
    exclude_patterns: str | list[str] | None = None,
) -> dict[str, Any]:
    """Automatically check after meaningful code changes before refreshing project knowledge."""
    settings = get_container().settings
    return indexing.sync_status(
        repo_path,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        max_file_size_mb=settings.index_max_file_size_mb,
    )


def brain_sync_project(
    repo_path: str = ".",
    include_patterns: str | list[str] | None = None,
    exclude_patterns: str | list[str] | None = None,
    async_mode: bool = True,
    force: bool = False,
    index_conventions: bool = True,
    conventions_path: str | None = None,
    graph_mode: str = "full",
    graph_persistence: bool = False,
) -> dict[str, Any]:
    """Automatically refresh project knowledge when brain_sync_status reports it stale."""
    status = brain_sync_status(
        repo_path,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
    )
    if not force and not status["needs_sync"]:
        return {
            "ok": True,
            "status": "fresh",
            "repo_path": status["repo_path"],
            "sync": status,
            "job": None,
        }

    def target() -> dict[str, Any]:
        return _run_sync_project(
            repo_path=status["repo_path"],
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            index_conventions=index_conventions,
            conventions_path=conventions_path,
            graph_mode=graph_mode,
            graph_persistence=graph_persistence,
        )

    if async_mode:
        job = jobs.start_job(f"sync {status['repo_path']}", target)
        return {
            "ok": True,
            "status": "queued",
            "repo_path": status["repo_path"],
            "sync": status,
            "job": job,
        }

    result = target()
    return {
        "ok": result.get("ok") is True,
        "status": result.get("status", "unknown"),
        "repo_path": status["repo_path"],
        "sync": status,
        "job": None,
        "result": result,
    }


def brain_index_job_status(job_id: str | None = None) -> dict[str, Any]:
    """Automatically poll any queued Codebase Brain job until it succeeds or fails."""
    if job_id:
        return jobs.get_job(job_id)
    return jobs.list_jobs()


def brain_index_project(
    repo_path: str = ".",
    index_conventions: bool = True,
    conventions_path: str | None = None,
    graph_mode: str = "full",
    graph_persistence: bool = False,
) -> dict[str, Any]:
    """Use only for initial setup or explicit re-indexing; this synchronous call may be slow."""
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
    """Use only when Context Pack lacks enough symbol-level call-path or impact detail."""
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


def _make_repository() -> Repository:
    container = get_container()
    return Repository(container.vector_store, container.embedder)


def _run_sync_project(
    *,
    repo_path: str,
    include_patterns: str | list[str] | None,
    exclude_patterns: str | list[str] | None,
    index_conventions: bool,
    conventions_path: str | None,
    graph_mode: str,
    graph_persistence: bool,
) -> dict[str, Any]:
    settings = get_container().settings
    snapshot = indexing.snapshot_project(
        repo_path,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        max_file_size_mb=settings.index_max_file_size_mb,
    )
    result = brain_index_project(
        repo_path=repo_path,
        index_conventions=index_conventions,
        conventions_path=conventions_path,
        graph_mode=graph_mode,
        graph_persistence=graph_persistence,
    )
    state = (
        indexing.record_index_state(repo_path, snapshot, result)
        if result.get("ok") is True
        else {"ok": False, "error": "index did not complete; state was not updated"}
    )
    return {
        "ok": result.get("ok") is True,
        "status": "synced" if result.get("ok") else "partial",
        "repo_path": repo_path,
        "snapshot": snapshot,
        "index": result,
        "state": state,
    }


def _milvus_status(settings: Settings) -> str:
    if settings.vector_store_backend != "milvus":
        return "available_when_configured"
    try:
        import pymilvus  # type: ignore[import-not-found]  # noqa: F401
    except Exception:
        return "missing_dependency"
    return "configured"


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


def _clean_text_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    if not isinstance(values, list):
        raise TypeError("value must be a list of strings")
    cleaned: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise TypeError("value must be a list of strings")
        stripped = value.strip()
        if stripped:
            cleaned.append(stripped)
    return cleaned


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
