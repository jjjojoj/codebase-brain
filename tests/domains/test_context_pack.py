"""Behavior tests for Context Pack assembly."""

from __future__ import annotations

from codebrain.domains.brain.context_pack import assemble_context_pack


def test_context_pack_keeps_local_context_when_graph_is_unavailable() -> None:
    local_context = {
        "status": {
            "conventions": "ready",
            "history": "ready",
            "memory": "ready",
        },
        "critical_conventions": [
            {
                "title": "Auth boundaries",
                "content": "Keep token refresh logic inside auth.",
                "similarity": 0.92,
            }
        ],
        "recent_changes": [
            {
                "file_path": "src/auth/tokens.py",
                "commit_hash": "abc123",
                "message": "Tighten refresh validation",
            }
        ],
        "similar_sessions": [
            {
                "task": "Refactor auth login flow",
                "decisions": "Kept session renewal in auth.",
            }
        ],
        "warnings": [],
    }

    pack = assemble_context_pack(
        task="重构 auth 模块的 token 刷新逻辑",
        local=local_context,
        graph=None,
    )

    assert pack["task"] == "重构 auth 模块的 token 刷新逻辑"
    assert pack["status"]["graph"] == "missing"
    assert pack["critical_conventions"] == local_context["critical_conventions"]
    assert pack["recent_changes"] == local_context["recent_changes"]
    assert pack["similar_sessions"] == local_context["similar_sessions"]
    assert pack["related_symbols"] == []
    assert "graph sidecar not available" in pack["warnings"]


def test_context_pack_returns_valid_empty_pack_when_all_sources_empty() -> None:
    pack = assemble_context_pack(
        task="重构 auth 模块",
        local=None,
        graph=None,
    )

    assert pack["critical_conventions"] == []
    assert pack["related_symbols"] == []
    assert pack["recent_changes"] == []
    assert pack["similar_sessions"] == []
    assert "graph sidecar not available" in pack["warnings"]
    assert "context pack has no results" in pack["warnings"]
    assert "run brain_index_project to index your repository" in pack["suggested_next_steps"]
    assert (
        "no context found for this task; try broader keywords or index conventions first"
        in pack["suggested_next_steps"]
    )


def test_context_pack_suggests_broader_keywords_when_local_context_is_empty() -> None:
    pack = assemble_context_pack(
        task="重构 auth 模块",
        local={
            "status": {"conventions": "empty", "history": "empty", "memory": "empty"},
            "critical_conventions": [],
            "recent_changes": [],
            "similar_sessions": [],
            "warnings": [],
        },
        graph={
            "status": "ready",
            "related_symbols": [{"name": "AuthService"}],
            "warnings": [],
        },
    )

    assert pack["related_symbols"] == [{"name": "AuthService"}]
    assert (
        "no context found for this task; try broader keywords or index conventions first"
        in pack["suggested_next_steps"]
    )


def test_context_pack_adds_task_checklist_for_common_omissions() -> None:
    pack = assemble_context_pack(
        task="Write a Django management command to export users as CSV",
        local={
            "status": {"conventions": "ready", "history": "empty", "memory": "empty"},
            "critical_conventions": [{"title": "Management commands"}],
            "recent_changes": [],
            "similar_sessions": [],
            "warnings": [],
        },
        graph={"status": "missing", "related_symbols": [], "warnings": []},
    )

    assert "ensure deterministic ordering (e.g. .order_by('id'))" in pack["suggested_next_steps"]
    assert "check requires_system_checks = [] for read-only commands" in pack["suggested_next_steps"]


def test_context_pack_adds_error_and_api_checklist_items() -> None:
    pack = assemble_context_pack(
        task="Fix FastAPI error handling for the report endpoint",
        local={"critical_conventions": [{"title": "API errors"}], "warnings": []},
        graph={"status": "ready", "related_symbols": [], "warnings": []},
    )

    assert (
        "avoid broad Exception unless intentionally documented"
        in pack["suggested_next_steps"]
    )
    assert "check response model, docstring, and version metadata" in pack["suggested_next_steps"]
