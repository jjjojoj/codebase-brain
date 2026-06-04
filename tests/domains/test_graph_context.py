"""Behavior tests for graph Context Pack gathering."""

from __future__ import annotations

from typing import Any

from codebrain.domains.brain.graph_context import gather_graph_context


def test_gather_graph_context_degrades_when_adapter_is_missing() -> None:
    result = gather_graph_context(
        task="重构 auth 模块",
        adapter=None,
    )

    assert result["status"] == "missing"
    assert result["related_symbols"] == []
    assert "graph sidecar not available" in result["warnings"]


class RecordingAdapter:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def status(self) -> dict[str, Any]:
        return {"available": True}

    def search_graph(self, symbol: str, repo_path: str, limit: int) -> dict[str, Any]:
        self.queries.append(symbol)
        return {
            "ok": True,
            "data": {"results": [{"name": f"{symbol}Result"}]},
        }


def test_gather_graph_context_extracts_symbol_like_task_keywords() -> None:
    adapter = RecordingAdapter()

    result = gather_graph_context(
        task="understand the authentication flow in ModelBackend",
        top_k=5,
        adapter=adapter,
    )

    assert adapter.queries == ["ModelBackend", "authentication"]
    assert result["status"] == "ready"


def test_gather_graph_context_prefers_explicit_symbols() -> None:
    adapter = RecordingAdapter()

    gather_graph_context(
        task="understand the authentication flow",
        symbols=["BaseBackend", " ModelBackend "],
        top_k=5,
        adapter=adapter,
    )

    assert adapter.queries == ["BaseBackend", "ModelBackend"]
