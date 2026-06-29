from __future__ import annotations

from pathlib import Path
import sqlite3

from .models import DownloadDetail, DownloadItemDetail, DownloadPlan, ImportDetail, ImportErrorSummary, ImportRecord, ImportStats, LinkItem
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

    def count_imports(self, status: str | None = None, source_type: str | None = None) -> int:
        where_sql, params = _import_filters(status, source_type)
        row = self.conn.execute(f"SELECT COUNT(*) FROM imports {where_sql}", params).fetchone()
        return int(row[0])

    def list_imports(
        self,
        limit: int,
        offset: int,
        status: str | None = None,
        source_type: str | None = None,
    ) -> list[ImportDetail]:
        where_sql, params = _import_filters(status, source_type)
        rows = self.conn.execute(
            f"""
            SELECT *
            FROM imports
            {where_sql}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            params + (limit, offset),
        ).fetchall()
        return [_import_detail(row) for row in rows]

    def get_import(self, import_id: int) -> ImportDetail | None:
        row = self.conn.execute("SELECT * FROM imports WHERE id = ?", (import_id,)).fetchone()
        return _import_detail(row) if row is not None else None

    def count_errors(self, import_id: int) -> int:
        row = self.conn.execute("SELECT COUNT(*) FROM import_errors WHERE import_id = ?", (import_id,)).fetchone()
        return int(row[0])

    def list_error_details(self, import_id: int, limit: int, offset: int) -> list[ImportErrorSummary]:
        rows = self.conn.execute(
            """
            SELECT *
            FROM import_errors
            WHERE import_id = ?
            ORDER BY id
            LIMIT ? OFFSET ?
            """,
            (import_id, limit, offset),
        ).fetchall()
        return [
            ImportErrorSummary(
                id=int(row["id"]),
                import_id=int(row["import_id"]),
                row_number=row["row_number"],
                source_key=row["source_key"],
                error_type=row["error_type"],
                message=row["message"],
                raw_value=row["raw_value"],
                created_at=row["created_at"],
            )
            for row in rows
        ]


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
        request_json: str | None = None,
    ) -> int:
        cursor = self.conn.execute(
            f"""
            INSERT INTO downloads (
                record_group_id, requested_at, output_dir, selected_bytes,
                free_bytes_before, status, mega_exit_code, message, request_json
            )
            VALUES (?, {utc_now_sql()}, ?, ?, ?, ?, NULL, ?, ?)
            """,
            (
                record_group_id,
                str(output_dir),
                selected_bytes,
                free_bytes_before,
                status,
                message,
                request_json,
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

    def create_from_plan(
        self,
        plan: DownloadPlan,
        status: str,
        message: str | None = None,
        request_json: str | None = None,
    ) -> int:
        return self.create_download(
            record_group_id=plan.record_group_id,
            output_dir=plan.output_dir,
            selected_bytes=plan.selected_bytes,
            free_bytes_before=plan.free_bytes_before,
            status=status,
            message=message,
            request_json=request_json,
        )

    def mark_interrupted_downloads(self, message: str) -> int:
        cursor = self.conn.execute(
            """
            UPDATE downloads
            SET status = 'interrupted',
                message = CASE
                    WHEN message IS NULL OR message = '' THEN ?
                    ELSE message || char(10) || ?
                END
            WHERE status IN ('planned', 'queued', 'running')
            """,
            (message, message),
        )
        self.conn.execute(
            f"""
            UPDATE download_items
            SET status = 'interrupted',
                finished_at = {utc_now_sql()},
                message = CASE
                    WHEN message IS NULL OR message = '' THEN ?
                    ELSE message || char(10) || ?
                END
            WHERE status IN ('planned', 'queued', 'running')
              AND EXISTS (
                  SELECT 1
                  FROM downloads d
                  WHERE d.id = download_items.download_id
                    AND d.status = 'interrupted'
              )
            """,
            (message, message),
        )
        return int(cursor.rowcount)

    def count_downloads(self, status: str | None = None, record_id: int | None = None) -> int:
        where_sql, params = _download_filters(status, record_id)
        row = self.conn.execute(f"SELECT COUNT(*) FROM downloads d {where_sql}", params).fetchone()
        return int(row[0])

    def list_downloads(
        self,
        limit: int,
        offset: int,
        status: str | None = None,
        record_id: int | None = None,
    ) -> list[DownloadDetail]:
        where_sql, params = _download_filters(status, record_id)
        rows = self.conn.execute(
            f"""
            SELECT d.*, rg.title AS record_title, rg.actor_raw, rg.source_name,
                   COUNT(di.id) AS item_count,
                   COUNT(CASE WHEN di.status IN ('completed', 'legacy_completed') THEN 1 END) AS completed_count,
                   COUNT(CASE WHEN di.status = 'failed' THEN 1 END) AS failed_count
            FROM downloads d
            JOIN record_groups rg ON rg.id = d.record_group_id
            LEFT JOIN download_items di ON di.download_id = d.id
            {where_sql}
            GROUP BY d.id
            ORDER BY d.id DESC
            LIMIT ? OFFSET ?
            """,
            params + (limit, offset),
        ).fetchall()
        return [_download_detail(row) for row in rows]

    def get_download(self, download_id: int) -> DownloadDetail | None:
        row = self.conn.execute(
            """
            SELECT d.*, rg.title AS record_title, rg.actor_raw, rg.source_name,
                   COUNT(di.id) AS item_count,
                   COUNT(CASE WHEN di.status IN ('completed', 'legacy_completed') THEN 1 END) AS completed_count,
                   COUNT(CASE WHEN di.status = 'failed' THEN 1 END) AS failed_count
            FROM downloads d
            JOIN record_groups rg ON rg.id = d.record_group_id
            LEFT JOIN download_items di ON di.download_id = d.id
            WHERE d.id = ?
            GROUP BY d.id
            """,
            (download_id,),
        ).fetchone()
        return _download_detail(row) if row is not None else None

    def list_download_items(self, download_id: int) -> list[DownloadItemDetail]:
        rows = self.conn.execute(
            """
            SELECT di.*, dl.link_order, dl.mega_url, dl.file_type, dl.size_bytes, dl.formatted_size
            FROM download_items di
            JOIN download_links dl ON dl.id = di.link_id
            WHERE di.download_id = ?
            ORDER BY dl.link_order, di.id
            """,
            (download_id,),
        ).fetchall()
        return [
            DownloadItemDetail(
                id=int(row["id"]),
                download_id=int(row["download_id"]),
                link_id=int(row["link_id"]),
                link_order=int(row["link_order"]),
                mega_url=row["mega_url"],
                file_type=row["file_type"],
                size_bytes=int(row["size_bytes"]),
                formatted_size=row["formatted_size"],
                status=row["status"],
                started_at=row["started_at"],
                finished_at=row["finished_at"],
                mega_exit_code=row["mega_exit_code"],
                message=row["message"],
            )
            for row in rows
        ]


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


def _import_filters(status: str | None, source_type: str | None) -> tuple[str, tuple[object, ...]]:
    clauses: list[str] = []
    params: list[object] = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if source_type:
        clauses.append("source_type = ?")
        params.append(source_type)
    return ("WHERE " + " AND ".join(clauses) if clauses else "", tuple(params))


def _download_filters(status: str | None, record_id: int | None) -> tuple[str, tuple[object, ...]]:
    clauses: list[str] = []
    params: list[object] = []
    if status:
        clauses.append("d.status = ?")
        params.append(status)
    if record_id is not None:
        clauses.append("d.record_group_id = ?")
        params.append(record_id)
    return ("WHERE " + " AND ".join(clauses) if clauses else "", tuple(params))


def _import_detail(row: sqlite3.Row) -> ImportDetail:
    return ImportDetail(
        id=int(row["id"]),
        source_type=row["source_type"],
        source_path=row["source_path"],
        source_file_name=row["source_file_name"],
        source_file_size=row["source_file_size"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        status=row["status"],
        total_rows=int(row["total_rows"] or 0),
        inserted_groups=int(row["inserted_groups"] or 0),
        updated_groups=int(row["updated_groups"] or 0),
        skipped_groups=int(row["skipped_groups"] or 0),
        link_sets_changed=int(row["link_sets_changed"] or 0),
        inserted_links=int(row["inserted_links"] or 0),
        skipped_links=int(row["skipped_links"] or 0),
        error_count=int(row["error_count"] or 0),
        notes=row["notes"],
    )


def _download_detail(row: sqlite3.Row) -> DownloadDetail:
    return DownloadDetail(
        id=int(row["id"]),
        record_group_id=int(row["record_group_id"]),
        record_title=row["record_title"],
        actor=row["actor_raw"],
        source=row["source_name"],
        requested_at=row["requested_at"],
        output_dir=row["output_dir"],
        selected_bytes=int(row["selected_bytes"] or 0),
        free_bytes_before=row["free_bytes_before"],
        status=row["status"],
        mega_exit_code=row["mega_exit_code"],
        message=row["message"],
        request_json=row["request_json"],
        item_count=int(row["item_count"] or 0),
        completed_count=int(row["completed_count"] or 0),
        failed_count=int(row["failed_count"] or 0),
    )
