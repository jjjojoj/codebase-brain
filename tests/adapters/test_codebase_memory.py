"""Tests for the codebase-memory-mcp sidecar adapter."""

from __future__ import annotations

import json
import subprocess

from codebrain.adapters import codebase_memory
from codebrain.adapters.codebase_memory import (
    CodebaseMemoryAdapter,
    legacy_project_name_from_path,
    project_name_aliases_from_path,
    project_name_from_path,
)


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


def test_search_graph_uses_short_search_timeout(monkeypatch) -> None:
    observed: list[int] = []

    def fake_runner(command: list[str], timeout_sec: int) -> subprocess.CompletedProcess[str]:
        observed.append(timeout_sec)
        return subprocess.CompletedProcess(command, 0, '{"results":[]}', "")

    monkeypatch.setattr(codebase_memory, "_resolve_binary", lambda binary: "/bin/cbm")
    adapter = CodebaseMemoryAdapter(
        binary="cbm",
        timeout_sec=120,
        search_timeout_sec=15,
        runner=fake_runner,
    )

    adapter.search_graph("OrderHandler", ".")
    adapter.index_repository(".")

    assert observed == [15, 120]


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


def test_call_preserves_long_windows_path(monkeypatch) -> None:
    long_path = "D:\\" + "\\".join(["deep"] * 70) + "\\项目"

    def fake_runner(command: list[str], timeout_sec: int) -> subprocess.CompletedProcess[str]:
        assert json.loads(command[3])["repo_path"] == long_path
        return subprocess.CompletedProcess(command, 0, '{"project":"demo"}', "")

    monkeypatch.setattr(codebase_memory, "_resolve_binary", lambda binary: r"D:\cb\sidecar.exe")
    adapter = CodebaseMemoryAdapter(binary="cbm", runner=fake_runner)

    assert adapter.call("index_repository", {"repo_path": long_path}).ok is True


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


def test_project_name_from_path_matches_sidecar_sanitizing(monkeypatch) -> None:
    monkeypatch.setattr(
        codebase_memory,
        "_resolve_path",
        lambda path: "/Users/me/Documents/New project 8/codebase-brain",
    )

    project = project_name_from_path("/Users/me/Documents/New project 8/codebase-brain")

    assert project == "Users-me-Documents-New project 8-codebase-brain"


def test_project_name_aliases_include_space_normalized_name(monkeypatch) -> None:
    monkeypatch.setattr(
        codebase_memory,
        "_resolve_path",
        lambda path: "/Users/me/Documents/New project 8/codebase-brain",
    )

    assert project_name_aliases_from_path(
        "/Users/me/Documents/New project 8/codebase-brain"
    ) == [
        "Users-me-Documents-New project 8-codebase-brain",
        "Users-me-Documents-New-project-8-codebase-brain",
    ]


def test_project_name_from_path_preserves_unicode_path_segments(monkeypatch) -> None:
    monkeypatch.setattr(
        codebase_memory,
        "_resolve_path",
        lambda path: r"D:\qoder工作区\django-test",
    )

    project = project_name_from_path(r"D:\qoder工作区\django-test")

    assert project == "D-qoder工作区-django-test"


def test_project_name_aliases_include_legacy_ascii_name(monkeypatch) -> None:
    monkeypatch.setattr(
        codebase_memory,
        "_resolve_path",
        lambda path: r"D:\qoder工作区\django-test",
    )

    assert project_name_aliases_from_path(r"D:\qoder工作区\django-test") == [
        "D-qoder工作区-django-test",
        "D-qoder-django-test",
    ]
    assert legacy_project_name_from_path(r"D:\qoder工作区\django-test") == (
        "D-qoder-django-test"
    )


def test_project_name_aliases_preserve_windows_spaces_and_unicode(monkeypatch) -> None:
    monkeypatch.setattr(
        codebase_memory,
        "_resolve_path",
        lambda path: r"D:\qoder工作区\New project 8\django-test",
    )

    assert project_name_aliases_from_path(
        r"D:\qoder工作区\New project 8\django-test"
    ) == [
        "D-qoder工作区-New project 8-django-test",
        "D-qoder工作区-New-project-8-django-test",
        "D-qoder-New-project-8-django-test",
    ]


def test_search_graph_falls_back_to_legacy_project_alias(monkeypatch) -> None:
    observed_projects: list[str] = []

    def fake_runner(command: list[str], timeout_sec: int) -> subprocess.CompletedProcess[str]:
        args = json.loads(command[3])
        observed_projects.append(args["project"])
        if args["project"] == "D-qoder工作区-django-test":
            return subprocess.CompletedProcess(command, 0, '{"results":[],"total":0}', "")
        return subprocess.CompletedProcess(
            command,
            0,
            '{"results":[{"name":"AuthService"}],"total":1}',
            "",
        )

    monkeypatch.setattr(codebase_memory, "_resolve_binary", lambda binary: "/bin/cbm")
    monkeypatch.setattr(
        codebase_memory,
        "_resolve_path",
        lambda path: r"D:\qoder工作区\django-test",
    )
    adapter = CodebaseMemoryAdapter(binary="cbm", runner=fake_runner)

    result = adapter.search_graph("AuthService", r"D:\qoder工作区\django-test")

    assert observed_projects == [
        "D-qoder工作区-django-test",
        "D-qoder-django-test",
    ]
    assert result["ok"] is True
    assert result["data"]["results"][0]["name"] == "AuthService"
    assert result["data"]["project_alias_used"] == "D-qoder-django-test"


