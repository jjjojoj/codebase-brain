"""Git history indexing helpers (pure subprocess, no MCP)."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import subprocess
from typing import Any

GIT_RECORD_SEPARATOR = "\x1e"
GIT_FIELD_SEPARATOR = "\x1f"


@dataclass(frozen=True)
class GitCommandResult:
    ok: bool
    stdout: str
    stderr: str
    returncode: int


def parse_git_log(repo_path: str | Path, max_commits: int = 500) -> list[dict[str, Any]]:
    repo = _resolve_repo(repo_path)
    if max_commits < 1 or not _is_git_repo(repo) or not _has_commits(repo):
        return []

    result = _run_git(
        repo,
        [
            "log",
            f"--max-count={max_commits}",
            "--date=iso-strict",
            f"--pretty=format:{GIT_RECORD_SEPARATOR}%H{GIT_FIELD_SEPARATOR}%an"
            f"{GIT_FIELD_SEPARATOR}%ad{GIT_FIELD_SEPARATOR}%s",
            "--name-only",
        ],
    )
    if not result.ok or not result.stdout.strip():
        return []

    commits: list[dict[str, Any]] = []
    for raw_record in result.stdout.split(GIT_RECORD_SEPARATOR):
        record = raw_record.strip()
        if not record:
            continue
        header, _, files_blob = record.partition("\n")
        fields = header.split(GIT_FIELD_SEPARATOR, 3)
        if len(fields) != 4:
            continue
        commit_hash, author, date, message = fields
        changed_files = [
            line.strip()
            for line in files_blob.splitlines()
            if line.strip()
        ]
        commits.append({
            "commit_hash": commit_hash,
            "author": author,
            "date": date,
            "commit_msg": message,
            "changed_files": changed_files,
        })
    return commits


def get_file_snippet_at_commit(
    repo_path: str | Path,
    commit_hash: str,
    file_path: str,
    max_chars: int = 4000,
) -> str:
    repo = _resolve_repo(repo_path)
    if not _is_git_repo(repo) or not commit_hash or not file_path:
        return ""
    result = _run_git(repo, ["show", f"{commit_hash}:{file_path}"])
    if not result.ok:
        return ""
    text = result.stdout.replace("\x00", "")
    return text[:max_chars]


def get_blame_info(
    repo_path: str | Path,
    file_path: str,
    start: int,
    end: int,
) -> list[dict[str, Any]]:
    repo = _resolve_repo(repo_path)
    if start < 1 or end < start or not _is_git_repo(repo) or not _has_commits(repo):
        return []
    if not (repo / file_path).exists():
        return []

    result = _run_git(
        repo,
        [
            "blame",
            "--line-porcelain",
            "-L",
            f"{start},{end}",
            "--",
            file_path,
        ],
    )
    if not result.ok:
        return []
    return _parse_blame_porcelain(result.stdout)


def get_co_changed(
    repo_path: str | Path,
    file_path: str,
    limit: int = 10,
    max_commits: int = 50,
) -> list[dict[str, Any]]:
    """Return files commonly changed with file_path.

    Two-phase approach: git log for hashes+dates, then git diff-tree
    (lighter than git show) per commit for co-changed files.
    """
    repo = _resolve_repo(repo_path)
    if limit < 1 or not _is_git_repo(repo) or not _has_commits(repo):
        return []

    # Phase 1: get hashes and dates in one pass
    log_result = _run_git(
        repo,
        [
            "log",
            f"-n{max_commits}",
            f"--format=%H{GIT_FIELD_SEPARATOR}%ad",
            "--date=iso-strict",
            "--",
            file_path,
        ],
    )
    if not log_result.ok or not log_result.stdout.strip():
        return []

    commits: list[tuple[str, str]] = []
    for line in log_result.stdout.splitlines():
        parts = line.split(GIT_FIELD_SEPARATOR, 1)
        if len(parts) == 2:
            commits.append((parts[0], parts[1]))

    # Phase 2: for each commit, use diff-tree (no diff, just file names)
    counts: Counter[str] = Counter()
    last_changed: dict[str, str] = {}
    for commit_hash, date in commits:
        files_result = _run_git(
            repo,
            ["diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash],
        )
        if not files_result.ok:
            continue
        changed_files = [
            line.strip()
            for line in files_result.stdout.splitlines()
            if line.strip()
        ]
        if file_path not in changed_files:
            continue
        for changed_file in changed_files:
            if changed_file == file_path:
                continue
            counts[changed_file] += 1
            last_changed.setdefault(changed_file, date)

    return [
        {
            "file": changed_file,
            "co_change_count": count,
            "last_changed_together": last_changed.get(changed_file, ""),
        }
        for changed_file, count in counts.most_common(limit)
    ]



def get_recent_changes(
    repo_path: str | Path,
    file_path: str,
    limit: int = 10,
) -> list[dict[str, str]]:
    repo = _resolve_repo(repo_path)
    if limit < 1 or not _is_git_repo(repo) or not _has_commits(repo):
        return []

    result = _run_git(
        repo,
        [
            "log",
            f"--max-count={limit}",
            "--date=iso-strict",
            f"--pretty=format:%H{GIT_FIELD_SEPARATOR}%an{GIT_FIELD_SEPARATOR}%ad"
            f"{GIT_FIELD_SEPARATOR}%s",
            "--",
            file_path,
        ],
    )
    if not result.ok or not result.stdout.strip():
        return []

    changes: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        fields = line.split(GIT_FIELD_SEPARATOR, 3)
        if len(fields) != 4:
            continue
        commit_hash, author, date, message = fields
        changes.append({
            "commit_hash": commit_hash,
            "commit_msg": message,
            "author": author,
            "date": date,
        })
    return changes


def _parse_blame_porcelain(output: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    current_line = 0
    for raw_line in output.splitlines():
        if not raw_line:
            continue
        if raw_line.startswith("\t"):
            rows.append({
                "line": current_line,
                "author": current.get("author", ""),
                "date": _format_unix_timestamp(current.get("author-time")),
                "commit_hash": current.get("commit_hash", ""),
                "commit_msg": current.get("summary", ""),
            })
            current_line += 1
            continue

        parts = raw_line.split()
        if len(parts) >= 4 and _looks_like_commit(parts[0]):
            current = {"commit_hash": parts[0]}
            current_line = int(parts[2])
            continue

        key, _, value = raw_line.partition(" ")
        if key in {"author", "author-time", "summary"}:
            current[key] = value
    return rows


def _run_git(repo: Path, args: list[str]) -> GitCommandResult:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        return GitCommandResult(False, "", str(exc), 127)
    return GitCommandResult(
        completed.returncode == 0,
        completed.stdout,
        completed.stderr,
        completed.returncode,
    )


def _resolve_repo(repo_path: str | Path) -> Path:
    return Path(repo_path).expanduser().resolve()


def _is_git_repo(repo: Path) -> bool:
    if not repo.exists():
        return False
    result = _run_git(repo, ["rev-parse", "--is-inside-work-tree"])
    return result.ok and result.stdout.strip() == "true"


def _has_commits(repo: Path) -> bool:
    result = _run_git(repo, ["rev-parse", "--verify", "HEAD"])
    return result.ok


def _looks_like_commit(value: str) -> bool:
    return len(value) >= 8 and all(char in "0123456789abcdef^" for char in value.lower())


def _format_unix_timestamp(value: Any) -> str:
    try:
        timestamp = int(str(value))
    except (TypeError, ValueError):
        return ""
    return datetime.fromtimestamp(timestamp, UTC).isoformat()
