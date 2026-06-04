from __future__ import annotations

from threading import Event
import time

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
    assert status["queue_seconds"] is not None


def test_completed_job_reports_execution_time() -> None:
    job = jobs.start_job("quick", lambda: {"ok": True})

    for _ in range(100):
        status = jobs.get_job(job["id"])
        if status["status"] == "succeeded":
            break
        time.sleep(0.001)

    assert status["status"] == "succeeded"
    assert status["execution_seconds"] is not None
    assert status["execution_seconds"] >= 0


def test_shutdown_jobs_marks_long_running_job_interrupted() -> None:
    release = Event()
    job = jobs.start_job("wait", lambda: _wait(release))

    jobs.shutdown_jobs(wait_seconds=0)
    status = jobs.get_job(job["id"])
    release.set()

    assert status["status"] == "interrupted"
    assert status["error"] == "server shutting down"


def _wait(release: Event) -> dict[str, bool]:
    release.wait(timeout=2)
    return {"ok": True}
