"""CLI behavior that must work without optional local embedding dependencies."""

from __future__ import annotations

import importlib

from typer.testing import CliRunner

from codebrain.cli import app
from codebrain.infrastructure.embedder.sentence_transformer import SentenceTransformerEmbedder


def _fail_model_load(self: SentenceTransformerEmbedder) -> None:
    raise AssertionError("minimal command path should not load the embedding model")


def test_info_does_not_load_sentence_transformer_model(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CODEBRAIN_DB_PATH", str(tmp_path / "codebrain.db"))
    monkeypatch.setattr(SentenceTransformerEmbedder, "_load_model", _fail_model_load)

    result = CliRunner().invoke(app, ["info"])

    assert result.exit_code == 0
    assert "Embedder provider:" in result.output


def test_index_empty_conventions_dir_does_not_load_sentence_transformer_model(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("CODEBRAIN_DB_PATH", str(tmp_path / "codebrain.db"))
    monkeypatch.setattr(SentenceTransformerEmbedder, "_load_model", _fail_model_load)
    conventions_dir = tmp_path / "conventions"
    conventions_dir.mkdir()

    result = CliRunner().invoke(app, ["index", "--path", str(conventions_dir)])

    assert result.exit_code == 0
    assert "Indexed 0 files" in result.output


def test_server_module_initialization_does_not_load_sentence_transformer_model(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("CODEBRAIN_DB_PATH", str(tmp_path / "codebrain.db"))
    monkeypatch.setattr(SentenceTransformerEmbedder, "_load_model", _fail_model_load)

    from codebrain import server

    loaded_server = importlib.reload(server)

    assert "health" in loaded_server.mcp._tool_manager._tools
