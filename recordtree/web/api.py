from __future__ import annotations

import re
import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, File, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from recordtree.app import RecordTreeApp
from recordtree.exceptions import ConfigError, NotFoundError, RecordTreeError, ValidationError

from .schemas import ActorDownloadRequest, DownloadPlanRequest, DownloadRequest, MegaLoginRequest
from .serializers import to_json_safe
from .jobs import JobManager



@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        RecordTreeApp().init()
    except RecordTreeError:
        pass
    yield


app = FastAPI(title="RecordTreeDownloader API", lifespan=lifespan)
job_manager = JobManager()
UPLOAD_DIR = Path("files/uploads")
ALLOWED_IMPORT_EXTENSIONS = {".xlsx", ".xlsm", ".json", ".db", ".sqlite", ".sqlite3"}
SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._ -]+")
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"


@app.exception_handler(ConfigError)
@app.exception_handler(ValidationError)
async def bad_request_handler(_request, exc: RecordTreeError) -> JSONResponse:
    return _error_response(400, exc)


@app.exception_handler(NotFoundError)
async def not_found_handler(_request, exc: NotFoundError) -> JSONResponse:
    return _error_response(404, exc)


@app.exception_handler(RecordTreeError)
async def recordtree_error_handler(_request, exc: RecordTreeError) -> JSONResponse:
    return _error_response(500, exc)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/init")
def init() -> dict[str, object]:
    return _serialize(RecordTreeApp().init())


@app.post("/api/imports")
def create_import(file: Annotated[UploadFile, File()]) -> dict[str, object]:
    if not file.filename:
        raise ValidationError("Uploaded file must have a filename.")
    filename = _safe_filename(file.filename)
    extension = Path(filename).suffix.casefold()
    if extension not in ALLOWED_IMPORT_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_IMPORT_EXTENSIONS))
        raise ValidationError(f"Unsupported import file extension: {extension or '(none)'}. Allowed: {allowed}")
    upload_dir = UPLOAD_DIR.resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    source_path = upload_dir / f"{_short_token()}_{filename}"
    with source_path.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)
    job = job_manager.start_import(source_path)
    return {"job_id": job.id, "status": job.status}


@app.get("/api/imports")
def imports(
    status: str | None = None,
    source_type: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, object]:
    return _serialize(
        RecordTreeApp().list_imports(
            page=page,
            page_size=page_size,
            status=status,
            source_type=source_type,
        )
    )


@app.get("/api/imports/{import_id}")
def import_detail(import_id: int) -> dict[str, object]:
    return _serialize(RecordTreeApp().get_import(import_id))


@app.get("/api/imports/{import_id}/errors")
def import_errors(import_id: int, page: int = 1, page_size: int = 100) -> dict[str, object]:
    return _serialize(RecordTreeApp().list_import_errors(import_id, page=page, page_size=page_size))


@app.get("/api/downloads")
def downloads(
    status: str | None = None,
    record_id: int | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, object]:
    return _serialize(
        RecordTreeApp().list_downloads(
            page=page,
            page_size=page_size,
            status=status,
            record_id=record_id,
        )
    )


@app.post("/api/downloads")
def create_download(request: DownloadRequest) -> dict[str, object]:
    job = job_manager.start_download(request)
    return {"job_id": job.id, "status": job.status}


@app.post("/api/downloads/actor")
def create_actor_download(request: ActorDownloadRequest) -> dict[str, object]:
    job = job_manager.start_actor_download(request)
    return {"job_id": job.id, "status": job.status}


@app.post("/api/downloads/{download_id}/resume")
def resume_download(download_id: int) -> dict[str, object]:
    request = DownloadRequest(**RecordTreeApp().get_download_resume_request(download_id))
    job = job_manager.start_download(request)
    return {"job_id": job.id, "status": job.status}


@app.get("/api/downloads/{download_id}")
def download_detail(download_id: int) -> dict[str, object]:
    return _serialize(RecordTreeApp().get_download(download_id))


@app.get("/api/downloads/{download_id}/items")
def download_items(download_id: int) -> list[dict[str, object]]:
    return _serialize(RecordTreeApp().list_download_items(download_id))


