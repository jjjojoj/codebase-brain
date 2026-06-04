"""Repository behavior tests."""

from __future__ import annotations

from codebrain.core.repository import Repository


def test_empty_searches_do_not_load_embedder(sqlite_store) -> None:
    class FailEmbedder:
        def embed(self, text: str) -> list[float]:
            raise AssertionError("empty collections must not load or call the embedder")

    repository = Repository(sqlite_store, FailEmbedder())

    assert repository.search_conventions("auth") == []
    assert repository.search_sessions("auth") == []
    assert repository.search_history("auth") == []


def test_repository_adds_searches_and_lists_conventions(
    repository: Repository,
) -> None:
    record_id = repository.add_convention(
        "auth",
        "Auth boundaries",
        "Keep token refresh logic inside auth.",
        record_id="conv-auth",
    )

    results = repository.search_conventions("token refresh", top_k=1)
    listed = repository.list_conventions(module="auth")

    assert record_id == "conv-auth"
    assert results[0]["id"] == "conv-auth"
    assert results[0]["module"] == "auth"
    assert listed[0]["id"] == "conv-auth"
    assert listed[0]["title"] == "Auth boundaries"


def test_repository_inserts_and_recalls_sessions(repository: Repository) -> None:
    record_id = repository.insert_session(
        task="Refactor auth login",
        files_modified='["src/auth/login.py"]',
        decisions='["Keep token refresh in auth"]',
        assumptions="",
        problems="[]",
        record_id="session-auth",
    )

    results = repository.search_sessions("auth token refresh", top_k=1)

    assert record_id == "session-auth"
    assert results[0]["id"] == "session-auth"
    assert results[0]["task"] == "Refactor auth login"


def test_repository_inserts_and_searches_git_history(repository: Repository) -> None:
    record_id = repository.insert_git_entry(
        file_path="src/auth/tokens.py",
        commit_hash="abc123",
        commit_msg="Tighten refresh validation",
        author="Dev",
        date="2026-06-02",
        code_snippet="def refresh_token(): ...",
        record_id="git-auth",
    )

    results = repository.search_history(
        "refresh validation",
        file_filter="src/auth/tokens.py",
        top_k=1,
    )

    assert record_id == "git-auth"
    assert results[0]["id"] == "git-auth"
    assert results[0]["file_path"] == "src/auth/tokens.py"
    assert results[0]["commit_hash"] == "abc123"
