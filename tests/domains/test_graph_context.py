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


def test_gather_graph_context_maps_chinese_code_terms() -> None:
    adapter = RecordingAdapter()

    gather_graph_context(
        task="理解 Django 用户认证和登录流程",
        top_k=5,
        adapter=adapter,
    )

    assert adapter.queries == [
        "authenticate",
        "authentication",
        "auth",
        "login",
    ]


class RankedAdapter:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def status(self) -> dict[str, Any]:
        return {"available": True}

    def search_graph(self, symbol: str, repo_path: str, limit: int) -> dict[str, Any]:
        self.queries.append(symbol)
        rows = {
            "authenticate": [
                {
                    "name": "AuthenticateTests",
                    "qualified_name": "tests.AuthenticateTests",
                    "label": "Class",
                    "file_path": "tests/test_auth.py",
                    "is_test": True,
                    "in_degree": 10,
                },
                {
                    "name": "authenticate",
                    "qualified_name": "django.contrib.auth.authenticate",
                    "label": "Function",
                    "file_path": "django/contrib/auth/__init__.py",
                    "in_degree": 20,
                },
            ],
            "login": [
                {
                    "name": "login",
                    "qualified_name": "django.contrib.auth.login",
                    "label": "Function",
                    "file_path": "django/contrib/auth/__init__.py",
                    "in_degree": 12,
                }
            ],
        }
        return {"ok": True, "data": {"results": rows[symbol]}}


def test_gather_graph_context_merges_and_ranks_all_symbol_queries() -> None:
    adapter = RankedAdapter()

    result = gather_graph_context(
        task="auth",
        symbols=["authenticate", "login"],
        top_k=2,
        adapter=adapter,
    )

    assert adapter.queries == ["authenticate", "login"]
    assert [row["name"] for row in result["related_symbols"]] == [
        "authenticate",
        "login",
    ]


def test_gather_graph_context_does_not_reserve_slots_for_nodes_without_source() -> None:
    adapter = RankedAdapter()
    original = adapter.search_graph

    def search_graph(symbol: str, repo_path: str, limit: int) -> dict[str, Any]:
        if symbol == "route":
            return {
                "ok": True,
                "data": {"results": [{"name": "/auth/", "file_path": "", "label": "Route"}]},
            }
        return original(symbol, repo_path, limit)

    adapter.search_graph = search_graph  # type: ignore[method-assign]

    result = gather_graph_context(
        task="auth",
        symbols=["authenticate", "route"],
        top_k=2,
        adapter=adapter,
    )

    assert all(row["name"] != "/auth/" for row in result["related_symbols"])
