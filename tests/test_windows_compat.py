"""Cross-platform checks for Windows-specific paths and setup safeguards."""

from __future__ import annotations

from pathlib import Path, PureWindowsPath
import re

from codebrain.domains.brain.local_context import select_context_files


def test_windows_paths_normalize_for_context_selection() -> None:
    path = PureWindowsPath(r"src\认证\middleware.py")

    result = select_context_files([str(path)], graph=None)

    assert result == ["src/认证/middleware.py"]


def test_setup_windows_detects_codebrain_and_sidecar_processes() -> None:
    script = (
        Path(__file__).parents[1] / "scripts" / "setup-windows.ps1"
    ).read_text(encoding="utf-8")

    assert re.search(
        r"Get-Process\s+-Name\s+[^\r\n]*codebrain[^\r\n]*codebase-memory-mcp",
        script,
        flags=re.IGNORECASE,
    )
    assert "BEGIN IMMEDIATE" in script
    assert "Codebrain database is locked" in script
