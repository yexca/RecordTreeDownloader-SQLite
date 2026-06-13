from __future__ import annotations

from pathlib import Path

import pytest

from recordtree.app import RecordTreeApp
from recordtree.db import connect
from recordtree.exceptions import NotFoundError, ValidationError
from recordtree.importer.service import ImportService
from recordtree.models import ImportRecord, LinkItem
from recordtree.repositories import ImportRepository, utc_now_sql


def _record(
    *,
    actor: str,
    title: str,
    upload_title: str,
    source: str,
    delivery_date: str | None,
    entry_date: str,
    links: list[LinkItem],
) -> ImportRecord:
    return ImportRecord(
        source_type="xlsx",
        actor_raw=actor,
        delivery_date=delivery_date,
        title=title,
        entry_date=entry_date,
        note=None,
        upload_title=upload_title,
        duplicate_search_raw=f"{title} {upload_title}",
        source_name=source,
        size_raw=None,
        size_bytes=sum(link.size_bytes for link in links),
        mega_file_name=upload_title,
        mega_total_bytes=sum(link.size_bytes for link in links),
        mega_formatted_size=None,
        mega_json="{}",
        source_row_number=2,
        links=links,
    )


def _setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    monkeypatch.chdir(tmp_path)
    RecordTreeApp().init()
    conn = connect(tmp_path / "env" / "recordtree.sqlite3")
    try:
        source = tmp_path / "fixture.xlsx"
        source.write_bytes(b"xlsx placeholder")
        import_id = ImportRepository(conn).create_import("xlsx", source)
        service = ImportService(conn)
        service.upsert_record(
            import_id,
            _record(
                actor="Actor A",
                title="ASMR sleep",
                upload_title="Quiet upload",
                source="niconico",
                delivery_date="2026-01-02",
                entry_date="2026-01-03",
                links=[
                    LinkItem(1, "https://example.invalid/a/1", ".mp4", 100, "100 B"),
                    LinkItem(2, "https://example.invalid/a/2", ".m4a", 200, "200 B"),
                ],
            ),
        )
        service.upsert_record(
            import_id,
            _record(
                actor="Actor B",
                title="music hour",
                upload_title="Concert upload",
                source="Withny",
                delivery_date="2026-02-02",
                entry_date="2026-02-03",
                links=[LinkItem(1, "https://example.invalid/b/1", ".mp4", 300, "300 B")],
            ),
        )
        service.upsert_record(
            import_id,
            _record(
                actor="Actor C",
                title="Talk",
                upload_title="ASMR upload title",
                source="rPlay",
                delivery_date=None,
                entry_date="2026-03-03",
                links=[LinkItem(1, "https://example.invalid/c/1", ".mp4", 400, "400 B")],
            ),
        )
        groups = {
            row["title"]: int(row["id"])
            for row in conn.execute("SELECT id, title FROM record_groups").fetchall()
        }
        links = {
            row["mega_url"]: int(row["id"])
            for row in conn.execute("SELECT id, mega_url FROM download_links").fetchall()
        }
        _insert_download(conn, groups["ASMR sleep"], links["https://example.invalid/a/1"], "completed")
        _insert_download(conn, groups["music hour"], links["https://example.invalid/b/1"], "legacy_completed")
        conn.commit()
        return groups
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


def test_search_and_info_commands(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    groups = _setup(tmp_path, monkeypatch)
    app = RecordTreeApp()

    actor_rows = app.search_actor("actor a")
    assert [row.title for row in actor_rows] == ["ASMR sleep"]

    title_rows = app.search_title("asmr")
    assert {row.title for row in title_rows} == {"ASMR sleep", "Talk"}

    source_rows = app.search_source("WITH")
    assert [row.title for row in source_rows] == ["music hour"]

    date_rows = app.search_date("2026-01-01", "2026-01-31")
    assert [row.title for row in date_rows] == ["ASMR sleep"]

    undownloaded = app.list_undownloaded()
    assert {row.title for row in undownloaded} == {"ASMR sleep", "Talk"}
    assert app.list_undownloaded(source="rplay")[0].title == "Talk"

    conn = connect(tmp_path / "env" / "recordtree.sqlite3")
    try:
        actor_a_id = int(
            conn.execute("SELECT id FROM actors WHERE name = ?", ("Actor A",)).fetchone()[0]
        )
        actor_b_id = int(
            conn.execute("SELECT id FROM actors WHERE name = ?", ("Actor B",)).fetchone()[0]
        )
    finally:
        conn.close()
    assert [row.title for row in app.list_undownloaded(actor_id=actor_a_id)] == ["ASMR sleep"]
    assert app.list_undownloaded(actor_id=actor_b_id) == []

    detail = app.info(str(groups["ASMR sleep"]))
    assert detail.downloaded == "partial"
    assert detail.active_links == 2
    assert len(detail.links) == 2
    assert {link.status for link in detail.links} == {"completed", "none"}

    by_key = app.info(detail.source_key)
    assert by_key.id == detail.id


def test_stats_and_parameter_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(tmp_path, monkeypatch)
    app = RecordTreeApp()

    stats = app.stats()

    assert stats.total_record_groups == 3
    assert stats.active_link_count == 4
    assert stats.actor_count == 3
    assert stats.source_count == 3
    assert stats.downloaded_all == 1
    assert stats.downloaded_partial == 1
    assert stats.downloaded_none == 1
    assert len(stats.recent_imports) == 1
    assert len(stats.recent_downloads) == 2

    with pytest.raises(ValidationError):
        app.search_actor("actor", limit=0)
    with pytest.raises(ValidationError):
        app.search_date(None, None)
    with pytest.raises(NotFoundError):
        app.info("999999")
