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
        if len(related_symbols) >= top_k:
            break

    return {
        "status": "ready" if related_symbols else "empty",
        "related_symbols": related_symbols[:top_k],
        "warnings": warnings,
    }


def _graph_queries(task: str, symbols: list[str] | None) -> list[str]:
    queries = [symbol.strip() for symbol in symbols or [] if symbol.strip()]
    if queries:
        return queries

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
    useful = [*symbol_like, *general][:5]
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
