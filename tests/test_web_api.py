from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from recordtree.app import RecordTreeApp
from recordtree.db import connect
from recordtree.importer.service import ImportService
from recordtree.models import ImportRecord, LinkItem
from recordtree.repositories import ImportRepository, utc_now_sql
from recordtree.web.api import app


def _record() -> ImportRecord:
    return ImportRecord(
        source_type="xlsx",
        actor_raw="API Actor",
        delivery_date="2026-01-02",
        title="API ASMR title",
        entry_date="2026-01-03",
        note="api note",
        upload_title="API upload",
        duplicate_search_raw="API ASMR upload",
        source_name="niconico",
        size_raw=None,
        size_bytes=600,
        mega_file_name="api",
        mega_total_bytes=600,
        mega_formatted_size=None,
        mega_json="{}",
        source_row_number=2,
        links=[
            LinkItem(1, "https://example.invalid/api/1", ".mp4", 100, "100 B"),
            LinkItem(2, "https://example.invalid/api/2", ".m4a", 200, "200 B"),
            LinkItem(3, "https://example.invalid/api/3", ".par2", 300, "300 B"),
        ],
    )


def _setup_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.chdir(tmp_path)
    RecordTreeApp().init()
    conn = connect(tmp_path / "env" / "recordtree.sqlite3")
    try:
        source = tmp_path / "fixture.xlsx"
        source.write_bytes(b"xlsx placeholder")
        import_id = ImportRepository(conn).create_import("xlsx", source)
        ImportService(conn).upsert_record(import_id, _record())
        group_id = int(conn.execute("SELECT id FROM record_groups").fetchone()[0])
        first_link_id = int(
            conn.execute(
                "SELECT id FROM download_links WHERE mega_url = ?",
                ("https://example.invalid/api/1",),
            ).fetchone()[0]
        )
        _insert_download(conn, group_id, first_link_id, "completed")
        conn.commit()
        return group_id
    finally:
        conn.close()


def _insert_download(conn, group_id: int, link_id: int, status: str) -> None:
    cursor = conn.execute(
        f"""
        INSERT INTO downloads (
            record_group_id, requested_at, output_dir, selected_bytes,
            free_bytes_before, status, mega_exit_code, message
        )
        VALUES (?, {utc_now_sql()}, '', 0, NULL, ?, NULL, NULL)
        """,
        (group_id, status),
    )
    conn.execute(
        f"""
        INSERT INTO download_items (
            download_id, link_id, status, started_at, finished_at, mega_exit_code, message
        )
        VALUES (?, ?, ?, {utc_now_sql()}, {utc_now_sql()}, 0, NULL)
        """,
        (int(cursor.lastrowid), link_id, status),
    )


def test_health_and_init_endpoints(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)

    assert client.get("/api/health").json() == {"status": "ok"}

    response = client.post("/api/init")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "1"
    assert Path(payload["database_path"]) == tmp_path / "env" / "recordtree.sqlite3"
    assert (tmp_path / "env" / "recordtree.sqlite3").exists()


def test_search_detail_stats_and_download_plan_endpoints(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    group_id = _setup_record(tmp_path, monkeypatch)
    client = TestClient(app)

    actors = client.get("/api/actors", params={"query": "api"}).json()
    assert actors[0]["name"] == "API Actor"
    assert actors[0]["record_count"] == 1

    actor_records = client.get(f"/api/actors/{actors[0]['id']}/records").json()
    assert actor_records[0]["id"] == group_id

    assert client.get("/api/records/search/title", params={"query": "asmr"}).json()[0]["id"] == group_id
    assert client.get("/api/records/search/source", params={"query": "nico"}).json()[0]["id"] == group_id
    assert client.get("/api/records/search/date", params={"from": "2026-01-01", "to": "2026-01-31"}).json()[0]["id"] == group_id
    assert client.get("/api/records/undownloaded").json()[0]["id"] == group_id

    detail = client.get(f"/api/records/{group_id}").json()
    assert detail["downloaded"] == "partial"
    assert len(detail["links"]) == 3

    stats = client.get("/api/stats").json()
    assert stats["total_record_groups"] == 1
    assert stats["downloaded_partial"] == 1

    plan = client.post(
        f"/api/records/{group_id}/download-plan",
        json={"types": ["mp4", "m4a"], "only_undownloaded": True},
    ).json()
    assert plan["record_group_id"] == group_id
    assert plan["output_dir"].endswith(f"downloads\\{group_id}") or plan["output_dir"].endswith(f"downloads/{group_id}")
    assert [link["file_type"] for link in plan["selected_links"]] == [".m4a"]
    assert plan["type_filter"] == [".m4a", ".mp4"]


def test_api_maps_project_errors_to_http_responses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _setup_record(tmp_path, monkeypatch)
    client = TestClient(app)

    bad_limit = client.get("/api/actors", params={"query": "api", "limit": 0})
    assert bad_limit.status_code == 400
    assert bad_limit.json()["error"] == "ValidationError"

    missing = client.get("/api/records/999999")
    assert missing.status_code == 404
    assert missing.json()["error"] == "NotFoundError"

    bad_date = client.get("/api/records/search/date")
    assert bad_date.status_code == 400
    assert bad_date.json()["error"] == "ValidationError"
