"""Behavior tests for graph Context Pack gathering."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import time
from typing import Any

from codebrain.domains.brain import graph_context
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
        self.limits: list[int] = []

    def status(self) -> dict[str, Any]:
        return {"available": True}

    def search_graph(self, symbol: str, repo_path: str, limit: int) -> dict[str, Any]:
        self.queries.append(symbol)
        self.limits.append(limit)
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
    assert adapter.limits == [25, 25]
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


def test_gather_graph_context_serializes_same_repository_queries() -> None:
    class ConcurrentAdapter(RecordingAdapter):
        def __init__(self) -> None:
            super().__init__()
            self.active = 0
            self.max_active = 0
            self.lock = Lock()

        def search_graph(self, symbol: str, repo_path: str, limit: int) -> dict[str, Any]:
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            time.sleep(0.01)
            with self.lock:
                self.active -= 1
            return {
                "ok": True,
                "data": {
                    "results": [
                        {"name": symbol, "file_path": f"src/{symbol}.py", "label": "Function"}
                    ]
                },
            }

    adapter = ConcurrentAdapter()
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda task: gather_graph_context(
                    task=task,
                    symbols=["auth"],
                    repo_path="/same/repo",
                    adapter=adapter,
                ),
                ["one", "two"],
            )
        )

    assert adapter.max_active == 1
    assert all(result["status"] == "ready" for result in results)
    assert any(result["timings"]["lock_wait_seconds"] > 0 for result in results)
    assert graph_context._repo_locks == {}


def test_repository_locks_are_released_after_distinct_queries() -> None:
    adapter = RecordingAdapter()

    for index in range(25):
        gather_graph_context(
            task="auth",
            symbols=["auth"],
            repo_path=f"/repo/{index}",
            adapter=adapter,
        )

    assert graph_context._repo_locks == {}


def test_repository_lock_is_released_after_wait_timeout(monkeypatch) -> None:
    key, lock = graph_context._claim_repo_lock("/busy/repo")
    lock.acquire()
    monkeypatch.setattr(graph_context, "_GRAPH_LOCK_WAIT_SECONDS", 0)

    result = gather_graph_context(
        task="auth",
        symbols=["auth"],
        repo_path="/busy/repo",
        adapter=RecordingAdapter(),
    )

    lock.release()
    graph_context._release_repo_lock(key)
    assert result["status"] == "busy"
    assert graph_context._repo_locks == {}


def test_gather_graph_context_stops_after_stage_budget(monkeypatch) -> None:
    class SlowAdapter(RecordingAdapter):
        def search_graph(self, symbol: str, repo_path: str, limit: int) -> dict[str, Any]:
            time.sleep(0.01)
            self.queries.append(symbol)
            return {"ok": False, "status": "timeout"}

    monkeypatch.setattr(graph_context, "_GRAPH_STAGE_BUDGET_SECONDS", 0.005)
    adapter = SlowAdapter()

    result = gather_graph_context(
        task="auth",
        symbols=["one", "two"],
        repo_path="/budget/repo",
        adapter=adapter,
    )

    assert adapter.queries == ["one"]
    assert "budget exhausted" in " ".join(result["warnings"])
