"""Tests for the stable MVP server surface."""

from __future__ import annotations

import importlib

import pytest

from codebrain.domains.history import tools as history_tools


def test_stable_mcp_surface_excludes_git_history_vector_tools() -> None:
    """The stable MCP server should expose only safe git read-only tools."""
    from codebrain import server

    tools = set(server.mcp._tool_manager._tools)

    assert "brain_context_for_task" in tools
    assert "brain_status" in tools
    assert "brain_sync_status" in tools
    assert "brain_sync_project" in tools
    assert "brain_index_job_status" in tools
    assert "brain_index_project" in tools
    assert "brain_explain_symbol" in tools
    assert "get_blame" in tools
    assert "get_recent_changes" in tools
    assert "get_co_changed_files" in tools
    assert "index_git_history" not in tools
    assert "search_history" not in tools


def test_git_history_vector_tools_register_only_when_flag_enabled(monkeypatch) -> None:
    """Semantic git history tools should be an explicit feature-flag surface."""
    from codebrain import server

    monkeypatch.setenv("CODEBRAIN_GIT_HISTORY_INDEX_ENABLED", "true")
    enabled_server = importlib.reload(server)

    tools = set(enabled_server.mcp._tool_manager._tools)

    assert "index_git_history" in tools
    assert "search_history" in tools

    monkeypatch.delenv("CODEBRAIN_GIT_HISTORY_INDEX_ENABLED")
    importlib.reload(server)


def test_git_history_vector_indexing_fails_closed() -> None:
    """Direct wrapper calls should also reject disabled history indexing."""
    with pytest.raises(RuntimeError, match="Git history vector indexing is disabled"):
        history_tools.index_git_history(".", max_commits=1)

    with pytest.raises(RuntimeError, match="Git history vector indexing is disabled"):
        history_tools.search_history("auth")
