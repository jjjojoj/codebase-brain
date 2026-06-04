from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from codebrain.domains.history import git_indexer
from codebrain.domains.history.git_indexer import _parse_blame_porcelain, get_co_changed


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
        lambda repo, args: git_indexer.GitCommandResult(False, "", "locked", 1),
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
