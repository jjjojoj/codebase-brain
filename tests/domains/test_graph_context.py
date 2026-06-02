"""Behavior tests for graph Context Pack gathering."""

from __future__ import annotations

from codebrain.domains.brain.graph_context import gather_graph_context


def test_gather_graph_context_degrades_when_adapter_is_missing() -> None:
    result = gather_graph_context(
        task="重构 auth 模块",
        adapter=None,
    )

    assert result["status"] == "missing"
    assert result["related_symbols"] == []
    assert "graph sidecar not available" in result["warnings"]
