from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from recordtree.exceptions import ImportRowError, ValidationError
from recordtree.importer.service import ImportService
from recordtree.models import ImportStats, LinkItem, ImportRecord
from recordtree.normalizers import clean_text, normalize_date
from recordtree.repositories import (
    DownloadRepository,
    LegacyMigrationRepository,
    LinkRepository,
)
from recordtree.sizes import parse_size_text


REQUIRED_SCHEMA = {
    "author": {"author_id", "name", "added_date"},
    "record": {
        "record_id",
        "author_id",
        "name",
        "date",
        "size",
        "link",
        "added_date",
        "downloaded_date",
    },
}


@dataclass(frozen=True)
class LegacyRow:
    record_id: int
    author_id: int
    author_name: str
    record_name: str
    record_date: object | None
    size_bytes: int | None
    mega_url: str | None
    added_date: object | None
    downloaded_date: object | None


class LegacyDbImporter:
    def iter_rows(self, path: Path):
        source_conn = sqlite3.connect(path)
        source_conn.row_factory = sqlite3.Row
        try:
            validate_legacy_schema(source_conn)
            for row in source_conn.execute(
                """
                SELECT
                    r.record_id,
                    r.author_id,
                    a.name AS author_name,
                    r.name AS record_name,
                    r.date AS record_date,
                    r.size AS size_bytes,
                    r.link AS mega_url,
                    r.added_date,
                    r.downloaded_date
                FROM record r
                JOIN author a ON a.author_id = r.author_id
                ORDER BY r.record_id
                """
            ):
                yield LegacyRow(
                    record_id=int(row["record_id"]),
                    author_id=int(row["author_id"]),
                    author_name=clean_text(row["author_name"]) or "",
                    record_name=clean_text(row["record_name"]) or "",
                    record_date=row["record_date"],
                    size_bytes=parse_size_text(row["size_bytes"]),
                    mega_url=clean_text(row["mega_url"]),
                    added_date=row["added_date"],
                    downloaded_date=row["downloaded_date"],
                )
        finally:
            source_conn.close()


class LegacyMigrationService:
    def __init__(self, target_conn: sqlite3.Connection, import_id: int) -> None:
        self.conn = target_conn
        self.import_id = import_id
        self.import_service = ImportService(target_conn)
        self.links = LinkRepository(target_conn)
        self.legacy = LegacyMigrationRepository(target_conn)
        self.downloads = DownloadRepository(target_conn)

    def migrate_row(self, row: LegacyRow, stats: ImportStats) -> None:
        existing = self.legacy.get_mapping(row.record_id)
        if existing is not None:
            stats.skipped_groups += 1
            return
        if clean_text(row.mega_url) is None:
            self.import_service.record_error(
                self.import_id,
                ImportRowError(
                    "legacy_link_missing",
                    "Legacy record has no MEGA URL.",
                    row_number=row.record_id,
                    raw_value=row.record_id,
                ),
            )
            stats.error_count += 1
            return

        active_matches = self.links.find_active_links_by_url(row.mega_url or "")
        if len(active_matches) > 1:
            self.import_service.record_error(
                self.import_id,
                ImportRowError(
                    "legacy_url_ambiguous",
                    "Legacy URL matches multiple active links.",
                    row_number=row.record_id,
                    raw_value=row.mega_url,
                ),
            )
            stats.error_count += 1
            return
        if len(active_matches) == 1:
            link = active_matches[0]
            self._write_mapping_and_status(row, int(link["record_group_id"]), int(link["id"]))
            self.links.update_legacy_ids(int(link["id"]), row.record_id, row.author_id)
            stats.updated_groups += 1
            return

        record = self._legacy_record(row)
        result = self.import_service.upsert_record(self.import_id, record)
        stats.inserted_groups += result.inserted_groups
        stats.updated_groups += result.updated_groups
        stats.link_sets_changed += result.link_sets_changed
        stats.inserted_links += result.inserted_links
        stats.skipped_links += result.skipped_links
        created_link = self.links.find_active_link_by_url(row.mega_url or "")
        if created_link is None:
            self.import_service.record_error(
                self.import_id,
                ImportRowError(
                    "legacy_record_conflict",
                    "Legacy-only record did not create an active link.",
                    row_number=row.record_id,
                    raw_value=row.mega_url,
                ),
            )
            stats.error_count += 1
            return
        self.links.update_legacy_ids(int(created_link["id"]), row.record_id, row.author_id)
        self._write_mapping_and_status(
            row,
            int(created_link["record_group_id"]),
            int(created_link["id"]),
        )

    def _legacy_record(self, row: LegacyRow) -> ImportRecord:
        try:
            delivery_date = normalize_date(row.record_date)
        except ValidationError:
            delivery_date = None
        size_bytes = row.size_bytes or 0
        return ImportRecord(
            source_type="legacy_db",
            actor_raw=row.author_name or "unknown",
            delivery_date=delivery_date,
            title=row.record_name or row.mega_url or f"legacy-{row.record_id}",
            entry_date=None,
            note=None,
            upload_title=row.record_name or row.mega_url or f"legacy-{row.record_id}",
            duplicate_search_raw=None,
            source_name="legacy",
            size_raw=None if row.size_bytes is None else str(row.size_bytes),
            size_bytes=row.size_bytes,
            mega_file_name=row.record_name or None,
            mega_total_bytes=row.size_bytes,
            mega_formatted_size=None,
            mega_json=None,
            source_row_number=row.record_id,
            links=[
                LinkItem(
                    link_order=1,
                    mega_url=row.mega_url or "",
                    file_type=None,
                    size_bytes=size_bytes,
                    formatted_size=None,
                )
            ],
        )

    def _write_mapping_and_status(self, row: LegacyRow, group_id: int, link_id: int) -> None:
        downloaded_raw = clean_text(row.downloaded_date)
        now = _utc_now_from_db(self.conn)
        self.legacy.insert_mapping(
            row.record_id,
            row.author_id,
            group_id,
            link_id,
            downloaded_raw,
            now,
        )
        if downloaded_raw is not None and downloaded_raw != "0" and not self.downloads.legacy_completed_exists(link_id):
            try:
                downloaded_date = normalize_date(downloaded_raw)
            except ValidationError:
                downloaded_date = None
            self.downloads.insert_legacy_completed(
                record_group_id=group_id,
                link_id=link_id,
                selected_bytes=row.size_bytes or 0,
                downloaded_date=downloaded_date,
                raw_downloaded_date=downloaded_raw,
            )


def validate_legacy_schema(conn: sqlite3.Connection) -> None:
    tables = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    missing_tables = sorted(set(REQUIRED_SCHEMA) - tables)
    if missing_tables:
        raise ValidationError(f"Missing legacy tables: {', '.join(missing_tables)}")
    for table, required_columns in REQUIRED_SCHEMA.items():
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        missing_columns = sorted(required_columns - columns)
        if missing_columns:
            raise ValidationError(
                f"Missing legacy columns in {table}: {', '.join(missing_columns)}"
            )


def _utc_now_from_db(conn: sqlite3.Connection) -> str:
    return conn.execute("SELECT strftime('%Y-%m-%dT%H:%M:%fZ','now')").fetchone()[0]
