from __future__ import annotations

from threading import Event

from codebrain.domains.brain import jobs


def test_running_job_reports_heartbeat_and_thread_state() -> None:
    release = Event()
    job = jobs.start_job("wait", lambda: _wait(release))

    status = jobs.get_job(job["id"])
    release.set()

    assert status["ok"] is True
    assert status["status"] in {"queued", "running"}
    assert status["thread_alive"] is True
    assert status["elapsed_seconds"] >= 0


def _wait(release: Event) -> dict[str, bool]:
    release.wait(timeout=2)
    return {"ok": True}
