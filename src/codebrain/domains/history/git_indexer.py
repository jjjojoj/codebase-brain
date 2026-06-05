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
    timeout_sec: float | None = None,
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
        timeout_sec=timeout_sec,
    )
    if not result.ok:
        detail = result.stderr.strip() or f"git blame exited with code {result.returncode}"
        raise RuntimeError(detail)
    return _parse_blame_porcelain(result.stdout)


def get_co_changed(
    repo_path: str | Path,
    file_path: str,
    limit: int = 10,
    max_commits: int = 50,
) -> list[dict[str, Any]]:
    """Return files commonly changed with file_path using one git process."""
    repo = _resolve_repo(repo_path)
    if limit < 1 or not _is_git_repo(repo) or not _has_commits(repo):
        return []

    log_result = _run_git(
        repo,
        [
            "log",
            f"-n{max_commits}",
            f"--format={GIT_RECORD_SEPARATOR}%ad",
            "--date=iso-strict",
            "--name-only",
            "--full-diff",
            "--",
            file_path,
        ],
    )
    if not log_result.ok or not log_result.stdout.strip():
        return []

    counts: Counter[str] = Counter()
    last_changed: dict[str, str] = {}
    for raw_record in log_result.stdout.split(GIT_RECORD_SEPARATOR):
        record = raw_record.strip()
        if not record:
            continue
        date, _, files_blob = record.partition("\n")
        changed_files = [
            line.strip()
            for line in files_blob.splitlines()
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


def get_co_changed_for_files(
    repo_path: str | Path,
    file_paths: list[str],
    limit: int = 10,
    max_commits: int = 50,
    timeout_sec: float | None = None,
) -> list[dict[str, Any]]:
    """Return co-change signals for multiple source files using one git process."""
    repo = _resolve_repo(repo_path)
    requested = _dedupe_paths(file_paths)
    if limit < 1 or not requested or not _is_git_repo(repo) or not _has_commits(repo):
        return []

    log_result = _run_git(
        repo,
        [
            "log",
            f"-n{max_commits}",
            f"--format={GIT_RECORD_SEPARATOR}%ad",
            "--date=iso-strict",
            "--name-only",
            "--full-diff",
            "--",
            *requested,
        ],
        timeout_sec=timeout_sec,
    )
    if not log_result.ok or not log_result.stdout.strip():
        return []

    requested_set = set(requested)
    counts: dict[str, Counter[str]] = {file_path: Counter() for file_path in requested}
    last_changed: dict[tuple[str, str], str] = {}
    for raw_record in log_result.stdout.split(GIT_RECORD_SEPARATOR):
        record = raw_record.strip()
        if not record:
            continue
        date, _, files_blob = record.partition("\n")
        changed_files = [
            line.strip()
            for line in files_blob.splitlines()
            if line.strip()
        ]
        changed_requested = [file_path for file_path in requested if file_path in changed_files]
        if not changed_requested:
            continue
        for source_file in changed_requested:
            for changed_file in changed_files:
                if changed_file in requested_set:
                    continue
                counts[source_file][changed_file] += 1
                last_changed.setdefault((source_file, changed_file), date)

    rows: list[dict[str, Any]] = []
    for source_file in requested:
        for changed_file, count in counts[source_file].most_common(limit):
            rows.append({
                "source_file": source_file,
                "file": changed_file,
                "co_change_count": count,
                "last_changed_together": last_changed.get((source_file, changed_file), ""),
            })
            if len(rows) >= limit:
                return rows
    return rows



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


def get_recent_changes_for_files(
    repo_path: str | Path,
    file_paths: list[str],
    limit: int = 10,
    timeout_sec: float | None = None,
) -> list[dict[str, str]]:
    """Return recent commits for multiple files using one git process."""
    repo = _resolve_repo(repo_path)
    requested = _dedupe_paths(file_paths)
    if limit < 1 or not requested or not _is_git_repo(repo) or not _has_commits(repo):
        return []

    max_commits = max(limit, limit * len(requested))
    result = _run_git(
        repo,
        [
            "log",
            f"--max-count={max_commits}",
            "--date=iso-strict",
            f"--pretty=format:{GIT_RECORD_SEPARATOR}%H{GIT_FIELD_SEPARATOR}%an"
            f"{GIT_FIELD_SEPARATOR}%ad{GIT_FIELD_SEPARATOR}%s",
            "--name-only",
            "--",
            *requested,
        ],
        timeout_sec=timeout_sec,
    )
    if not result.ok or not result.stdout.strip():
        return []

    requested_set = set(requested)
    changes: list[dict[str, str]] = []
    for raw_record in result.stdout.split(GIT_RECORD_SEPARATOR):
        record = raw_record.strip()
        if not record:
            continue
        header, _, files_blob = record.partition("\n")
        fields = header.split(GIT_FIELD_SEPARATOR, 3)
        if len(fields) != 4:
            continue
        commit_hash, author, date, message = fields
        changed = {
            line.strip()
            for line in files_blob.splitlines()
            if line.strip() in requested_set
        }
        for file_path in requested:
            if file_path not in changed:
                continue
            changes.append({
                "file_path": file_path,
                "commit_hash": commit_hash,
                "commit_msg": message,
                "author": author,
                "date": date,
            })
            if len(changes) >= limit:
                return changes
    return changes


def get_history_context_for_files(
    repo_path: str | Path,
    file_paths: list[str],
    limit: int = 10,
    max_commits: int = 50,
    timeout_sec: float | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Return recent, co-change, and attribution signals from one git log."""
    repo = _resolve_repo(repo_path)
    requested = _dedupe_paths(file_paths)
    empty: dict[str, list[dict[str, Any]]] = {
        "recent_changes": [],
        "co_changed_files": [],
        "blame": [],
    }
    if limit < 1 or not requested or max_commits < 1 or not _is_git_repo(repo) or not _has_commits(repo):
        return empty

    result = _run_git(
        repo,
        [
            "log",
            f"--max-count={max_commits}",
            "--date=iso-strict",
            f"--pretty=format:{GIT_RECORD_SEPARATOR}%H{GIT_FIELD_SEPARATOR}%an"
            f"{GIT_FIELD_SEPARATOR}%ad{GIT_FIELD_SEPARATOR}%s",
            "--name-only",
            "--full-diff",
            "--",
            *requested,
        ],
        timeout_sec=timeout_sec,
    )
    if not result.ok or not result.stdout.strip():
        return empty

    requested_set = set(requested)
    recent_changes: list[dict[str, Any]] = []
    attribution: list[dict[str, Any]] = []
    attributed: set[str] = set()
    co_counts: dict[str, Counter[str]] = {file_path: Counter() for file_path in requested}
    co_last_changed: dict[tuple[str, str], str] = {}

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
        changed_requested = [file_path for file_path in requested if file_path in changed_files]
        if not changed_requested:
            continue

        for file_path in changed_requested:
            if len(recent_changes) < limit:
                recent_changes.append({
                    "file_path": file_path,
                    "commit_hash": commit_hash,
                    "commit_msg": message,
                    "author": author,
                    "date": date,
                })
            if file_path not in attributed:
                attribution.append({
                    "file_path": file_path,
                    "line": 1,
                    "author": author,
                    "date": date,
                    "commit_hash": commit_hash,
                    "commit_msg": message,
                    "source": "git_log_last_change",
                })
                attributed.add(file_path)

            for changed_file in changed_files:
                if changed_file in requested_set:
                    continue
                co_counts[file_path][changed_file] += 1
                co_last_changed.setdefault((file_path, changed_file), date)

    co_changed: list[dict[str, Any]] = []
    for source_file in requested:
        for changed_file, count in co_counts[source_file].most_common(limit):
            co_changed.append({
                "source_file": source_file,
                "file": changed_file,
                "co_change_count": count,
                "last_changed_together": co_last_changed.get((source_file, changed_file), ""),
            })
            if len(co_changed) >= limit:
                break
        if len(co_changed) >= limit:
            break

    return {
        "recent_changes": recent_changes[:limit],
        "co_changed_files": co_changed[:limit],
        "blame": attribution[:limit],
    }


def get_last_change_for_files(
    repo_path: str | Path,
    file_paths: list[str],
    max_commits: int = 50,
    timeout_sec: float | None = None,
) -> list[dict[str, Any]]:
    """Return the newest commit touching each file using one git log process."""
    repo = _resolve_repo(repo_path)
    requested = _dedupe_paths(file_paths)
    if not requested or max_commits < 1 or not _is_git_repo(repo) or not _has_commits(repo):
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
            "--",
            *requested,
        ],
        timeout_sec=timeout_sec,
    )
    if not result.ok or not result.stdout.strip():
        return []

    remaining = set(requested)
    rows: list[dict[str, Any]] = []
    for raw_record in result.stdout.split(GIT_RECORD_SEPARATOR):
        record = raw_record.strip()
        if not record:
            continue
        header, _, files_blob = record.partition("\n")
        fields = header.split(GIT_FIELD_SEPARATOR, 3)
        if len(fields) != 4:
            continue
        commit_hash, author, date, message = fields
        changed = {
            line.strip()
            for line in files_blob.splitlines()
            if line.strip() in remaining
        }
        for file_path in requested:
            if file_path not in changed:
                continue
            rows.append({
                "file_path": file_path,
                "line": 1,
                "author": author,
                "date": date,
                "commit_hash": commit_hash,
                "commit_msg": message,
                "source": "git_log_last_change",
            })
            remaining.discard(file_path)
        if not remaining:
            break
    return rows


def _parse_blame_porcelain(output: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    current_line = 0
    for raw_line in output.splitlines():
        if not raw_line:
            continue
        if raw_line.startswith("\t"):
            if not current.get("commit_hash") or current_line < 1:
                raise ValueError("Malformed git blame porcelain: source line without header")
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
            try:
                current_line = int(parts[2])
            except ValueError as exc:
                raise ValueError(
                    "Malformed git blame porcelain: invalid source line number"
                ) from exc
            current = {"commit_hash": parts[0]}
            continue

        key, _, value = raw_line.partition(" ")
        if key in {"author", "author-time", "summary"}:
            current[key] = value
    if output.strip() and not rows:
        raise ValueError("Malformed git blame porcelain: no source records")
    return rows


def _run_git(
    repo: Path,
    args: list[str],
    timeout_sec: float | None = None,
) -> GitCommandResult:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        return GitCommandResult(False, exc.stdout or "", str(exc), 124)
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


def _dedupe_paths(file_paths: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for file_path in file_paths:
        normalized = file_path.strip().replace("\\", "/")
        if normalized and normalized not in seen:
            deduped.append(normalized)
            seen.add(normalized)
    return deduped


def _format_unix_timestamp(value: Any) -> str:
    try:
        timestamp = int(str(value))
    except (TypeError, ValueError):
        return ""
    return datetime.fromtimestamp(timestamp, UTC).isoformat()
