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
    assert result["privacy"]["embedding_policy"] == "local_only"
    assert result["privacy"]["supported_embedding_providers"] == [
        "sentence-transformers",
        "ollama",
    ]
    assert result["resources"]["embedder_device"] == "cpu"
    assert result["resources"]["embedding_model_loaded"] is False
    assert result["primary_tool"] == "brain_context_for_task"
    assert "brain_context_for_task" in result["recommended_tools"]
    assert "get_recent_changes" in result["deep_dive_tools"]
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


def test_brain_sync_status_uses_file_snapshot(tmp_path, container) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")

    result = brain_tools.brain_sync_status(str(tmp_path))

    assert result["ok"] is True
    assert result["needs_sync"] is True
    assert result["snapshot"]["file_count"] == 1


def test_brain_sync_project_runs_sync_and_records_state(monkeypatch, tmp_path, container) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    monkeypatch.setattr(
        brain_tools,
        "_make_codebase_memory_adapter",
        lambda settings: FakeGraphAdapter(),
    )
    monkeypatch.setattr(
        brain_tools.convention_tools,
        "index_convention_files",
        lambda path: {"ok": True, "path": path, "indexed": 0, "skipped": 0, "errors": []},
    )

    result = brain_tools.brain_sync_project(str(tmp_path), async_mode=False)
    status = brain_tools.brain_sync_status(str(tmp_path))

    assert result["ok"] is True
    assert result["status"] == "synced"
    assert result["result"]["state"]["ok"] is True
    assert status["needs_sync"] is False


def test_brain_sync_project_does_not_record_failed_index(monkeypatch, tmp_path, container) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    monkeypatch.setattr(
        brain_tools,
        "_make_codebase_memory_adapter",
        lambda settings: MissingGraphAdapter(),
    )

    result = brain_tools.brain_sync_project(
        str(tmp_path),
        async_mode=False,
        index_conventions=False,
    )
    status = brain_tools.brain_sync_status(str(tmp_path))

    assert result["ok"] is False
    assert result["result"]["state"]["ok"] is False
    assert status["needs_sync"] is True


def test_brain_index_job_status_lists_jobs() -> None:
    result = brain_tools.brain_index_job_status()

    assert result["ok"] is True
    assert "jobs" in result


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


def test_brain_context_for_task_assembles_local_and_graph_context(
    monkeypatch,
    container,
) -> None:
    repository = object()
    graph_adapter = MissingGraphAdapter()
    monkeypatch.setattr(brain_tools, "_make_repository", lambda: repository)
    monkeypatch.setattr(
        brain_tools,
        "_make_codebase_memory_adapter",
        lambda settings: graph_adapter,
    )

    def fake_local_context(**kwargs: Any) -> dict[str, Any]:
        assert kwargs["repository"] is repository
        return {
            "status": {"conventions": "ready", "history": "ready", "memory": "ready"},
            "critical_conventions": [{"title": "Auth boundaries"}],
            "recent_changes": [{"file_path": "src/auth/tokens.py"}],
            "similar_sessions": [{"task": "Auth refactor"}],
            "warnings": [],
        }

    def fake_graph_context(**kwargs: Any) -> dict[str, Any]:
        assert kwargs["adapter"] is graph_adapter
        return {
            "status": "missing",
            "related_symbols": [],
            "warnings": ["graph sidecar not available"],
        }

    monkeypatch.setattr(
        brain_tools.local_context,
        "gather_local_context",
        fake_local_context,
    )
    monkeypatch.setattr(
        brain_tools.graph_context,
        "gather_graph_context",
        fake_graph_context,
    )

    result = brain_tools.brain_context_for_task(
        "重构 auth 模块的 token 刷新逻辑",
        files=["src/auth/tokens.py"],
        symbols=["TokenService"],
        top_k=3,
        async_mode=False,
    )

    assert result["task"] == "重构 auth 模块的 token 刷新逻辑"
    assert result["status"]["graph"] == "missing"
    assert result["critical_conventions"][0]["title"] == "Auth boundaries"
    assert result["related_symbols"] == []
    assert "graph sidecar not available" in result["warnings"]


def test_brain_context_for_task_defaults_to_async(monkeypatch, container) -> None:
    monkeypatch.setattr(
        brain_tools,
        "_build_context_pack",
        lambda **kwargs: {"task": kwargs["task"], "status": "ready"},
    )

    result = brain_tools.brain_context_for_task("inspect auth")

    assert result["status"] == "queued"
    assert result["job"]["description"].startswith("context-pack")


def test_brain_context_for_task_infers_files_for_git_context(
    monkeypatch,
    container,
) -> None:
    monkeypatch.setattr(brain_tools, "_make_repository", lambda: object())
    monkeypatch.setattr(
        brain_tools,
        "_make_codebase_memory_adapter",
        lambda settings: FakeGraphAdapter(),
    )
    monkeypatch.setattr(
        brain_tools.graph_context,
        "gather_graph_context",
        lambda **kwargs: {
            "status": "ready",
            "related_symbols": [{"name": "login", "file_path": "src/auth/login.py"}],
            "warnings": [],
        },
    )

    def fake_local_context(**kwargs: Any) -> dict[str, Any]:
        assert kwargs["files"] == ["src/auth/login.py"]
        return {
            "status": {"history": "ready"},
            "context_files": kwargs["files"],
            "recent_changes": [{"file_path": "src/auth/login.py"}],
            "co_changed_files": [{"file": "tests/test_login.py"}],
            "blame": [{"file_path": "src/auth/login.py", "line": 1}],
            "warnings": [],
        }

    monkeypatch.setattr(
        brain_tools.local_context,
        "gather_local_context",
        fake_local_context,
    )

    result = brain_tools.brain_context_for_task(
        "fix login",
        async_mode=False,
    )

    assert result["context_files"] == ["src/auth/login.py"]
    assert result["recent_changes"]
    assert result["co_changed_files"]
    assert result["blame"]
