from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from openpyxl import Workbook

from recordtree.app import RecordTreeApp
from recordtree.db import connect


def _mega(url: str, size: int = 1024) -> str:
    return json.dumps(
        {
            "FileNames": "matched",
            "total": size,
            "FormattedSize": "1 KB",
            "property": [
                {
                    "Link": url,
                    "Size": size,
                    "FormattedSize": "1 KB",
                    "Type": ".mp4",
                }
            ],
        }
    )


def _write_excel(path: Path, matched_url: str) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
        [
            "actor_raw",
            "delivery_date",
            "title",
            "entry_date",
            "note",
            "upload_title",
            "duplicate_search_raw",
            "source_name",
            "mega_json",
            "size_raw",
        ]
    )
    sheet.append(
        [
            "Excel Actor",
            "2026-01-01",
            "Matched title",
            "2026-01-02",
            "",
            "Matched upload",
            "",
            "Excel source",
            _mega(matched_url),
            "1 KB",
        ]
    )
    workbook.save(path)


def _write_legacy_db(path: Path, matched_url: str, legacy_only_url: str) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE author (
                author_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                added_date TEXT
            );
            CREATE TABLE record (
                record_id INTEGER PRIMARY KEY,
                author_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                date TEXT,
                size INTEGER,
                link TEXT,
                added_date TEXT,
                downloaded_date TEXT
            );
            """
        )
        conn.executemany(
            "INSERT INTO author (author_id, name, added_date) VALUES (?, ?, ?)",
            [(1, "Legacy Actor A", "2025-01-01"), (2, "Legacy Actor B", "2025-01-02")],
        )
        conn.executemany(
            """
            INSERT INTO record (
                record_id, author_id, name, date, size, link, added_date, downloaded_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (10, 1, "Matched legacy", "2026-01-01", 1024, matched_url, "2025-01-01", "2026-01-02"),
                (11, 2, "Legacy only", "2026-02-01", 2048, legacy_only_url, "2025-01-02", "0"),
                (12, 2, "Missing link", "2026-03-01", 4096, "", "2025-01-03", "0"),
            ],
        )
        conn.commit()
    finally:
        conn.close()


def test_legacy_db_import_matches_creates_and_preserves_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    RecordTreeApp().init()
    matched_url = "https://example.invalid/legacy/matched"
    legacy_only_url = "https://example.invalid/legacy/only"
    workbook = tmp_path / "source.xlsx"
    legacy_db = tmp_path / "legacy.sqlite3"
    _write_excel(workbook, matched_url)
    _write_legacy_db(legacy_db, matched_url, legacy_only_url)

    excel_result = RecordTreeApp().import_file(workbook)
    first = RecordTreeApp().import_file(legacy_db)
    second = RecordTreeApp().import_file(legacy_db)

    assert excel_result.stats.inserted_groups == 1
    assert first.status == "completed_with_errors"
    assert first.stats.total_rows == 3
    assert first.stats.updated_groups == 1
    assert first.stats.inserted_groups == 1
    assert first.stats.inserted_links == 1
    assert first.stats.error_count == 1
    assert second.stats.skipped_groups == 2
    assert second.stats.error_count == 1

    conn = connect(tmp_path / "env" / "recordtree.sqlite3")
    try:
        assert conn.execute("SELECT COUNT(*) FROM record_groups").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM download_links WHERE is_deleted = 0").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM legacy_migration_map").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM download_items WHERE status = 'legacy_completed'").fetchone()[0] == 1
        matched_group_count = conn.execute(
            """
            SELECT COUNT(DISTINCT rg.id)
            FROM record_groups rg
            JOIN download_links dl ON dl.record_group_id = rg.id
            WHERE dl.mega_url = ?
            """,
            (matched_url,),
        ).fetchone()[0]
        assert matched_group_count == 1
        error = conn.execute(
            "SELECT error_type FROM import_errors WHERE error_type = 'legacy_link_missing'"
        ).fetchone()
        assert error is not None
    finally:
        conn.close()
