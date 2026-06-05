from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from codebrain.domains.history import git_indexer
from codebrain.domains.history.git_indexer import (
    _parse_blame_porcelain,
    get_co_changed,
    get_co_changed_for_files,
    get_history_context_for_files,
    get_last_change_for_files,
    get_recent_changes_for_files,
)


def test_get_co_changed_returns_other_files_from_matching_commits(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")

    (tmp_path / "target.py").write_text("one\n", encoding="utf-8")
    (tmp_path / "related.py").write_text("one\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "first")

    (tmp_path / "target.py").write_text("two\n", encoding="utf-8")
    (tmp_path / "related.py").write_text("two\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "second")

    result = get_co_changed(tmp_path, "target.py", limit=5, max_commits=10)

    assert result[0]["file"] == "related.py"
    assert result[0]["co_change_count"] == 2


def test_get_recent_changes_for_files_uses_one_git_log_for_multiple_paths(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")

    (tmp_path / "a.py").write_text("one\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "add a")

    (tmp_path / "b.py").write_text("one\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "add b")

    (tmp_path / "a.py").write_text("two\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("two\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "touch both")

    result = get_recent_changes_for_files(tmp_path, ["a.py", "b.py"], limit=4)

    assert [(row["file_path"], row["commit_msg"]) for row in result] == [
        ("a.py", "touch both"),
        ("b.py", "touch both"),
        ("b.py", "add b"),
        ("a.py", "add a"),
    ]


def test_get_co_changed_for_files_returns_sources_from_one_log(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")

    (tmp_path / "a.py").write_text("one\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("one\n", encoding="utf-8")
    (tmp_path / "shared.py").write_text("one\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial shared")

    (tmp_path / "a.py").write_text("two\n", encoding="utf-8")
    (tmp_path / "shared.py").write_text("two\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "touch a shared")

    result = get_co_changed_for_files(tmp_path, ["a.py", "b.py"], limit=3, max_commits=10)

    assert result[0]["source_file"] == "a.py"
    assert result[0]["file"] == "shared.py"
    assert result[0]["co_change_count"] == 2
    assert any(row["source_file"] == "b.py" and row["file"] == "shared.py" for row in result)


def test_get_last_change_for_files_returns_newest_touch_per_file(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")

    (tmp_path / "a.py").write_text("one\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("one\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")

    (tmp_path / "b.py").write_text("two\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "touch b")

    result = get_last_change_for_files(tmp_path, ["a.py", "b.py"], max_commits=10)

    assert [(row["file_path"], row["commit_msg"]) for row in result] == [
        ("b.py", "touch b"),
        ("a.py", "initial"),
    ]
    assert all(row["source"] == "git_log_last_change" for row in result)


def test_get_history_context_for_files_combines_signals_from_one_log(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")

    (tmp_path / "a.py").write_text("one\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("one\n", encoding="utf-8")
    (tmp_path / "shared.py").write_text("one\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")

    (tmp_path / "a.py").write_text("two\n", encoding="utf-8")
    (tmp_path / "shared.py").write_text("two\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "touch a shared")

    result = get_history_context_for_files(tmp_path, ["a.py", "b.py"], limit=5, max_commits=10)

    assert result["recent_changes"][0]["file_path"] == "a.py"
    assert result["recent_changes"][0]["commit_msg"] == "touch a shared"
    assert any(row["file"] == "shared.py" for row in result["co_changed_files"])
    assert [(row["file_path"], row["source"]) for row in result["blame"]] == [
        ("a.py", "git_log_last_change"),
        ("b.py", "git_log_last_change"),
    ]


def test_parse_blame_porcelain_rejects_source_without_header() -> None:
    with pytest.raises(ValueError, match="source line without header"):
        _parse_blame_porcelain("\tprint('missing header')\n")


def test_parse_blame_porcelain_rejects_output_without_source_records() -> None:
    with pytest.raises(ValueError, match="no source records"):
        _parse_blame_porcelain("author Test User\n")


def test_get_blame_info_surfaces_git_failure(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "target.py").write_text("one\n", encoding="utf-8")
    monkeypatch.setattr(git_indexer, "_is_git_repo", lambda repo: True)
    monkeypatch.setattr(git_indexer, "_has_commits", lambda repo: True)
    monkeypatch.setattr(
        git_indexer,
        "_run_git",
        lambda repo, args, timeout_sec=None: git_indexer.GitCommandResult(
            False,
            "",
            "locked",
            1,
        ),
    )

    with pytest.raises(RuntimeError, match="locked"):
        git_indexer.get_blame_info(tmp_path, "target.py", 1, 1)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
