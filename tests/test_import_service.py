from __future__ import annotations

from pathlib import Path

import pytest

from recordtree.db import connect, initialize_schema
from recordtree.exceptions import ValidationError
from recordtree.importer.service import ImportService
from recordtree.models import ImportRecord, LinkItem
from recordtree.normalizers import (
    build_link_set_hash,
    build_source_key,
    clean_text,
    normalize_date,
    normalize_file_type,
)
from recordtree.repositories import ImportRepository
from recordtree.sizes import calculate_required_bytes, format_bytes, parse_size_text


def _conn(tmp_path: Path):
    conn = connect(tmp_path / "test.sqlite3")
    initialize_schema(conn)
    return conn


def _record(
    *,
    title: str = "Title",
    url: str = "https://example.invalid/file/a",
    row: int = 2,
    links: list[LinkItem] | None = None,
) -> ImportRecord:
    return ImportRecord(
        source_type="xlsx",
        actor_raw="Actor",
        delivery_date="2026-01-02",
        title=title,
        entry_date="2026-01-03",
        note=None,
        upload_title=f"{title} upload",
        duplicate_search_raw=None,
        source_name="Source",
        size_raw="1 MB",
        size_bytes=1024 * 1024,
        mega_file_name=f"{title}.mp4",
        mega_total_bytes=1024,
        mega_formatted_size="1 KB",
        mega_json="{}",
        source_row_number=row,
        links=links
        or [
            LinkItem(
                link_order=1,
                mega_url=url,
                file_type="mp4",
                size_bytes=1024,
                formatted_size="1 KB",
            )
        ],
    )


def _import_id(conn, tmp_path: Path) -> int:
    source = tmp_path / "source.xlsx"
    source.write_bytes(b"placeholder")
    return ImportRepository(conn).create_import("xlsx", source)


def test_normalizers_sizes_and_hashes() -> None:
    assert clean_text("  abc  ") == "abc"
    assert clean_text("   ") is None
    assert normalize_date("2026/01/02") == "2026-01-02"
    assert normalize_file_type("MP4") == ".mp4"
    assert parse_size_text("1.5 GB") == 1610612736
    assert parse_size_text("not a size") is None
    assert calculate_required_bytes(100, 10, 1) == 1048676
    assert format_bytes(1024) == "1.00 KB"

    one = build_source_key(_record(title="Case"))
    two = build_source_key(_record(title="case"))
    assert one == two
    assert build_link_set_hash(_record().links) == build_link_set_hash(_record().links)

    with pytest.raises(ValidationError):
        normalize_date("not-a-date")


def test_first_import_inserts_group_links_and_mappings(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    try:
        import_id = _import_id(conn, tmp_path)
        result = ImportService(conn).upsert_record(import_id, _record())

        assert result.inserted_groups == 1
        assert result.inserted_links == 1
        assert conn.execute("SELECT COUNT(*) FROM record_groups").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM download_links WHERE is_deleted = 0").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM record_group_actors").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM record_group_sources").fetchone()[0] == 1
    finally:
        conn.close()


def test_reimport_same_record_is_idempotent(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    try:
        import_id = _import_id(conn, tmp_path)
        service = ImportService(conn)

        service.upsert_record(import_id, _record())
        result = service.upsert_record(import_id, _record())

        assert result.updated_groups == 1
        assert result.skipped_links == 1
        assert conn.execute("SELECT COUNT(*) FROM download_links WHERE is_deleted = 0").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM record_group_actors").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM record_group_sources").fetchone()[0] == 1
    finally:
        conn.close()


def test_changed_link_set_preserves_inactive_history(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    try:
        import_id = _import_id(conn, tmp_path)
        service = ImportService(conn)

        service.upsert_record(import_id, _record())
        changed = _record(
            links=[
                LinkItem(1, "https://example.invalid/file/b", ".mp4", 2048, "2 KB"),
                LinkItem(2, "https://example.invalid/file/c", ".srt", 128, "128 B"),
            ]
        )
        result = service.upsert_record(import_id, changed)

        assert result.link_sets_changed == 1
        assert result.inserted_links == 2
        assert conn.execute("SELECT COUNT(*) FROM download_links WHERE is_deleted = 0").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM download_links WHERE is_deleted = 1").fetchone()[0] == 1
    finally:
        conn.close()


def test_active_url_conflict_records_error(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    try:
        import_id = _import_id(conn, tmp_path)
        service = ImportService(conn)

        service.upsert_record(import_id, _record(title="One", url="https://example.invalid/file/shared"))
        result = service.upsert_record(import_id, _record(title="Two", url="https://example.invalid/file/shared"))

        assert result.inserted_groups == 1
        assert result.inserted_links == 0
        error = conn.execute("SELECT * FROM import_errors").fetchone()
        assert error["error_type"] == "active_url_conflict"
        assert error["raw_value"] == "https://example.invalid/file/shared"
    finally:
        conn.close()
