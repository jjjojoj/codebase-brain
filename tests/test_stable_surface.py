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


def test_server_instructions_define_automatic_tool_lifecycle() -> None:
    from codebrain import server

    instructions = server.mcp.instructions

    assert "without asking the user to name tools" in instructions
    assert "Before planning or editing code" in instructions
    assert "start one session automatically" in instructions
    assert "record only finalized decisions" in instructions
    assert "end the active session" in instructions


def test_all_stable_tool_descriptions_define_ai_decision_triggers() -> None:
    from codebrain import server

    expected = {
        "add_convention": "Use only",
        "brain_context_for_task": "Automatically call first",
        "brain_explain_symbol": "Use only when Context Pack lacks",
        "brain_index_job_status": "Automatically poll",
        "brain_index_project": "Use only for initial setup",
        "brain_status": "Use only for setup or diagnostics",
        "brain_sync_project": "Automatically refresh",
        "brain_sync_status": "Automatically check",
        "end_session": "Automatically call once",
        "get_blame": "Use only when Context Pack lacks",
        "get_co_changed_files": "Use only when Context Pack lacks",
        "get_recent_changes": "Use only when Context Pack lacks",
        "health": "Use only to diagnose",
        "index_convention_files": "Automatically use after",
        "list_conventions": "Use for convention maintenance or diagnostics",
        "recall_context": "Use only when Context Pack lacks",
        "record_decision": "Automatically record a finalized",
        "record_file_change": "Automatically record each meaningful",
        "record_problem": "Automatically record a solved",
        "search_conventions": "Use only when Context Pack lacks",
        "start_session": "Automatically call once after Context Pack",
    }

    tools = server.mcp._tool_manager._tools
    assert set(tools) == set(expected)
    for name, trigger in expected.items():
        assert trigger in tools[name].description


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