def test_search_graph_falls_back_to_space_normalized_project_alias(monkeypatch) -> None:
    observed_projects: list[str] = []

    def fake_runner(command: list[str], timeout_sec: int) -> subprocess.CompletedProcess[str]:
        args = json.loads(command[3])
        observed_projects.append(args["project"])
        if args["project"] == "Users-me-Documents-New project 8-codebase-brain":
            return subprocess.CompletedProcess(command, 2, "", "project not found")
        return subprocess.CompletedProcess(
            command,
            0,
            '{"results":[{"name":"brain_context_for_task"}],"total":1}',
            "",
        )

    monkeypatch.setattr(codebase_memory, "_resolve_binary", lambda binary: "/bin/cbm")
    monkeypatch.setattr(
        codebase_memory,
        "_resolve_path",
        lambda path: "/Users/me/Documents/New project 8/codebase-brain",
    )
    adapter = CodebaseMemoryAdapter(binary="cbm", runner=fake_runner)

    result = adapter.search_graph(
        "brain_context_for_task", "/Users/me/Documents/New project 8/codebase-brain"
    )

    assert observed_projects == [
        "Users-me-Documents-New project 8-codebase-brain",
        "Users-me-Documents-New-project-8-codebase-brain",
    ]
    assert result["ok"] is True
    assert result["data"]["results"][0]["name"] == "brain_context_for_task"
    assert result["data"]["project_alias_used"] == (
        "Users-me-Documents-New-project-8-codebase-brain"
    )


def test_trace_call_path_falls_back_after_project_error(monkeypatch) -> None:
    observed_projects: list[str] = []

    def fake_runner(command: list[str], timeout_sec: int) -> subprocess.CompletedProcess[str]:
        args = json.loads(command[3])
        observed_projects.append(args["project"])
        if args["project"] == "D-qoder工作区-django-test":
            return subprocess.CompletedProcess(command, 2, "", "project not found")
        return subprocess.CompletedProcess(
            command,
            0,
            '{"paths":[{"caller":"view","callee":"AuthService"}]}',
            "",
        )

    monkeypatch.setattr(codebase_memory, "_resolve_binary", lambda binary: "/bin/cbm")
    monkeypatch.setattr(
        codebase_memory,
        "_resolve_path",
        lambda path: r"D:\qoder工作区\django-test",
    )
    adapter = CodebaseMemoryAdapter(binary="cbm", runner=fake_runner)

    result = adapter.trace_call_path("AuthService", r"D:\qoder工作区\django-test")

    assert observed_projects == [
        "D-qoder工作区-django-test",
        "D-qoder-django-test",
    ]
    assert result["ok"] is True
    assert result["data"]["paths"][0]["callee"] == "AuthService"


def test_index_repository_uses_configured_repo_alias(monkeypatch) -> None:
    observed_repo_paths: list[str] = []

    def fake_runner(command: list[str], timeout_sec: int) -> subprocess.CompletedProcess[str]:
        args = json.loads(command[3])
        observed_repo_paths.append(args["repo_path"])
        return subprocess.CompletedProcess(command, 0, '{"project":"D-projects-django-test"}', "")

    monkeypatch.setattr(codebase_memory, "_resolve_binary", lambda binary: "/bin/cbm")
    monkeypatch.setattr(codebase_memory, "_resolve_path", lambda path: path)
    adapter = CodebaseMemoryAdapter(
        binary="cbm",
        repo_aliases={r"D:\qoder工作区\django-test": r"D:\projects\django-test"},
        runner=fake_runner,
    )

    result = adapter.index_repository(r"D:\qoder工作区\django-test", mode="fast")

    assert observed_repo_paths == [r"D:\projects\django-test"]
    assert result["ok"] is True


def test_search_graph_uses_configured_repo_alias_project(monkeypatch) -> None:
    observed_projects: list[str] = []

    def fake_runner(command: list[str], timeout_sec: int) -> subprocess.CompletedProcess[str]:
        args = json.loads(command[3])
        observed_projects.append(args["project"])
        if args["project"] == "D-projects-django-test":
            return subprocess.CompletedProcess(
                command,
                0,
                '{"results":[{"name":"authenticate"}],"total":1}',
                "",
            )
        return subprocess.CompletedProcess(command, 0, '{"results":[],"total":0}', "")

    monkeypatch.setattr(codebase_memory, "_resolve_binary", lambda binary: "/bin/cbm")
    monkeypatch.setattr(codebase_memory, "_resolve_path", lambda path: path)
    adapter = CodebaseMemoryAdapter(
        binary="cbm",
        repo_aliases=r"D:\qoder工作区\django-test=D:\projects\django-test",
        runner=fake_runner,
    )

    result = adapter.search_graph("authenticate", r"D:\qoder工作区\django-test")

    assert observed_projects == [
        "D-qoder工作区-django-test",
        "D-qoder-django-test",
        "D-projects-django-test",
    ]
    assert result["ok"] is True
    assert result["data"]["project_alias_used"] == "D-projects-django-test"
    assert result["data"]["results"][0]["name"] == "authenticate"
