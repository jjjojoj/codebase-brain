"""Optional graph-sidecar context gathering for Context Packs."""

from __future__ import annotations

import re
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

    related_symbols: list[dict[str, Any]] = []
    warnings: list[str] = []
    for query in _graph_queries(task, symbols):
        result = graph.search_graph(symbol=query, repo_path=repo_path, limit=top_k)
        if result.get("ok") is True:
            related_symbols.extend(_extract_symbols(query, result))
        else:
            warnings.append(f"graph search unavailable for {query}")
    related_symbols = _rank_and_dedupe(related_symbols)

    return {
        "status": "ready" if related_symbols else "empty",
        "related_symbols": related_symbols[:top_k],
        "warnings": warnings,
    }


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
    useful = _dedupe_text([*symbol_like, *mapped, *general])[:8]
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
    return exact, prefix, production, code_symbol, degree


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
