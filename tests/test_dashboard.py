"""Tests for the local dashboard payload and HTML shell."""

from __future__ import annotations

from pathlib import Path

from codebrain.config import Settings
from codebrain.core.di import init_container
from codebrain import dashboard
from codebrain.dashboard import build_dashboard_payload, render_dashboard_html


def test_dashboard_payload_contains_mcp_config(tmp_path) -> None:
    settings = Settings(
        db_path=str(tmp_path / "codebrain.db"),
        codebase_memory_binary="missing-cbm",
    )
    init_container(settings)
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")

    payload = build_dashboard_payload(settings, str(tmp_path))

    server = payload["mcp_config"]["mcpServers"]["codebase-brain"]
    assert server["args"] == ["serve"]
    assert server["env"]["CODEBRAIN_CODEBASE_MEMORY_BINARY"] == "missing-cbm"
    assert payload["status"]["graph"]["status"] == "missing"
    assert payload["sync"]["needs_sync"] is True


def test_dashboard_html_has_required_mount_points() -> None:
    html = render_dashboard_html()

    assert "Codebase Brain" in html
    assert "/api/status" in html
    assert 'id="mcp"' in html


def test_command_hint_prefers_installed_codebrain(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "installed" / "codebrain.exe"
    executable.parent.mkdir()
    executable.touch()
    monkeypatch.setattr(dashboard.sys, "executable", str(tmp_path / "python" / "python.exe"))
    monkeypatch.setattr(dashboard.shutil, "which", lambda name: str(executable))

    assert dashboard._command_hint() == str(executable.resolve())


def test_command_hint_prefers_current_virtualenv(monkeypatch, tmp_path) -> None:
    python = tmp_path / "python.exe"
    codebrain = tmp_path / "codebrain"
    codebrain.touch()
    monkeypatch.setattr(dashboard.sys, "executable", str(python))
    monkeypatch.setattr(dashboard.sys, "platform", "linux")
    monkeypatch.setattr(dashboard.shutil, "which", lambda name: "/other/codebrain")

    assert dashboard._command_hint() == str(codebrain)


def test_command_hint_ignores_python_module_path(monkeypatch, tmp_path) -> None:
    script = tmp_path / "cli.py"
    script.touch()
    monkeypatch.setattr(dashboard.shutil, "which", lambda name: None)
    monkeypatch.setattr(dashboard.sys, "executable", str(tmp_path / "python.exe"))
    monkeypatch.setattr(dashboard.sys, "argv", [str(script)])

    assert dashboard._command_hint() == "codebrain"
