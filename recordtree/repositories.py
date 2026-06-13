from __future__ import annotations

from pathlib import Path
import sqlite3

from .models import DownloadPlan, ImportRecord, ImportStats, LinkItem
from .normalizers import build_link_content_hash, clean_text, normalize_search_text


def utc_now_sql() -> str:
    return "strftime('%Y-%m-%dT%H:%M:%fZ','now')"


class ImportRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create_import(self, source_type: str, source_path: Path, status: str = "running") -> int:
        stat = source_path.stat()
        cursor = self.conn.execute(
            f"""
            INSERT INTO imports (
                source_type, source_path, source_file_name, source_file_size,
                started_at, status
            )
            VALUES (?, ?, ?, ?, {utc_now_sql()}, ?)
            """,
            (source_type, str(source_path), source_path.name, stat.st_size, status),
        )
        return int(cursor.lastrowid)

    def finish_import(
        self,
        import_id: int,
        stats: ImportStats,
        status: str,
        notes: str | None = None,
    ) -> None:
        self.conn.execute(
            f"""
            UPDATE imports
            SET finished_at = {utc_now_sql()},
                status = ?,
                total_rows = ?,
                inserted_groups = ?,
                updated_groups = ?,
                skipped_groups = ?,
                link_sets_changed = ?,
                inserted_links = ?,
                skipped_links = ?,
                error_count = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                status,
                stats.total_rows,
                stats.inserted_groups,
                stats.updated_groups,
                stats.skipped_groups,
                stats.link_sets_changed,
                stats.inserted_links,
                stats.skipped_links,
                stats.error_count,
                notes,
                import_id,
            ),
        )

    def fail_import(self, import_id: int, message: str) -> None:
        self.conn.execute(
            f"""
            UPDATE imports
            SET finished_at = {utc_now_sql()}, status = 'failed', notes = ?
            WHERE id = ?
            """,
            (message, import_id),
        )

    def add_import_error(
        self,
        import_id: int,
        row_number: int | None,
        source_key: str | None,
        error_type: str,
        message: str,
        raw_value: str | None,
    ) -> None:
        self.conn.execute(
            f"""
            INSERT INTO import_errors (
                import_id, row_number, source_key, error_type, message, raw_value, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, {utc_now_sql()})
            """,
            (import_id, row_number, source_key, error_type, message, raw_value),
        )

    def list_errors(self, import_id: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            """
            SELECT import_id, row_number, source_key, error_type, message, raw_value, created_at
            FROM import_errors
            WHERE import_id = ?
            ORDER BY id
            """,
            (import_id,),
        ).fetchall()


class RecordGroupRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get_group_by_source_key(self, source_key: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM record_groups WHERE source_key = ?",
            (source_key,),
        ).fetchone()

    def insert_group(self, record: ImportRecord, source_key: str, now: str) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO record_groups (
                source_key, source_type, actor_raw, delivery_date, title, entry_date,
                note, upload_title, duplicate_search_raw, source_name, size_raw, size_bytes,
                mega_file_name, mega_total_bytes, mega_formatted_size, mega_json,
                source_row_number, first_imported_at, last_seen_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _record_values(record, source_key) + (now, now, now),
        )
        return int(cursor.lastrowid)

    def update_group_seen(self, group_id: int, record: ImportRecord, now: str) -> None:
        self.conn.execute(
            """
            UPDATE record_groups
            SET source_type = ?,
                actor_raw = ?,
                delivery_date = ?,
                title = ?,
                entry_date = ?,
                note = ?,
                upload_title = ?,
                duplicate_search_raw = ?,
                source_name = ?,
                size_raw = ?,
                size_bytes = ?,
                mega_file_name = ?,
                mega_total_bytes = ?,
                mega_formatted_size = ?,
                mega_json = ?,
                source_row_number = ?,
                last_seen_at = ?,
                updated_at = ?,
                is_deleted = 0
            WHERE id = ?
            """,
            (
                record.source_type,
                record.actor_raw,
                record.delivery_date,
                record.title,
                record.entry_date,
                record.note,
                record.upload_title,
                record.duplicate_search_raw,
                record.source_name,
                record.size_raw,
                record.size_bytes,
                record.mega_file_name,
                record.mega_total_bytes,
                record.mega_formatted_size,
                record.mega_json,
                record.source_row_number,
                now,
                now,
                group_id,
            ),
        )


class LinkRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def list_active_links(self, group_id: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            """
            SELECT *
            FROM download_links
            WHERE record_group_id = ? AND is_deleted = 0
            ORDER BY link_order, id
            """,
            (group_id,),
        ).fetchall()

    def touch_active_links(self, group_id: int, now: str) -> None:
        self.conn.execute(
            """
            UPDATE download_links
            SET last_seen_at = ?
            WHERE record_group_id = ? AND is_deleted = 0
            """,
            (now, group_id),
        )

    def mark_active_links_deleted(self, group_id: int, now: str) -> None:
        self.conn.execute(
            """
            UPDATE download_links
            SET is_deleted = 1, deleted_at = ?
            WHERE record_group_id = ? AND is_deleted = 0
            """,
            (now, group_id),
        )

    def insert_link(self, group_id: int, item: LinkItem, now: str) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO download_links (
                record_group_id, link_order, mega_url, file_type, size_bytes,
                formatted_size, content_hash, first_seen_at, last_seen_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                group_id,
                item.link_order,
                item.mega_url,
                item.file_type,
                item.size_bytes,
                item.formatted_size,
                build_link_content_hash(item),
                now,
                now,
            ),
        )
        return int(cursor.lastrowid)

    def find_active_link_by_url(self, url: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM download_links WHERE mega_url = ? AND is_deleted = 0",
            (url,),
        ).fetchone()

    def find_active_links_by_url(self, url: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM download_links WHERE mega_url = ? AND is_deleted = 0 ORDER BY id",
            (url,),
        ).fetchall()

    def update_legacy_ids(self, link_id: int, legacy_record_id: int, legacy_author_id: int) -> None:
        self.conn.execute(
            """
            UPDATE download_links
            SET legacy_record_id = ?, legacy_author_id = ?
            WHERE id = ?
            """,
            (legacy_record_id, legacy_author_id, link_id),
        )


class ActorRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def ensure_mapping(self, group_id: int, name: object) -> None:
        cleaned = clean_text(name)
        if cleaned is None:
            return
        cursor = self.conn.execute(
            """
            INSERT INTO actors (name, name_normalized)
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET name_normalized = excluded.name_normalized
            RETURNING id
            """,
            (cleaned, normalize_search_text(cleaned)),
        )
        actor_id = int(cursor.fetchone()["id"])
        self.conn.execute(
            """
            INSERT OR IGNORE INTO record_group_actors (record_group_id, actor_id)
            VALUES (?, ?)
            """,
            (group_id, actor_id),
        )


class SourceRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def ensure_mapping(self, group_id: int, name: object) -> None:
        cleaned = clean_text(name)
        if cleaned is None:
            return
        cursor = self.conn.execute(
            """
            INSERT INTO sources (name, name_normalized)
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET name_normalized = excluded.name_normalized
            RETURNING id
            """,
            (cleaned, normalize_search_text(cleaned)),
        )
        source_id = int(cursor.fetchone()["id"])
        self.conn.execute(
            """
            INSERT OR IGNORE INTO record_group_sources (record_group_id, source_id)
            VALUES (?, ?)
            """,
            (group_id, source_id),
        )


class DownloadRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def insert_legacy_completed(
        self,
        record_group_id: int,
        link_id: int,
        selected_bytes: int,
        downloaded_date: str | None,
        raw_downloaded_date: str,
    ) -> int:
        message = f"Migrated from legacy database downloaded_date={raw_downloaded_date}"
        cursor = self.conn.execute(
            f"""
            INSERT INTO downloads (
                record_group_id, requested_at, output_dir, selected_bytes,
                free_bytes_before, status, mega_exit_code, message
            )
            VALUES (?, {utc_now_sql()}, '', ?, NULL, 'legacy_completed', NULL, ?)
            """,
            (record_group_id, selected_bytes, message),
        )
        download_id = int(cursor.lastrowid)
        self.conn.execute(
            """
            INSERT INTO download_items (
                download_id, link_id, status, started_at, finished_at, mega_exit_code, message
            )
            VALUES (?, ?, 'legacy_completed', NULL, ?, NULL, ?)
            """,
            (download_id, link_id, downloaded_date, message),
        )
        return download_id

    def legacy_completed_exists(self, link_id: int) -> bool:
        row = self.conn.execute(
            """
            SELECT 1
            FROM download_items
            WHERE link_id = ? AND status = 'legacy_completed'
            LIMIT 1
            """,
            (link_id,),
        ).fetchone()
        return row is not None

    def create_download(
        self,
        record_group_id: int,
        output_dir: Path,
        selected_bytes: int,
        free_bytes_before: int | None,
        status: str,
        message: str | None = None,
    ) -> int:
        cursor = self.conn.execute(
            f"""
            INSERT INTO downloads (
                record_group_id, requested_at, output_dir, selected_bytes,
                free_bytes_before, status, mega_exit_code, message
            )
            VALUES (?, {utc_now_sql()}, ?, ?, ?, ?, NULL, ?)
            """,
            (
                record_group_id,
                str(output_dir),
                selected_bytes,
                free_bytes_before,
                status,
                message,
            ),
        )
        return int(cursor.lastrowid)

    def update_download_status(
        self,
        download_id: int,
        status: str,
        mega_exit_code: int | None = None,
        message: str | None = None,
    ) -> None:
        self.conn.execute(
            """
            UPDATE downloads
            SET status = ?, mega_exit_code = ?, message = ?
            WHERE id = ?
            """,
            (status, mega_exit_code, message, download_id),
        )

    def create_download_item(self, download_id: int, link_id: int, status: str = "planned") -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO download_items (
                download_id, link_id, status, started_at, finished_at, mega_exit_code, message
            )
            VALUES (?, ?, ?, NULL, NULL, NULL, NULL)
            """,
            (download_id, link_id, status),
        )
        return int(cursor.lastrowid)

    def start_download_item(self, item_id: int) -> None:
        self.conn.execute(
            f"""
            UPDATE download_items
            SET status = 'running', started_at = {utc_now_sql()}
            WHERE id = ?
            """,
            (item_id,),
        )

    def finish_download_item(
        self,
        item_id: int,
        status: str,
        mega_exit_code: int | None,
        message: str | None,
    ) -> None:
        self.conn.execute(
            f"""
            UPDATE download_items
            SET status = ?, finished_at = {utc_now_sql()},
                mega_exit_code = ?, message = ?
            WHERE id = ?
            """,
            (status, mega_exit_code, message, item_id),
        )

    def create_from_plan(self, plan: DownloadPlan, status: str, message: str | None = None) -> int:
        return self.create_download(
            record_group_id=plan.record_group_id,
            output_dir=plan.output_dir,
            selected_bytes=plan.selected_bytes,
            free_bytes_before=plan.free_bytes_before,
            status=status,
            message=message,
        )


class LegacyMigrationRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get_mapping(self, legacy_record_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM legacy_migration_map WHERE legacy_record_id = ?",
            (legacy_record_id,),
        ).fetchone()

    def insert_mapping(
        self,
        legacy_record_id: int,
        legacy_author_id: int,
        record_group_id: int,
        link_id: int,
        legacy_downloaded_date: str | None,
        now: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO legacy_migration_map (
                legacy_record_id, legacy_author_id, record_group_id,
                link_id, legacy_downloaded_date, migrated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                legacy_record_id,
                legacy_author_id,
                record_group_id,
                link_id,
                legacy_downloaded_date,
                now,
            ),
        )


def _record_values(record: ImportRecord, source_key: str) -> tuple[object, ...]:
    return (
        source_key,
        record.source_type,
        record.actor_raw,
        record.delivery_date,
        record.title,
        record.entry_date,
        record.note,
        record.upload_title,
        record.duplicate_search_raw,
        record.source_name,
        record.size_raw,
        record.size_bytes,
        record.mega_file_name,
        record.mega_total_bytes,
        record.mega_formatted_size,
        record.mega_json,
        record.source_row_number,
    )
