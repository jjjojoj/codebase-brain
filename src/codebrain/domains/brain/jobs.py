"""In-process background job registry for indexing tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock, Thread
import time
from typing import Any, Callable
from uuid import uuid4


JobTarget = Callable[[], dict[str, Any]]


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class IndexJob:
    """Serializable indexing job state."""

    id: str
    description: str
    status: str = "queued"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    result: dict[str, Any] | None = None
    error: str = ""
    queue_seconds: float | None = None
    execution_seconds: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "result": self.result,
            "error": self.error,
            "queue_seconds": self.queue_seconds,
            "execution_seconds": self.execution_seconds,
        }


_jobs: dict[str, IndexJob] = {}
_threads: dict[str, Thread] = {}
_lock = Lock()


def start_job(description: str, target: JobTarget) -> dict[str, Any]:
    """Start a background indexing job and return initial state."""
    job = IndexJob(id=uuid4().hex, description=description)
    with _lock:
        _jobs[job.id] = job

    thread = Thread(target=_run_job, args=(job.id, target), daemon=True)
    with _lock:
        _threads[job.id] = thread
    thread.start()
    return job.as_dict()


def get_job(job_id: str) -> dict[str, Any]:
    """Return one job, or a structured not-found response."""
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return {"ok": False, "status": "not_found", "job_id": job_id}
        data = job.as_dict()
        thread = _threads.get(job_id)
        if job.status == "running" and thread and thread.is_alive():
            job.updated_at = _now()
            data = job.as_dict()
        data["thread_alive"] = bool(thread and thread.is_alive())
        data["elapsed_seconds"] = _elapsed_seconds(job.created_at)
    data["ok"] = True
    return data


def list_jobs() -> dict[str, Any]:
    """Return all known in-process jobs."""
    with _lock:
        jobs = [job.as_dict() for job in _jobs.values()]
    return {"ok": True, "jobs": jobs}


def clear_jobs_for_tests() -> None:
    """Clear job state for isolated tests."""
    with _lock:
        _jobs.clear()
        _threads.clear()


def _run_job(job_id: str, target: JobTarget) -> None:
    started = time.perf_counter()
    _update_job(job_id, status="running", queue_seconds=_job_age_seconds(job_id))
    try:
        result = target()
    except Exception as exc:
        _update_job(
            job_id,
            status="failed",
            error=str(exc),
            execution_seconds=round(time.perf_counter() - started, 3),
        )
        return
    _update_job(
        job_id,
        status="succeeded",
        result=result,
        execution_seconds=round(time.perf_counter() - started, 3),
    )


def _update_job(
    job_id: str,
    *,
    status: str,
    result: dict[str, Any] | None = None,
    error: str = "",
    queue_seconds: float | None = None,
    execution_seconds: float | None = None,
) -> None:
    with _lock:
        job = _jobs[job_id]
        job.status = status
        job.updated_at = _now()
        if result is not None:
            job.result = result
        if error:
            job.error = error
        if queue_seconds is not None:
            job.queue_seconds = queue_seconds
        if execution_seconds is not None:
            job.execution_seconds = execution_seconds


def _elapsed_seconds(created_at: str) -> float:
    try:
        created = datetime.fromisoformat(created_at)
    except ValueError:
        return 0.0
    return round((datetime.now(UTC) - created).total_seconds(), 3)


def _job_age_seconds(job_id: str) -> float:
    with _lock:
        created_at = _jobs[job_id].created_at
    return _elapsed_seconds(created_at)
