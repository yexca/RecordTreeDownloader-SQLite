from __future__ import annotations

import json
import threading
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from recordtree.app import RecordTreeApp
from recordtree.models import ImportProgress

from .serializers import to_json_safe
from .schemas import ActorDownloadRequest, DownloadRequest

JobStatus = Literal["queued", "running", "completed", "failed"]
JobKind = Literal["import", "download"]
ACTIVE_STATUSES = {"queued", "running"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class JobEvent:
    index: int
    type: str
    created_at: str
    data: dict[str, Any]


@dataclass
class Job:
    id: str
    kind: JobKind
    status: JobStatus = "queued"
    created_at: str = field(default_factory=utc_now_iso)
    started_at: str | None = None
    finished_at: str | None = None
    events: list[JobEvent] = field(default_factory=list)
    target: dict[str, Any] | None = None
    options: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None


class JobManager:
    def __init__(self, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="recordtree-job")
        self._jobs: dict[str, Job] = {}
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)

    def start_import(self, source_path: Path, app_factory: Callable[[], RecordTreeApp] = RecordTreeApp) -> Job:
        job = Job(id=uuid.uuid4().hex, kind="import", target={"source_path": source_path})
        self._add_event(job, "queued", {"source_path": source_path})
        with self._lock:
            self._jobs[job.id] = job
        self._executor.submit(self._run_import, job.id, source_path, app_factory)
        return self.get(job.id)

    def start_download(
        self,
        request: DownloadRequest,
        app_factory: Callable[[], RecordTreeApp] = RecordTreeApp,
    ) -> Job:
        target = {"record_id_or_key": request.record_id_or_key}
        options = {
            "include_par2": request.include_par2,
            "types": request.types_text(),
            "output": request.output_path(),
            "only_undownloaded": request.only_undownloaded,
        }
        job = Job(id=uuid.uuid4().hex, kind="download", target=target, options=options)
        self._add_event(job, "queued", {"target": target, "options": options})
        with self._lock:
            self._jobs[job.id] = job
        self._executor.submit(self._run_download, job.id, request, app_factory)
        return self.get(job.id)

    def start_actor_download(
        self,
        request: ActorDownloadRequest,
        app_factory: Callable[[], RecordTreeApp] = RecordTreeApp,
    ) -> Job:
        target = {"actor_id": request.actor_id}
        options = {
            "count": request.count,
            "include_par2": request.include_par2,
            "types": request.types_text(),
            "output": request.output_path(),
        }
        job = Job(id=uuid.uuid4().hex, kind="download", target=target, options=options)
        self._add_event(job, "queued", {"target": target, "options": options})
        with self._lock:
            self._jobs[job.id] = job
        self._executor.submit(self._run_actor_download, job.id, request, app_factory)
        return self.get(job.id)

    def get(self, job_id: str) -> Job:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            return _copy_job(job)

    def list(self, kind: JobKind | None = None, active: bool | None = None) -> list[Job]:
        with self._lock:
            jobs = list(self._jobs.values())
            if kind is not None:
                jobs = [job for job in jobs if job.kind == kind]
            if active is True:
                jobs = [job for job in jobs if job.status in ACTIVE_STATUSES]
            elif active is False:
                jobs = [job for job in jobs if job.status not in ACTIVE_STATUSES]
            return [_copy_job(job) for job in sorted(jobs, key=lambda item: item.created_at, reverse=True)]

    def list_events(self, job_id: str, after: int = 0) -> list[JobEvent]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            return [event for event in job.events if event.index > after]

    def stream_events(
        self,
        job_id: str,
        after: int = 0,
        keepalive_seconds: float = 15.0,
    ):
        next_index = max(0, after)
        while True:
            with self._condition:
                job = self._jobs.get(job_id)
                if job is None:
                    raise KeyError(job_id)
                pending = [event for event in job.events if event.index > next_index]
                if pending:
                    payloads = [_format_sse(event) for event in pending]
                    next_index = pending[-1].index
                    done = job.status in {"completed", "failed"}
                else:
                    if job.status in {"completed", "failed"}:
                        return
                    self._condition.wait(timeout=keepalive_seconds)
                    latest_job = self._jobs.get(job_id)
                    if latest_job is None:
                        raise KeyError(job_id)
                    has_new_events = any(event.index > next_index for event in latest_job.events)
                    payloads = [] if has_new_events else [f": keepalive {int(time.time())}\n\n"]
                    done = False
            for payload in payloads:
                yield payload
            if done:
                return

    def serialize(self, job: Job) -> dict[str, Any]:
        progress = None
        for event in reversed(job.events):
            if event.type == "progress":
                progress = event.data
                break
        return to_json_safe(
            {
                "id": job.id,
                "kind": job.kind,
                "status": job.status,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "finished_at": job.finished_at,
                "progress": progress,
                "target": job.target,
                "options": job.options,
                "events": job.events,
                "result": job.result,
                "error": job.error,
            }
        )

    def sse_payloads(self, job_id: str, after: int = 0) -> list[str]:
        return [_format_sse(event) for event in self.list_events(job_id, after)]

    def _run_import(self, job_id: str, source_path: Path, app_factory: Callable[[], RecordTreeApp]) -> None:
        self._mark_running(job_id)
        try:
            result = app_factory().import_file(source_path, progress_callback=lambda progress: self._record_progress(job_id, progress))
        except Exception as error:
            self._mark_failed(job_id, str(error))
            return
        self._mark_completed(job_id, to_json_safe(result))

    def _run_download(
        self,
        job_id: str,
        request: DownloadRequest,
        app_factory: Callable[[], RecordTreeApp],
    ) -> None:
        self._mark_running(job_id)
        try:
            result = app_factory().download(
                record_id_or_key=request.record_id_or_key,
                include_par2=request.include_par2,
                types=request.types_text(),
                output=request.output_path(),
                assume_yes=True,
                only_undownloaded=request.only_undownloaded,
                output_callback=lambda chunk: self._record_output(job_id, chunk),
            )
        except Exception as error:
            self._mark_failed(job_id, str(error))
            return
        self._finish_download(job_id, to_json_safe(result), result.status)

    def _run_actor_download(
        self,
        job_id: str,
        request: ActorDownloadRequest,
        app_factory: Callable[[], RecordTreeApp],
    ) -> None:
        self._mark_running(job_id)
        try:
            result = app_factory().download_actor(
                actor_id=request.actor_id,
                limit=request.count,
                include_par2=request.include_par2,
                types=request.types_text(),
                output=request.output_path(),
                assume_yes=True,
                output_callback=lambda chunk: self._record_output(job_id, chunk),
            )
        except Exception as error:
            self._mark_failed(job_id, str(error))
            return
        statuses = {item.status for item in result.results}
        final_status = "failed" if statuses & {"blocked", "failed", "cancelled"} else "completed"
        self._finish_download(job_id, to_json_safe(result), final_status)

    def _record_progress(self, job_id: str, progress: ImportProgress) -> None:
        self._add_event_by_id(
            job_id,
            "progress",
            {
                "phase": progress.phase,
                "source_type": progress.source_type,
                "source_path": progress.source_path,
                "completed_rows": progress.completed_rows,
                "total_rows": progress.total_rows,
            },
        )

    def _record_output(self, job_id: str, chunk: str) -> None:
        self._add_event_by_id(job_id, "output", {"chunk": chunk})

    def _mark_running(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "running"
            job.started_at = utc_now_iso()
            self._add_event(job, "running", {})

    def _mark_completed(self, job_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "completed"
            job.finished_at = utc_now_iso()
            job.result = result
            self._add_event(job, "completed", {"result": result})

    def _finish_download(self, job_id: str, result: dict[str, Any], result_status: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.result = result
            if result_status in {"blocked", "failed", "cancelled"}:
                job.status = "failed"
                job.error = result.get("message") or f"Download ended with status: {result_status}"
                event_type = "failed"
                data = {"error": job.error, "result": result}
            else:
                job.status = "completed"
                event_type = "completed"
                data = {"result": result}
            job.finished_at = utc_now_iso()
            self._add_event(job, event_type, data)

    def _mark_failed(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "failed"
            job.finished_at = utc_now_iso()
            job.error = error
            self._add_event(job, "failed", {"error": error})

    def _add_event_by_id(self, job_id: str, event_type: str, data: dict[str, Any]) -> None:
        with self._lock:
            self._add_event(self._jobs[job_id], event_type, data)

    def _add_event(self, job: Job, event_type: str, data: dict[str, Any]) -> None:
        with self._condition:
            job.events.append(
                JobEvent(
                    index=len(job.events) + 1,
                    type=event_type,
                    created_at=utc_now_iso(),
                    data=to_json_safe(data),
                )
            )
            self._condition.notify_all()


def _copy_job(job: Job) -> Job:
    return Job(
        id=job.id,
        kind=job.kind,
        status=job.status,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        events=list(job.events),
        target=job.target,
        options=dict(job.options),
        result=job.result,
        error=job.error,
    )


def _format_sse(event: JobEvent) -> str:
    return (
        f"id: {event.index}\n"
        f"event: {event.type}\n"
        f"data: {json.dumps(to_json_safe(event), ensure_ascii=False)}\n\n"
    )
