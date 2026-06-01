"""Tests for task-shaped brain tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from codebrain.domains.brain import tools as brain_tools


class FakeGraphAdapter:
    def status(self) -> dict[str, Any]:
        return {
            "available": True,
            "status": "ready",
            "binary": "fake-cbm",
            "resolved_binary": "/bin/fake-cbm",
        }

    def index_repository(
        self,
        repo_path: str,
        mode: str = "full",
        persistence: bool = False,
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "status": "ok",
            "tool": "index_repository",
            "data": {
                "project": Path(repo_path).name,
                "mode": mode,
                "persistence": persistence,
                "nodes": 10,
                "edges": 20,
            },
        }

    def search_graph(self, symbol: str, repo_path: str, limit: int = 5) -> dict[str, Any]:
        return {
            "ok": True,
            "status": "ok",
            "tool": "search_graph",
            "data": {"results": [{"name": symbol}], "total": 1},
        }

    def trace_call_path(self, symbol: str, repo_path: str, depth: int = 2) -> dict[str, Any]:
        return {
            "ok": True,
            "status": "ok",
            "tool": "trace_call_path",
            "data": {"function_name": symbol, "depth": depth, "paths": []},
        }


class MissingGraphAdapter(FakeGraphAdapter):
    def status(self) -> dict[str, Any]:
        return {
            "available": False,
            "status": "missing",
            "binary": "missing-cbm",
            "resolved_binary": "",
        }

    def index_repository(
        self,
        repo_path: str,
        mode: str = "full",
        persistence: bool = False,
    ) -> dict[str, Any]:
        return {"ok": False, "status": "missing", "tool": "index_repository"}

    def search_graph(self, symbol: str, repo_path: str, limit: int = 5) -> dict[str, Any]:
        return {"ok": False, "status": "missing", "tool": "search_graph"}

    def trace_call_path(self, symbol: str, repo_path: str, depth: int = 2) -> dict[str, Any]:
        return {"ok": False, "status": "missing", "tool": "trace_call_path"}


def test_brain_status_reports_graph_and_privacy(monkeypatch, container) -> None:
    monkeypatch.setattr(
        brain_tools,
        "_make_codebase_memory_adapter",
        lambda settings: MissingGraphAdapter(),
    )

    result = brain_tools.brain_status(".")

    assert result["profile"] == "composition-first"
    assert result["graph"]["status"] == "missing"
    assert result["privacy"]["cloud_embeddings_allowed"] is False
    assert "brain_index_project" in result["recommended_tools"]


def test_brain_index_project_combines_graph_and_conventions(monkeypatch, container) -> None:
    monkeypatch.setattr(
        brain_tools,
        "_make_codebase_memory_adapter",
        lambda settings: FakeGraphAdapter(),
    )
    monkeypatch.setattr(
        brain_tools.convention_tools,
        "index_convention_files",
        lambda path: {"ok": True, "path": path, "indexed": 2, "skipped": 0, "errors": []},
    )

    result = brain_tools.brain_index_project(
        repo_path=".",
        conventions_path="/tmp/rules",
        graph_mode="fast",
        graph_persistence=True,
    )

    assert result["ok"] is True
    assert result["status"] == "ok"
    assert result["graph"]["data"]["nodes"] == 10
    assert result["graph"]["data"]["mode"] == "fast"
    assert result["graph"]["data"]["persistence"] is True
    assert result["conventions"]["indexed"] == 2
    assert result["notes"] == []


def test_brain_index_project_degrades_when_graph_missing(monkeypatch, container) -> None:
    monkeypatch.setattr(
        brain_tools,
        "_make_codebase_memory_adapter",
        lambda settings: MissingGraphAdapter(),
    )
    monkeypatch.setattr(
        brain_tools.convention_tools,
        "index_convention_files",
        lambda path: {"ok": True, "path": path, "indexed": 0, "skipped": 0, "errors": []},
    )

    result = brain_tools.brain_index_project(repo_path=".")

    assert result["ok"] is True
    assert result["status"] == "partial"
    assert result["graph"]["status"] == "missing"
    assert result["notes"]


def test_brain_index_project_returns_convention_index_error(monkeypatch, container) -> None:
    monkeypatch.setattr(
        brain_tools,
        "_make_codebase_memory_adapter",
        lambda settings: FakeGraphAdapter(),
    )

    def fail_index(path: str) -> dict[str, Any]:
        raise ValueError("path must be a directory")

    monkeypatch.setattr(brain_tools.convention_tools, "index_convention_files", fail_index)

    result = brain_tools.brain_index_project(repo_path=".", conventions_path="/tmp/file.md")

    assert result["ok"] is True
    assert result["status"] == "partial"
    assert result["conventions"]["ok"] is False
    assert result["conventions"]["error"] == "path must be a directory"


def test_brain_explain_symbol_combines_graph_and_conventions(monkeypatch, container) -> None:
    monkeypatch.setattr(
        brain_tools,
        "_make_codebase_memory_adapter",
        lambda settings: FakeGraphAdapter(),
    )
    monkeypatch.setattr(
        brain_tools.convention_tools,
        "search_conventions",
        lambda query, top_k: [{"title": "Handlers", "content": "Keep handlers thin"}],
    )

    result = brain_tools.brain_explain_symbol("OrderHandler", depth=3, top_k=1)

    assert result["ok"] is True
    assert result["status"] == "ok"
    assert result["graph"]["search"]["data"]["results"][0]["name"] == "OrderHandler"
    assert result["graph"]["call_trace"]["data"]["depth"] == 3
    assert result["conventions"][0]["title"] == "Handlers"
