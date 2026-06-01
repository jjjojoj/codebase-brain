"""In-process background job registry for indexing tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock, Thread
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

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "result": self.result,
            "error": self.error,
        }


_jobs: dict[str, IndexJob] = {}
_lock = Lock()


def start_job(description: str, target: JobTarget) -> dict[str, Any]:
    """Start a background indexing job and return initial state."""
    job = IndexJob(id=uuid4().hex, description=description)
    with _lock:
        _jobs[job.id] = job

    thread = Thread(target=_run_job, args=(job.id, target), daemon=True)
    thread.start()
    return job.as_dict()


def get_job(job_id: str) -> dict[str, Any]:
    """Return one job, or a structured not-found response."""
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return {"ok": False, "status": "not_found", "job_id": job_id}
        data = job.as_dict()
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


def _run_job(job_id: str, target: JobTarget) -> None:
    _update_job(job_id, status="running")
    try:
        result = target()
    except Exception as exc:
        _update_job(job_id, status="failed", error=str(exc))
        return
    _update_job(job_id, status="succeeded", result=result)


def _update_job(
    job_id: str,
    *,
    status: str,
    result: dict[str, Any] | None = None,
    error: str = "",
) -> None:
    with _lock:
        job = _jobs[job_id]
        job.status = status
        job.updated_at = _now()
        if result is not None:
            job.result = result
        if error:
            job.error = error
