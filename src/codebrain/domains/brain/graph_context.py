"""Optional graph-sidecar context gathering for Context Packs."""

from __future__ import annotations

from typing import Any

from codebrain.adapters.codebase_memory import CodebaseMemoryAdapter


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
    return [task]


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
