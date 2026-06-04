"""Optional graph-sidecar context gathering for Context Packs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from threading import Lock
import time
from typing import Any

from codebrain.adapters.codebase_memory import CodebaseMemoryAdapter


_TASK_QUERY_STOPWORDS = {
    "add",
    "build",
    "change",
    "check",
    "create",
    "debug",
    "explain",
    "fix",
    "flow",
    "for",
    "from",
    "implement",
    "inspect",
    "into",
    "logic",
    "module",
    "refactor",
    "remove",
    "the",
    "understand",
    "update",
    "with",
}

_TASK_TERM_MAPPINGS = {
    "认证": ["authenticate", "authentication", "auth"],
    "登录": ["login"],
}

_GRAPH_LOCK_WAIT_SECONDS = 30
_GRAPH_STAGE_BUDGET_SECONDS = 45
@dataclass
class _RepoLockEntry:
    lock: Lock = field(default_factory=Lock)
    users: int = 0


_repo_locks: dict[str, _RepoLockEntry] = {}
_repo_locks_guard = Lock()


def gather_graph_context(
    *,
    task: str,
    symbols: list[str] | None = None,
    repo_path: str = ".",
    top_k: int = 5,
    adapter: CodebaseMemoryAdapter | None = None,
) -> dict[str, Any]:
    """Gather graph symbols through codebase-memory-mcp when available."""
    if adapter is None:
        return {
            "status": "missing",
            "related_symbols": [],
            "warnings": ["graph sidecar not available"],
        }
    graph = adapter
    status = graph.status()
    if not status.get("available"):
        return {
            "status": "missing",
            "related_symbols": [],
            "warnings": ["graph sidecar not available"],
        }

    lock_key, lock = _claim_repo_lock(repo_path)
    wait_started = time.perf_counter()
    acquired = lock.acquire(timeout=_GRAPH_LOCK_WAIT_SECONDS)
    lock_wait_seconds = round(time.perf_counter() - wait_started, 3)
    if not acquired:
        _release_repo_lock(lock_key)
        return {
            "status": "busy",
            "related_symbols": [],
            "warnings": [
                f"graph context busy for {repo_path}; skipped after "
                f"{lock_wait_seconds}s lock wait"
            ],
            "timings": {"lock_wait_seconds": lock_wait_seconds, "query_seconds": 0.0},
        }

    try:
        return _gather_locked(
            graph=graph,
            task=task,
            symbols=symbols,
            repo_path=repo_path,
            top_k=top_k,
            lock_wait_seconds=lock_wait_seconds,
        )
    finally:
        lock.release()
        _release_repo_lock(lock_key)


def _gather_locked(
    *,
    graph: CodebaseMemoryAdapter,
    task: str,
    symbols: list[str] | None,
    repo_path: str,
    top_k: int,
    lock_wait_seconds: float,
) -> dict[str, Any]:
    queries = _graph_queries(task, symbols)
    related_symbols: list[dict[str, Any]] = []
    warnings: list[str] = []
    query_timings: list[dict[str, Any]] = []
    candidate_limit = min(max(top_k * 5, 25), 50)
    query_started = time.perf_counter()
    for query in queries:
        elapsed = time.perf_counter() - query_started
        if elapsed >= _GRAPH_STAGE_BUDGET_SECONDS:
            warnings.append(
                f"graph context budget exhausted after {round(elapsed, 3)}s; "
                "remaining queries skipped"
            )
            break
        item_started = time.perf_counter()
        result = graph.search_graph(symbol=query, repo_path=repo_path, limit=candidate_limit)
        query_timings.append({
            "query": query,
            "status": result.get("status", "unknown"),
            "seconds": round(time.perf_counter() - item_started, 3),
        })
        if result.get("ok") is True:
            related_symbols.extend(_extract_symbols(query, result))
        else:
            status = result.get("status", "error")
            warnings.append(f"graph search {status} for {query}")
    query_seconds = round(time.perf_counter() - query_started, 3)
    related_symbols = _select_diverse(_rank_and_dedupe(related_symbols), queries, top_k)

    return {
        "status": "ready" if related_symbols else "empty",
        "related_symbols": related_symbols[:top_k],
        "warnings": warnings,
        "timings": {
            "lock_wait_seconds": lock_wait_seconds,
            "query_seconds": query_seconds,
            "queries": query_timings,
        },
    }


def _claim_repo_lock(repo_path: str) -> tuple[str, Lock]:
    key = str(repo_path).lower()
    with _repo_locks_guard:
        entry = _repo_locks.setdefault(key, _RepoLockEntry())
        entry.users += 1
        return key, entry.lock


def _release_repo_lock(key: str) -> None:
    with _repo_locks_guard:
        entry = _repo_locks.get(key)
        if entry is None:
            return
        entry.users -= 1
        if entry.users == 0:
            _repo_locks.pop(key, None)


def _graph_queries(task: str, symbols: list[str] | None) -> list[str]:
    queries = [symbol.strip() for symbol in symbols or [] if symbol.strip()]
    if queries:
        return _dedupe_text(queries)

    candidates = re.findall(r"[A-Za-z_][A-Za-z0-9_.]*", task)
    symbol_like: list[str] = []
    general: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = candidate.strip("._")
        lowered = normalized.lower()
        if len(normalized) < 3 or lowered in _TASK_QUERY_STOPWORDS or lowered in seen:
            continue
        target = symbol_like if _looks_symbol_like(normalized) else general
        target.append(normalized)
        seen.add(lowered)
    mapped = [
        query
        for term, queries in _TASK_TERM_MAPPINGS.items()
        if term in task
        for query in queries
    ]
    useful = _dedupe_text([*symbol_like, *mapped, *(general if not mapped else [])])[:8]
    return useful or [task]


def _looks_symbol_like(value: str) -> bool:
    return any(char.isupper() for char in value[1:]) or "_" in value or "." in value


def _extract_symbols(query: str, result: dict[str, Any]) -> list[dict[str, Any]]:
    data = result.get("data")
    if not isinstance(data, dict):
        return []
    rows = data.get("results")
    if not isinstance(rows, list):
        return []
    extracted: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            extracted.append({"query": query, **row})
    return extracted


def _rank_and_dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row.get("qualified_name") or row.get("name") or row)
        current = best.get(key)
        if current is None or _symbol_score(row) > _symbol_score(current):
            best[key] = row
    return sorted(best.values(), key=_symbol_score, reverse=True)


def _symbol_score(row: dict[str, Any]) -> tuple[int, int, int, int, int]:
    query = str(row.get("query", "")).lower()
    name = str(row.get("name", "")).lower()
    label = str(row.get("label", "")).lower()
    file_path = str(row.get("file_path", "")).lower()
    exact = int(name == query)
    prefix = int(name.startswith(query))
    production = int(not row.get("is_test") and "/test" not in file_path)
    code_symbol = int(label in {"function", "method", "class"})
    degree = _as_int(row.get("in_degree")) * 2 + _as_int(row.get("out_degree"))
    return exact, production, code_symbol, prefix, degree


def _select_diverse(
    ranked: list[dict[str, Any]],
    queries: list[str],
    top_k: int,
) -> list[dict[str, Any]]:
    source_rows = [row for row in ranked if _has_source_location(row)]
    if source_rows:
        ranked = source_rows
    selected: list[dict[str, Any]] = []
    selected_keys: set[str] = set()
    for query in queries:
        match = next(
            (
                row
                for row in ranked
                if str(row.get("query", "")).lower() == query.lower()
                and _has_source_location(row)
            ),
            None,
        )
        if match is not None:
            _append_unique(selected, selected_keys, match)
        if len(selected) >= top_k:
            return sorted(selected, key=_symbol_score, reverse=True)
    for row in ranked:
        _append_unique(selected, selected_keys, row)
        if len(selected) >= top_k:
            break
    return sorted(selected, key=_symbol_score, reverse=True)


def _append_unique(
    selected: list[dict[str, Any]],
    selected_keys: set[str],
    row: dict[str, Any],
) -> None:
    key = str(row.get("qualified_name") or row.get("name") or row)
    if key not in selected_keys:
        selected.append(row)
        selected_keys.add(key)


def _has_source_location(row: dict[str, Any]) -> bool:
    return bool(str(row.get("file_path", "")).strip())


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _dedupe_text(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        lowered = normalized.lower()
        if normalized and lowered not in seen:
            result.append(normalized)
            seen.add(lowered)
    return result