@app.get("/api/downloads/{download_id}/log")
def download_log(download_id: int) -> dict[str, str]:
    return {"text": RecordTreeApp().get_download_log(download_id)}


@app.get("/api/jobs")
def jobs(kind: Literal["import", "download"] | None = None, active: bool | None = None) -> list[dict[str, object]]:
    return _serialize([job_manager.serialize(job) for job in job_manager.list(kind=kind, active=active)])


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, object]:
    try:
        job = job_manager.get(job_id)
    except KeyError as error:
        raise NotFoundError(f"Job not found: {job_id}") from error
    return job_manager.serialize(job)


@app.get("/api/jobs/{job_id}/events")
def job_events(job_id: str, after: int = 0) -> StreamingResponse:
    try:
        payloads = job_manager.stream_events(job_id, after)
    except KeyError as error:
        raise NotFoundError(f"Job not found: {job_id}") from error
    return StreamingResponse(payloads, media_type="text/event-stream")


@app.get("/api/doctor")
def doctor() -> dict[str, object]:
    return _serialize(RecordTreeApp().doctor())


@app.get("/api/mega/status")
def mega_status() -> dict[str, object]:
    return _serialize(RecordTreeApp().mega_status())


@app.post("/api/mega/login")
def mega_login(request: MegaLoginRequest) -> dict[str, object]:
    return _serialize(
        RecordTreeApp().mega_login(
            email=request.email,
            password=request.password,
            auth_code=request.auth_code,
        )
    )


@app.post("/api/mega/logout")
def mega_logout() -> dict[str, object]:
    return _serialize(RecordTreeApp().mega_logout())


@app.get("/api/stats")
def stats() -> dict[str, object]:
    return _serialize(RecordTreeApp().stats())


@app.get("/api/maintenance/summary")
def maintenance_summary() -> dict[str, object]:
    return _serialize(RecordTreeApp().maintenance_summary())


@app.post("/api/maintenance/backup")
def maintenance_backup() -> dict[str, object]:
    return _serialize(RecordTreeApp().backup_database())


@app.get("/api/maintenance/backups")
def maintenance_backups() -> list[dict[str, object]]:
    return _serialize(RecordTreeApp().list_backups())


@app.get("/api/maintenance/backups/{filename}")
def maintenance_download_backup(filename: str) -> FileResponse:
    backup_path = RecordTreeApp().backup_path(filename)
    return FileResponse(
        backup_path,
        media_type="application/vnd.sqlite3",
        filename=backup_path.name,
    )


@app.post("/api/maintenance/integrity-check")
def maintenance_integrity_check() -> dict[str, object]:
    return _serialize(RecordTreeApp().database_integrity())


@app.get("/api/maintenance/orphans")
def maintenance_orphans() -> dict[str, object]:
    return _serialize(RecordTreeApp().orphan_report())


@app.post("/api/maintenance/analyze")
def maintenance_analyze() -> dict[str, object]:
    return _serialize(RecordTreeApp().analyze_database())


@app.post("/api/maintenance/vacuum")
def maintenance_vacuum() -> dict[str, object]:
    return _serialize(RecordTreeApp().vacuum_database())


@app.get("/api/actors")
def actors(query: str = "", limit: int = 50) -> list[dict[str, object]]:
    return _serialize(RecordTreeApp().search_actor(query, limit))


@app.get("/api/actors/page")
def actor_page(query: str = "", page: int = 1, page_size: int = 50) -> dict[str, object]:
    return _serialize(RecordTreeApp().list_actor_page(query, page=page, page_size=page_size))


@app.get("/api/actors/undownloaded-counts")
def actor_undownloaded_counts(ids: str = "") -> dict[str, int]:
    return {str(key): value for key, value in RecordTreeApp().actor_undownloaded_counts(_parse_ids(ids)).items()}


@app.get("/api/actors/{actor_id}")
def actor(actor_id: int) -> dict[str, object]:
    return _serialize(RecordTreeApp().get_actor(actor_id))


@app.get("/api/actors/{actor_id}/records")
def actor_records(actor_id: int, limit: int = 50) -> list[dict[str, object]]:
    return _serialize(RecordTreeApp().list_actor_records(actor_id, limit))


