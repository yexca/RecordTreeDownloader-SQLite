from __future__ import annotations

import json
from pathlib import Path

from recordtree.app import RecordTreeApp
from recordtree.db import connect
from recordtree.exceptions import ValidationError
from recordtree.importer.service import ImportService
from recordtree.models import ImportRecord, LinkItem
from recordtree.repositories import ImportRepository


def _write_json(path: Path, *, shared_url: str = "https://example.invalid/json/shared") -> None:
    path.write_text(
        json.dumps(
            [
                {
                    "author": "JSON Actor",
                    "records": [
                        {
                            "FileNames": "JSON bundle",
                            "total": 3072,
                            "FormattedSize": "3 KB",
                            "property": [
                                {
                                    "Link": "https://example.invalid/json/1",
                                    "Size": 1024,
                                    "FormattedSize": "1 KB",
                                    "Type": "mp4",
                                },
                                {
                                    "Link": "https://example.invalid/json/2",
                                    "Size": 2048,
                                    "FormattedSize": "2 KB",
                                    "Type": ".m4a",
                                },
                            ],
                        },
                        {
                            "FileNames": "Overlapping bundle",
                            "total": 100,
                            "FormattedSize": "100 B",
                            "property": [
                                {
                                    "Link": shared_url,
                                    "Size": 100,
                                    "FormattedSize": "100 B",
                                    "Type": "mp4",
                                }
                            ],
                        },
                        {"FileNames": "Malformed"},
                    ],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _excel_record(shared_url: str) -> ImportRecord:
    return ImportRecord(
        source_type="xlsx",
        actor_raw="Excel Actor",
        delivery_date="2026-01-02",
        title="Excel title",
        entry_date="2026-01-03",
        note="keep me",
        upload_title="Excel upload",
        duplicate_search_raw=None,
        source_name="Excel Source",
        size_raw="100 B",
        size_bytes=100,
        mega_file_name="excel.mp4",
        mega_total_bytes=100,
        mega_formatted_size="100 B",
        mega_json="{}",
        source_row_number=2,
        links=[LinkItem(1, shared_url, ".mp4", 100, "100 B")],
    )


def test_json_import_records_errors_overlap_and_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    RecordTreeApp().init()
    shared_url = "https://example.invalid/excel/shared"

    conn = connect(tmp_path / "env" / "recordtree.sqlite3")
    try:
        source = tmp_path / "fixture.xlsx"
        source.write_bytes(b"xlsx placeholder")
        import_id = ImportRepository(conn).create_import("xlsx", source)
        ImportService(conn).upsert_record(import_id, _excel_record(shared_url))
        conn.commit()
    finally:
        conn.close()

    json_path = tmp_path / "fixture.json"
    _write_json(json_path, shared_url=shared_url)

    first = RecordTreeApp().import_file(json_path)
    second = RecordTreeApp().import_file(json_path)

    assert first.status == "completed_with_errors"
    assert first.stats.total_rows == 3
    assert first.stats.inserted_groups == 1
    assert first.stats.inserted_links == 2
    assert first.stats.error_count == 2
    assert first.error_csv_path is not None
    assert first.error_csv_path.exists()

    assert second.status == "completed_with_errors"
    assert second.stats.inserted_groups == 0
    assert second.stats.updated_groups == 1
    assert second.stats.skipped_links == 2
    assert second.stats.error_count == 2

    conn = connect(tmp_path / "env" / "recordtree.sqlite3")
    try:
        excel = conn.execute("SELECT * FROM record_groups WHERE source_type = 'xlsx'").fetchone()
        assert excel["title"] == "Excel title"
        assert excel["actor_raw"] == "Excel Actor"
        assert conn.execute("SELECT COUNT(*) FROM record_groups WHERE source_type = 'json'").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM download_links WHERE is_deleted = 0").fetchone()[0] == 3
        error_types = {
            row["error_type"]
            for row in conn.execute("SELECT error_type FROM import_errors").fetchall()
        }
        assert "mega_property_invalid" in error_types
        assert "json_xlsx_overlap" in error_types
    finally:
        conn.close()


def test_json_root_must_be_list(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    RecordTreeApp().init()
    path = tmp_path / "bad.json"
    path.write_text("{}", encoding="utf-8")

    try:
        RecordTreeApp().import_file(path)
    except ValidationError as error:
        assert "JSON root must be a list" in str(error)
    else:
        raise AssertionError("Expected JSON root validation error")
