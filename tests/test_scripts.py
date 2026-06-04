"""Behavior tests for standalone operator scripts."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def test_async_smoke_explains_missing_codebrain_installation() -> None:
    script = Path(__file__).parents[1] / "scripts" / "smoke-async-workflows.py"

    result = subprocess.run(
        [sys.executable, "-I", "-S", str(script), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "Codebrain is not installed in this Python environment" in result.stderr
    assert "pip install -e" in result.stderr
