from __future__ import annotations

import subprocess
from pathlib import Path

from codebrain.domains.history.git_indexer import get_co_changed


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


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
