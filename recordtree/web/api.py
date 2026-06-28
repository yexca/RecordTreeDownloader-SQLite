from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from recordtree.app import RecordTreeApp
from recordtree.exceptions import ConfigError, NotFoundError, RecordTreeError, ValidationError

from .schemas import DownloadPlanRequest
from .serializers import to_json_safe


app = FastAPI(title="RecordTreeDownloader API")


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


@app.get("/api/doctor")
def doctor() -> dict[str, object]:
    return _serialize(RecordTreeApp().doctor())


@app.get("/api/stats")
def stats() -> dict[str, object]:
    return _serialize(RecordTreeApp().stats())


@app.get("/api/actors")
def actors(query: str = "", limit: int = 50) -> list[dict[str, object]]:
    return _serialize(RecordTreeApp().search_actor(query, limit))


@app.get("/api/actors/{actor_id}/records")
def actor_records(actor_id: int, limit: int = 50) -> list[dict[str, object]]:
    return _serialize(RecordTreeApp().list_actor_records(actor_id, limit))


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

