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
        runner: Runner | None = None,
    ) -> None:
        self.binary = binary
        self.timeout_sec = timeout_sec
        self.search_timeout_sec = min(search_timeout_sec, timeout_sec)
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
        args: dict[str, Any] = {
            "repo_path": _resolve_path(repo_path),
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
            "project": project_name_from_path(repo_path),
            "name_pattern": symbol,
            "limit": limit,
        }
        return self.call("search_graph", args, timeout_sec=self.search_timeout_sec).as_dict()

    def trace_call_path(
        self,
        symbol: str,
        repo_path: str,
        depth: int = 2,
    ) -> dict[str, Any]:
        """Trace callers and callees for a symbol."""
        args = {
            "project": project_name_from_path(repo_path),
            "function_name": symbol,
            "direction": "both",
            "depth": depth,
        }
        return self.call("trace_call_path", args, timeout_sec=self.search_timeout_sec).as_dict()

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
            error=stderr,
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
    resolved = _resolve_path(path)
    chars: list[str] = []
    previous = ""
    for char in resolved:
        safe = char.isascii() and (char.isalnum() or char in "._-")
        normalized = char if safe else "-"
        if (normalized == "-" and previous == "-") or (
            normalized == "." and previous == "."
        ):
            continue
        chars.append(normalized)
        previous = normalized

    candidate = "".join(chars).lstrip("-.").rstrip("-")
    return candidate or "root"


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
