"""Sidecar adapter for DeusData/codebase-memory-mcp.

The adapter keeps Codebase Brain as one MCP server while allowing a richer
code graph engine to be installed beside it. Missing sidecars degrade into
structured status dictionaries instead of failing server startup.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any, Callable


Runner = Callable[[list[str], int], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class SidecarResult:
    """Normalized result from one codebase-memory-mcp CLI call."""

    ok: bool
    status: str
    tool: str
    command: list[str]
    data: Any = None
    text: str = ""
    error: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable result for MCP tool responses."""
        result: dict[str, Any] = {
            "ok": self.ok,
            "status": self.status,
            "tool": self.tool,
            "command": self.command,
        }
        if self.data is not None:
            result["data"] = self.data
        if self.text:
            result["text"] = self.text
        if self.error:
            result["error"] = self.error
        return result


class CodebaseMemoryAdapter:
    """Thin CLI adapter around codebase-memory-mcp's graph tools."""

    def __init__(
        self,
        binary: str = "codebase-memory-mcp",
        timeout_sec: int = 120,
        search_timeout_sec: int = 15,
        repo_aliases: str | dict[str, str] | None = None,
        runner: Runner | None = None,
    ) -> None:
        self.binary = binary
        self.timeout_sec = timeout_sec
        self.search_timeout_sec = min(search_timeout_sec, timeout_sec)
        self.repo_aliases = _parse_repo_aliases(repo_aliases)
        self._runner = runner or _run_subprocess

    def status(self) -> dict[str, Any]:
        """Report whether the sidecar binary is currently callable."""
        resolved = _resolve_binary(self.binary)
        return {
            "available": bool(resolved),
            "status": "ready" if resolved else "missing",
            "binary": self.binary,
            "resolved_binary": resolved,
            "timeout_sec": self.timeout_sec,
            "search_timeout_sec": self.search_timeout_sec,
            "repo_aliases": self.repo_aliases,
            "tools": [
                "index_repository",
                "search_graph",
                "trace_path",
                "get_code_snippet",
            ],
        }

    def index_repository(
        self,
        repo_path: str,
        mode: str = "full",
        persistence: bool = False,
    ) -> dict[str, Any]:
        """Index a repository through the sidecar graph engine."""
        graph_repo_path = self._graph_repo_path(repo_path)
        args: dict[str, Any] = {
            "repo_path": _resolve_path(graph_repo_path),
            "mode": mode,
            "persistence": persistence,
        }
        return self.call("index_repository", args).as_dict()

    def search_graph(
        self,
        symbol: str,
        repo_path: str,
        limit: int = 5,
    ) -> dict[str, Any]:
        """Search graph symbols matching a name pattern."""
        args = {
            "name_pattern": symbol,
            "limit": limit,
        }
        return self._call_with_project_aliases("search_graph", args, repo_path).as_dict()

    def trace_call_path(
        self,
        symbol: str,
        repo_path: str,
        depth: int = 2,
    ) -> dict[str, Any]:
        """Trace callers and callees for a symbol."""
        args = {
            "function_name": symbol,
            "mode": "calls",
            "direction": "both",
            "depth": depth,
        }
        return self._call_with_project_aliases("trace_path", args, repo_path).as_dict()

    def _call_with_project_aliases(
        self,
        tool: str,
        args: dict[str, Any],
        repo_path: str,
    ) -> SidecarResult:
        aliases = self._project_aliases(repo_path)
        first_result: SidecarResult | None = None
        first_ok_result: SidecarResult | None = None
        first_ok_project = ""
        last_result: SidecarResult | None = None
        for project in aliases:
            result = self.call(
                tool,
                {"project": project, **args},
                timeout_sec=self.search_timeout_sec,
            )
            if first_result is None:
                first_result = result
            last_result = result
            if result.ok is True and first_ok_result is None:
                first_ok_result = result
                first_ok_project = project
            if _sidecar_result_has_payload(result):
                return _with_alias_metadata(result, aliases, project)
        if first_result is None:
            return self.call(tool, args, timeout_sec=self.search_timeout_sec)
        if first_ok_result is not None:
            return _with_alias_metadata(first_ok_result, aliases, first_ok_project)
        return _with_alias_metadata(last_result or first_result, aliases, aliases[-1])

    def _graph_repo_path(self, repo_path: str) -> str:
        key = _normalize_alias_key(repo_path)
        return self.repo_aliases.get(key, repo_path)

    def _project_aliases(self, repo_path: str) -> list[str]:
        paths = [repo_path]
        graph_repo_path = self._graph_repo_path(repo_path)
        if graph_repo_path != repo_path:
            paths.append(graph_repo_path)
        aliases: list[str] = []
        for path in paths:
            aliases.extend(project_name_aliases_from_path(path))
        return _dedupe_text(aliases)

    def call(
        self,
        tool: str,
        args: dict[str, Any],
        *,
        timeout_sec: int | None = None,
    ) -> SidecarResult:
        """Call one codebase-memory-mcp CLI tool and normalize output."""
        resolved_binary = _resolve_binary(self.binary)
        command = [
            resolved_binary or self.binary,
            "cli",
            tool,
            # Keep Windows command-line arguments ASCII-only. The sidecar's
            # JSON parser restores Unicode paths from \uXXXX escapes.
            json.dumps(args, ensure_ascii=True),
        ]
        if not resolved_binary:
            return SidecarResult(
                ok=False,
                status="missing",
                tool=tool,
                command=command,
                error=(
                    "codebase-memory-mcp binary not found. Install it and set "
                    "CODEBRAIN_CODEBASE_MEMORY_BINARY if it is outside PATH."
                ),
            )

        effective_timeout = timeout_sec or self.timeout_sec
        try:
            completed = self._runner(command, effective_timeout)
        except subprocess.TimeoutExpired as exc:
            return SidecarResult(
                ok=False,
                status="timeout",
                tool=tool,
                command=command,
                error=f"sidecar call timed out after {effective_timeout}s: {exc}",
            )
        except OSError as exc:
            return SidecarResult(
                ok=False,
                status="error",
                tool=tool,
                command=command,
                error=str(exc),
            )

        stdout = completed.stdout.strip() if completed.stdout else ""
        stderr = completed.stderr.strip() if completed.stderr else ""
        data = _parse_sidecar_output(stdout)
        if completed.returncode != 0:
            return SidecarResult(
                ok=False,
                status="error",
                tool=tool,
                command=command,
                data=data if not isinstance(data, str) else None,
                text=data if isinstance(data, str) else "",
                error=stderr or f"sidecar exited with code {completed.returncode}",
            )

        return SidecarResult(
            ok=True,
            status="ok",
            tool=tool,
            command=command,
            data=data if not isinstance(data, str) else None,
            text=data if isinstance(data, str) else "",
        )


