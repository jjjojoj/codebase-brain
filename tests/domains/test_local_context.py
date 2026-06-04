"""Behavior tests for local-only Context Pack gathering."""

from __future__ import annotations

from typing import Any

from codebrain.core.repository import Repository
from codebrain.domains.brain import local_context


def test_gather_local_context_uses_repository_for_vector_sources(
    monkeypatch,
    repository: Repository,
    tmp_path,
) -> None:
    repository.add_convention(
        "auth",
        "Auth boundaries",
        "Keep token refresh logic inside auth.",
        record_id="conv-auth",
    )
    repository.insert_session(
        task="Refactor auth login",
        files_modified='["src/auth/login.py"]',
        decisions='["Keep token refresh in auth"]',
        assumptions="",
        problems="[]",
        record_id="session-auth",
    )

    def fake_recent_changes(
        repo_path: str,
        file_path: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        assert repo_path == str(tmp_path)
        assert file_path == "src/auth/tokens.py"
        assert limit == 5
        return [{"commit_hash": "abc123", "commit_msg": "Tighten refresh validation"}]

    def fake_co_changed(repo_path, file_path, limit, max_commits):
        assert max_commits == 50
        return [{"file": "tests/auth/test_tokens.py", "co_change_count": 4}]

    def fake_blame(repo_path, file_path, start, end):
        assert (start, end) == (1, 2)
        return [{"line": 1, "commit_hash": "abc123", "author": "Dev"}]

    monkeypatch.setattr(local_context.git_indexer, "get_recent_changes", fake_recent_changes)
    monkeypatch.setattr(local_context.git_indexer, "get_co_changed", fake_co_changed)
    monkeypatch.setattr(local_context.git_indexer, "get_blame_info", fake_blame)
    target = tmp_path / "src" / "auth" / "tokens.py"
    target.parent.mkdir(parents=True)
    target.write_text("one\ntwo\n", encoding="utf-8")

    result = local_context.gather_local_context(
        task="重构 auth token refresh",
        files=["src/auth/tokens.py"],
        repo_path=str(tmp_path),
        top_k=5,
        repository=repository,
    )

    assert result["status"]["conventions"] == "ready"
    assert result["status"]["memory"] == "ready"
    assert result["status"]["history"] == "ready"
    assert result["critical_conventions"][0]["id"] == "conv-auth"
    assert result["similar_sessions"][0]["session_id"] == "session-auth"
    assert result["recent_changes"][0]["file_path"] == "src/auth/tokens.py"
    assert result["co_changed_files"][0]["source_file"] == "src/auth/tokens.py"
    assert result["blame"][0]["file_path"] == "src/auth/tokens.py"


def test_select_context_files_prefers_explicit_then_graph_sources() -> None:
    result = local_context.select_context_files(
        ["src/auth/service.py"],
        {
            "related_symbols": [
                {"file_path": "src/auth/service.py"},
                {"file_path": "src/auth/models.py"},
                {"file_path": "tests/test_auth.py"},
            ]
        },
        limit=2,
    )

    assert result == ["src/auth/service.py", "src/auth/models.py"]


def test_gather_local_context_degrades_without_repository() -> None:
    result = local_context.gather_local_context(
        task="重构 auth token refresh",
        repository=None,
    )

    assert result["critical_conventions"] == []
    assert result["similar_sessions"] == []
    assert "repository unavailable for local vector context" in result["warnings"]
