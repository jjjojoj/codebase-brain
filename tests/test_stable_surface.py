"""Tests for the stable MVP server surface."""

from __future__ import annotations

import pytest

from codebrain.domains.history import tools as history_tools


def test_stable_mcp_surface_excludes_git_history_vector_tools() -> None:
    """The stable MCP server should expose only safe git read-only tools."""
    from codebrain import server

    tools = set(server.mcp._tool_manager._tools)

    assert "get_blame" in tools
    assert "get_recent_changes" in tools
    assert "get_co_changed_files" in tools
    assert "index_git_history" not in tools
    assert "search_history" not in tools


def test_git_history_vector_indexing_fails_closed() -> None:
    """Direct wrapper calls should also reject disabled history indexing."""
    with pytest.raises(RuntimeError, match="Git history vector indexing is disabled"):
        history_tools.index_git_history(".", max_commits=1)

    with pytest.raises(RuntimeError, match="Git history vector indexing is disabled"):
        history_tools.search_history("auth")
