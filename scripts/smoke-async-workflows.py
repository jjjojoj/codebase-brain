"""Smoke-test Qoder-sensitive asynchronous workflows."""

from __future__ import annotations

import argparse
import json
import time

try:
    from codebrain.config import Settings
    from codebrain.core.di import init_container
    from codebrain.domains.brain.tools import brain_context_for_task, brain_index_job_status
    from codebrain.domains.history.tools import get_co_changed_files
except ModuleNotFoundError as exc:
    if exc.name == "codebrain":
        raise SystemExit(
            "Codebrain is not installed in this Python environment. "
            "Run: python -m pip install -e '.[local]'"
        ) from exc
    raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-path", required=True)
    parser.add_argument("--file-path", required=True)
    parser.add_argument("--task", default="understand the authentication flow")
    parser.add_argument("--wait-seconds", type=float, default=10)
    args = parser.parse_args()

    init_container(Settings())

    context = _submit(
        "context",
        lambda: brain_context_for_task(args.task, repo_path=args.repo_path),
    )
    co_changed = _submit(
        "co_changed",
        lambda: get_co_changed_files(args.file_path, repo_path=args.repo_path),
    )

    deadline = time.monotonic() + args.wait_seconds
    pending = {
        "context": context["job"]["id"],
        "co_changed": co_changed["job"]["id"],
    }
    while pending and time.monotonic() < deadline:
        time.sleep(0.5)
        for name, job_id in list(pending.items()):
            status = brain_index_job_status(job_id)
            print(f"{name}_status={json.dumps(status, ensure_ascii=True)}")
            if status.get("status") in {"succeeded", "failed"}:
                pending.pop(name)

    if pending:
        print(f"still_running={json.dumps(pending, ensure_ascii=True)}")


def _submit(name: str, call) -> dict:
    started = time.perf_counter()
    result = call()
    elapsed = round(time.perf_counter() - started, 3)
    print(f"{name}_submit_seconds={elapsed}")
    print(f"{name}_submit={json.dumps(result, ensure_ascii=True)}")
    if elapsed >= 5:
        raise RuntimeError(f"{name} async submission took too long: {elapsed}s")
    if result.get("status") != "queued":
        raise RuntimeError(f"{name} did not queue: {result}")
    return result


if __name__ == "__main__":
    main()
