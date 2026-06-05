from __future__ import annotations

from codebrain.domains.brain import jobs
from codebrain.domains.history import tools


def test_get_blame_defaults_to_async_job(monkeypatch) -> None:
    jobs.clear_jobs_for_tests()
    monkeypatch.setattr(
        tools.git_indexer,
        "get_blame_info",
        lambda repo_path, file_path, start_line, end_line: [
            {"repo_path": repo_path, "file_path": file_path, "line": start_line}
        ],
    )

    result = tools.get_blame("src/App.java", 3, 5, repo_path="/repo")

    assert result["ok"] is True
    assert result["status"] == "queued"
    assert result["job"]["description"] == "blame src/App.java:3-5"

    status = jobs.get_job(result["job"]["id"])
    assert status["ok"] is True
    assert status["status"] in {"queued", "running", "succeeded"}
    jobs.clear_jobs_for_tests()
    status = jobs.get_job(result["job"]["id"])
    assert status["status"] == "not_found"


def test_get_blame_sync_mode_returns_raw_blame_rows(monkeypatch) -> None:
    monkeypatch.setattr(
        tools.git_indexer,
        "get_blame_info",
        lambda repo_path, file_path, start_line, end_line: [
            {"repo_path": repo_path, "file_path": file_path, "line": end_line}
        ],
    )

    result = tools.get_blame("src/App.java", 3, 5, repo_path="/repo", async_mode=False)

    assert result == [{"repo_path": "/repo", "file_path": "src/App.java", "line": 5}]