def _run_subprocess(
    command: list[str],
    timeout_sec: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_sec,
    )


def _resolve_binary(binary: str) -> str:
    if not binary:
        return ""
    found = shutil.which(binary)
    if found:
        return found
    path = Path(binary).expanduser()
    if path.exists() and path.is_file():
        return str(path.resolve())
    return ""


def _resolve_path(path: str) -> str:
    return str(Path(path).expanduser().resolve())


def project_name_from_path(path: str) -> str:
    """Match codebase-memory-mcp's project name derived from repo path."""
    return _project_name_from_path(path, unicode_safe=True, preserve_spaces=True)


def project_name_aliases_from_path(path: str) -> list[str]:
    """Return current and legacy sidecar project names for one repo path."""
    return _dedupe_text([
        _project_name_from_path(path, unicode_safe=True, preserve_spaces=True),
        _project_name_from_path(path, unicode_safe=True, preserve_spaces=False),
        _project_name_from_path(path, unicode_safe=False, preserve_spaces=False),
    ])


def legacy_project_name_from_path(path: str) -> str:
    """Return the pre-Unicode project name for existing sidecar databases."""
    return _project_name_from_path(path, unicode_safe=False, preserve_spaces=False)


def repo_alias_source_paths(value: str | dict[str, str] | None) -> list[str]:
    """Return configured source paths from a repo alias mapping."""
    if not value:
        return []
    if isinstance(value, dict):
        return [
            str(source)
            for source, target in value.items()
            if str(source).strip() and str(target).strip()
        ]
    sources: list[str] = []
    for item in value.split(";"):
        source, separator, target = item.partition("=>")
        if not separator:
            source, separator, target = item.partition("=")
        if separator and source.strip() and target.strip():
            sources.append(source.strip())
    return sources


def _parse_repo_aliases(value: str | dict[str, str] | None) -> dict[str, str]:
    if not value:
        return {}
    if isinstance(value, dict):
        return {
            _normalize_alias_key(source): target
            for source, target in value.items()
            if str(source).strip() and str(target).strip()
        }
    aliases: dict[str, str] = {}
    for item in value.split(";"):
        source, separator, target = item.partition("=>")
        if not separator:
            source, separator, target = item.partition("=")
        if not separator:
            continue
        source = source.strip()
        target = target.strip()
        if source and target:
            aliases[_normalize_alias_key(source)] = target
    return aliases


def _normalize_alias_key(path: str) -> str:
    return str(path).strip().replace("\\", "/").rstrip("/").lower()


def _project_name_from_path(
    path: str,
    *,
    unicode_safe: bool,
    preserve_spaces: bool,
) -> str:
    resolved = _resolve_path(path)
    chars: list[str] = []
    previous = ""
    for char in resolved:
        safe = (char.isalnum() if unicode_safe else char.isascii() and char.isalnum())
        safe = safe or char in "._-" or (preserve_spaces and char == " ")
        normalized = char if safe else "-"
        if (normalized == "-" and previous == "-") or (
            normalized == "." and previous == "."
        ):
            continue
        chars.append(normalized)
        previous = normalized

    candidate = "".join(chars).lstrip("-.").rstrip("-")
    return candidate or "root"


def _sidecar_result_has_payload(result: SidecarResult) -> bool:
    if result.ok is not True:
        return False
    if result.text.strip():
        return True
    return _has_payload(result.data)


def _has_payload(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, list):
        return bool(value)
    if isinstance(value, dict):
        for empty_key in ("results", "paths", "callers", "callees", "nodes", "edges"):
            if empty_key in value:
                return _has_payload(value.get(empty_key))
        total = value.get("total")
        if isinstance(total, int):
            return total > 0
        return any(_has_payload(item) for item in value.values())
    return bool(value)


def _with_alias_metadata(
    result: SidecarResult,
    aliases: list[str],
    project: str,
) -> SidecarResult:
    if len(aliases) < 2:
        return result
    data = result.data
    if isinstance(data, dict):
        data = {
            **data,
            "project_alias_used": project,
            "project_aliases_tried": aliases,
        }
    return SidecarResult(
        ok=result.ok,
        status=result.status,
        tool=result.tool,
        command=result.command,
        data=data,
        text=result.text,
        error=result.error,
    )


def _dedupe_text(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            deduped.append(value)
            seen.add(value)
    return deduped


def _parse_sidecar_output(stdout: str) -> Any:
    if not stdout:
        return {}
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return stdout

    if isinstance(parsed, dict):
        content = parsed.get("content")
        if isinstance(content, list) and len(content) == 1:
            item = content[0]
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str):
                    return _parse_sidecar_output(text)
    return parsed
