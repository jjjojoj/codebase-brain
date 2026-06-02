"""Behavior tests for local-only Context Pack gathering."""

from __future__ import annotations

from typing import Any

from codebrain.core.repository import Repository
from codebrain.domains.brain import local_context


def test_gather_local_context_uses_repository_for_vector_sources(
    monkeypatch,
    repository: Repository,
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
        assert repo_path == "/repo"
        assert file_path == "src/auth/tokens.py"
        assert limit == 5
        return [{"commit_hash": "abc123", "commit_msg": "Tighten refresh validation"}]

    monkeypatch.setattr(local_context.git_indexer, "get_recent_changes", fake_recent_changes)

    result = local_context.gather_local_context(
        task="重构 auth token refresh",
        files=["src/auth/tokens.py"],
        repo_path="/repo",
        top_k=5,
        repository=repository,
    )

    assert result["status"]["conventions"] == "ready"
    assert result["status"]["memory"] == "ready"
    assert result["status"]["history"] == "ready"
    assert result["critical_conventions"][0]["id"] == "conv-auth"
    assert result["similar_sessions"][0]["session_id"] == "session-auth"
    assert result["recent_changes"][0]["file_path"] == "src/auth/tokens.py"


def test_gather_local_context_degrades_without_repository() -> None:
    result = local_context.gather_local_context(
        task="重构 auth token refresh",
        repository=None,
    )

    assert result["critical_conventions"] == []
    assert result["similar_sessions"] == []
    assert "repository unavailable for local vector context" in result["warnings"]
