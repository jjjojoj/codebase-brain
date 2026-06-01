"""Tests for the local dashboard payload and HTML shell."""

from __future__ import annotations

from codebrain.config import Settings
from codebrain.core.di import init_container
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
