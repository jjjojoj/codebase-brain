"""Project file filtering and sync-state helpers for brain indexing."""

from __future__ import annotations

from datetime import UTC, datetime
import fnmatch
import hashlib
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_EXCLUDE_PATTERNS = [
    ".git/**",
    ".codebrain/*.db",
    ".codebrain/**/*.db",
    ".codebrain/index-state.json",
    ".venv/**",
    "venv/**",
    "node_modules/**",
    "dist/**",
    "build/**",
    "target/**",
    ".pytest_cache/**",
    ".mypy_cache/**",
    ".ruff_cache/**",
    "__pycache__/**",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
]


def sync_status(
    repo_path: str,
    *,
    include_patterns: str | list[str] | None = None,
    exclude_patterns: str | list[str] | None = None,
    max_file_size_mb: int = 5,
) -> dict[str, Any]:
    """Return current snapshot plus whether the project should be re-indexed."""
    snapshot = snapshot_project(
        repo_path,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        max_file_size_mb=max_file_size_mb,
    )
    state = load_index_state(repo_path)
    last_snapshot = state.get("snapshot") if isinstance(state, dict) else None
    last_fingerprint = (
        last_snapshot.get("fingerprint") if isinstance(last_snapshot, dict) else ""
    )
    needs_sync = snapshot["fingerprint"] != last_fingerprint
    return {
        "ok": True,
        "repo_path": snapshot["repo_path"],
        "needs_sync": needs_sync,
        "reason": "changed" if last_fingerprint and needs_sync else (
            "never_indexed" if needs_sync else "fresh"
        ),
        "snapshot": snapshot,
        "last_index": state or None,
    }


def snapshot_project(
    repo_path: str,
    *,
    include_patterns: str | list[str] | None = None,
    exclude_patterns: str | list[str] | None = None,
    max_file_size_mb: int = 5,
) -> dict[str, Any]:
    """Build a cheap file snapshot without reading file contents."""
    root = Path(repo_path).expanduser().resolve()
    includes = _normalize_patterns(include_patterns)
    excludes = [*DEFAULT_EXCLUDE_PATTERNS, *_normalize_patterns(exclude_patterns)]
    max_bytes = max_file_size_mb * 1024 * 1024

    digest = hashlib.sha256()
    file_count = 0
    total_bytes = 0
    samples: list[str] = []
    skipped = {"excluded": 0, "too_large": 0, "errors": 0}

    for dirpath, dirnames, filenames in os.walk(root):
        kept_dirs: list[str] = []
        for dirname in dirnames:
            if _is_excluded(_relative_path(root, Path(dirpath) / dirname) + "/", excludes):
                skipped["excluded"] += 1
                continue
            kept_dirs.append(dirname)
        dirnames[:] = kept_dirs
        for filename in filenames:
            path = Path(dirpath) / filename
            rel_path = _relative_path(root, path)
            if _is_excluded(rel_path, excludes):
                skipped["excluded"] += 1
                continue
            if includes and not _matches_any(rel_path, includes):
                skipped["excluded"] += 1
                continue
            try:
                stat = path.stat()
            except OSError:
                skipped["errors"] += 1
                continue
            if stat.st_size > max_bytes:
                skipped["too_large"] += 1
                continue

            file_count += 1
            total_bytes += stat.st_size
            if len(samples) < 20:
                samples.append(rel_path)
            digest.update(rel_path.encode("utf-8"))
            digest.update(str(stat.st_size).encode("ascii"))
            digest.update(str(stat.st_mtime_ns).encode("ascii"))

    return {
        "ok": True,
        "repo_path": str(root),
        "fingerprint": digest.hexdigest(),
        "generated_at": _now(),
        "file_count": file_count,
        "total_bytes": total_bytes,
        "max_file_size_mb": max_file_size_mb,
        "include_patterns": includes,
        "exclude_patterns": excludes,
        "skipped": skipped,
        "sample_files": samples,
    }


def load_index_state(repo_path: str) -> dict[str, Any]:
    """Load persisted index state for one project."""
    path = index_state_path(repo_path)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"ok": False, "path": str(path), "error": "invalid index state"}
    return data if isinstance(data, dict) else {}


def record_index_state(
    repo_path: str,
    snapshot: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    """Persist the last successful sync snapshot and result summary."""
    path = index_state_path(repo_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "ok": True,
        "version": 1,
        "updated_at": _now(),
        "snapshot": snapshot,
        "result": _compact_result(result),
    }
    temp_path = path.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)
    return {"ok": True, "path": str(path), "updated_at": state["updated_at"]}


def index_state_path(repo_path: str) -> Path:
    return Path(repo_path).expanduser().resolve() / ".codebrain" / "index-state.json"


def _compact_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": result.get("ok"),
        "status": result.get("status"),
        "graph_status": (result.get("graph") or {}).get("status"),
        "conventions_indexed": (result.get("conventions") or {}).get("indexed"),
        "notes": result.get("notes") or [],
    }


def _normalize_patterns(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return [item.strip() for item in value if item.strip()]
    raise TypeError("patterns must be a comma-separated string, list of strings, or None")


def _relative_path(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def _is_excluded(rel_path: str, patterns: list[str]) -> bool:
    return _matches_any(rel_path, patterns)


def _matches_any(rel_path: str, patterns: list[str]) -> bool:
    name = rel_path.rstrip("/").rsplit("/", 1)[-1]
    return any(
        fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(name, pattern)
        for pattern in patterns
    )


def _now() -> str:
    return datetime.now(UTC).isoformat()
