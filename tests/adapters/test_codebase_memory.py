"""Tests for the codebase-memory-mcp sidecar adapter."""

from __future__ import annotations

import json
import subprocess

from codebrain.adapters import codebase_memory
from codebrain.adapters.codebase_memory import CodebaseMemoryAdapter, project_name_from_path


def test_missing_binary_returns_structured_error() -> None:
    adapter = CodebaseMemoryAdapter(binary="definitely-not-codebase-memory-mcp")

    result = adapter.index_repository(".")

    assert result["ok"] is False
    assert result["status"] == "missing"
    assert "CODEBRAIN_CODEBASE_MEMORY_BINARY" in result["error"]


def test_call_parses_mcp_text_envelope(monkeypatch) -> None:
    def fake_runner(command: list[str], timeout_sec: int) -> subprocess.CompletedProcess[str]:
        args = json.loads(command[3])
        assert command[:3] == ["/bin/cbm", "cli", "search_graph"]
        assert "project" in args
        assert "repo_path" not in args
        payload = {"results": [{"name": "OrderHandler"}], "total": 1}
        envelope = {"content": [{"type": "text", "text": json.dumps(payload)}]}
        return subprocess.CompletedProcess(command, 0, json.dumps(envelope), "")

    monkeypatch.setattr(codebase_memory, "_resolve_binary", lambda binary: "/bin/cbm")
    adapter = CodebaseMemoryAdapter(binary="cbm", runner=fake_runner)

    result = adapter.search_graph("OrderHandler", ".", limit=1)

    assert result["ok"] is True
    assert result["data"]["total"] == 1
    assert result["data"]["results"][0]["name"] == "OrderHandler"


def test_index_repository_passes_sidecar_mode(monkeypatch) -> None:
    def fake_runner(command: list[str], timeout_sec: int) -> subprocess.CompletedProcess[str]:
        args = json.loads(command[3])
        assert args["repo_path"]
        assert args["mode"] == "fast"
        assert args["persistence"] is True
        return subprocess.CompletedProcess(command, 0, '{"project":"demo"}', "")

    monkeypatch.setattr(codebase_memory, "_resolve_binary", lambda binary: "/bin/cbm")
    adapter = CodebaseMemoryAdapter(binary="cbm", runner=fake_runner)

    result = adapter.index_repository(".", mode="fast", persistence=True)

    assert result["ok"] is True
    assert result["data"]["project"] == "demo"


def test_call_escapes_unicode_paths_for_windows_command_line(monkeypatch) -> None:
    def fake_runner(command: list[str], timeout_sec: int) -> subprocess.CompletedProcess[str]:
        assert "工作区" not in command[3]
        assert "\\u5de5\\u4f5c\\u533a" in command[3]
        assert json.loads(command[3])["repo_path"] == r"D:\工作区\demo"
        return subprocess.CompletedProcess(command, 0, '{"project":"demo"}', "")

    monkeypatch.setattr(codebase_memory, "_resolve_binary", lambda binary: r"D:\cb\sidecar.exe")
    adapter = CodebaseMemoryAdapter(binary="cbm", runner=fake_runner)

    result = adapter.call("index_repository", {"repo_path": r"D:\工作区\demo"})

    assert result.ok is True


def test_nonzero_exit_returns_error_text(monkeypatch) -> None:
    def fake_runner(command: list[str], timeout_sec: int) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 2, "bad args", "failed")

    monkeypatch.setattr(codebase_memory, "_resolve_binary", lambda binary: "/bin/cbm")
    adapter = CodebaseMemoryAdapter(binary="cbm", runner=fake_runner)

    result = adapter.call("search_graph", {"project": "missing"})

    assert result.ok is False
    assert result.status == "error"
    assert result.text == "bad args"
    assert result.error == "failed"


def test_project_name_from_path_matches_sidecar_sanitizing() -> None:
    project = project_name_from_path("/Users/me/Documents/New project 8/codebase-brain")

    assert project == "Users-me-Documents-New-project-8-codebase-brain"
