"""Tests for project filtering and sync-state helpers."""

from __future__ import annotations

from codebrain.domains.brain import indexing


def test_snapshot_project_filters_common_noise(tmp_path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "pkg.js").write_text("noise", encoding="utf-8")

    snapshot = indexing.snapshot_project(str(tmp_path))

    assert snapshot["file_count"] == 1
    assert snapshot["sample_files"] == ["src/app.py"]
    assert snapshot["skipped"]["excluded"] == 1


def test_sync_status_changes_after_recording_state(tmp_path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")

    first = indexing.sync_status(str(tmp_path))
    indexing.record_index_state(str(tmp_path), first["snapshot"], {"ok": True, "status": "ok"})
    second = indexing.sync_status(str(tmp_path))

    assert first["needs_sync"] is True
    assert second["needs_sync"] is False
    assert second["reason"] == "fresh"


def test_record_index_state_replaces_file_atomically(tmp_path) -> None:
    snapshot = indexing.snapshot_project(str(tmp_path))

    result = indexing.record_index_state(str(tmp_path), snapshot, {"ok": True})

    assert result["ok"] is True
    assert indexing.load_index_state(str(tmp_path))["ok"] is True
    assert not indexing.index_state_path(str(tmp_path)).with_suffix(".json.tmp").exists()