@app.get("/api/platforms")
def platforms(query: str = "", limit: int = 50) -> list[dict[str, object]]:
    return _serialize(RecordTreeApp().search_platform(query, limit))


@app.get("/api/platforms/page")
def platform_page(query: str = "", page: int = 1, page_size: int = 50) -> dict[str, object]:
    return _serialize(RecordTreeApp().list_platform_page(query, page=page, page_size=page_size))


@app.get("/api/platforms/undownloaded-counts")
def platform_undownloaded_counts(ids: str = "") -> dict[str, int]:
    return {str(key): value for key, value in RecordTreeApp().platform_undownloaded_counts(_parse_ids(ids)).items()}


@app.get("/api/platforms/{source_id}")
def platform(source_id: int) -> dict[str, object]:
    return _serialize(RecordTreeApp().get_platform(source_id))


@app.get("/api/platforms/{source_id}/records")
def platform_records(source_id: int, limit: int = 50) -> list[dict[str, object]]:
    return _serialize(RecordTreeApp().list_platform_records(source_id, limit))


@app.get("/api/records")
def records(
    record_id: int | None = None,
    title: str = "",
    actor: str = "",
    source: str = "",
    date_from: str | None = None,
    date_to: str | None = None,
    downloaded: str | None = None,
    file_type: str | None = None,
    only_undownloaded: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, object]:
    return _serialize(
        RecordTreeApp().list_records(
            record_id=record_id,
            title=title,
            actor=actor,
            source=source,
            date_from=date_from,
            date_to=date_to,
            downloaded=downloaded,
            file_type=file_type,
            only_undownloaded=only_undownloaded,
            page=page,
            page_size=page_size,
        )
    )


@app.get("/api/records/search/title")
def search_title(query: str = "", limit: int = 50) -> list[dict[str, object]]:
    return _serialize(RecordTreeApp().search_title(query, limit))


@app.get("/api/records/search/source")
def search_source(query: str = "", limit: int = 50) -> list[dict[str, object]]:
    return _serialize(RecordTreeApp().search_source(query, limit))


@app.get("/api/records/search/date")
def search_date(
    date_from: Annotated[str | None, Query(alias="from")] = None,
    date_to: Annotated[str | None, Query(alias="to")] = None,
    limit: int = 50,
) -> list[dict[str, object]]:
    return _serialize(RecordTreeApp().search_date(date_from, date_to, limit))


@app.get("/api/records/undownloaded")
def undownloaded(
    actor: str | None = None,
    actor_id: int | None = None,
    source: str | None = None,
    limit: int = 50,
) -> list[dict[str, object]]:
    return _serialize(
        RecordTreeApp().list_undownloaded(
            actor=actor,
            actor_id=actor_id,
            source=source,
            limit=limit,
        )
    )


@app.get("/api/records/{record_id_or_key}")
def record_detail(record_id_or_key: str) -> dict[str, object]:
    return _serialize(RecordTreeApp().info(record_id_or_key))


@app.post("/api/records/{record_id_or_key}/download-plan")
def download_plan(record_id_or_key: str, request: DownloadPlanRequest) -> dict[str, object]:
    return _serialize(
        RecordTreeApp().build_download_plan(
            record_id_or_key=record_id_or_key,
            include_par2=request.include_par2,
            types=request.types_text(),
            output=request.output_path(),
            only_undownloaded=request.only_undownloaded,
        )
    )


def _serialize(value):
    return to_json_safe(value)


def _error_response(status_code: int, exc: RecordTreeError) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": str(exc),
            "error": exc.__class__.__name__,
        },
    )


def _safe_filename(filename: str) -> str:
    name = Path(filename).name.strip().replace("\\", "_")
    cleaned = SAFE_FILENAME_RE.sub("_", name).strip(" .")
    if not cleaned:
        raise ValidationError("Uploaded file must have a usable filename.")
    return cleaned


def _parse_ids(value: str) -> list[int]:
    if not value.strip():
        return []
    ids: list[int] = []
    for part in value.split(","):
        text = part.strip()
        if not text:
            continue
        if not text.isdigit():
            raise ValidationError("ids must be a comma-separated list of positive integers.")
        ids.append(int(text))
    return ids


def _short_token() -> str:
    return uuid.uuid4().hex[:12]


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="web")
