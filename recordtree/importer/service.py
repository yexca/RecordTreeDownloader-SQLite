from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import sqlite3

from recordtree.exceptions import ImportRowError
from recordtree.models import ImportRecord, LinkItem
from recordtree.normalizers import (
    build_link_set_hash,
    build_source_key,
    clean_text,
    normalize_file_type,
)
from recordtree.repositories import (
    ActorRepository,
    ImportRepository,
    LinkRepository,
    RecordGroupRepository,
    SourceRepository,
)


@dataclass(frozen=True)
class UpsertResult:
    inserted_groups: int = 0
    updated_groups: int = 0
    skipped_groups: int = 0
    link_sets_changed: int = 0
    inserted_links: int = 0
    skipped_links: int = 0
    errors_recorded: int = 0


class ImportService:
    def __init__(self, conn: sqlite3.Connection, prefer_xlsx_metadata: bool = True) -> None:
        self.conn = conn
        self.prefer_xlsx_metadata = prefer_xlsx_metadata
        self.imports = ImportRepository(conn)
        self.groups = RecordGroupRepository(conn)
        self.links = LinkRepository(conn)
        self.actors = ActorRepository(conn)
        self.sources = SourceRepository(conn)

    def upsert_record(self, import_id: int, record: ImportRecord) -> UpsertResult:
        self._validate_record(record)
        now = _utc_now()
        source_key = build_source_key(record)
        group = self.groups.get_group_by_source_key(source_key)

        if group is None:
            if self._all_links_overlap_xlsx(import_id, record, source_key):
                return UpsertResult(skipped_groups=1, errors_recorded=len(record.links))
            group_id = self.groups.insert_group(record, source_key, now)
            self.actors.ensure_mapping(group_id, record.actor_raw)
            self.sources.ensure_mapping(group_id, record.source_name)
            inserted, errors = self._insert_all_links(import_id, group_id, record, now)
            return UpsertResult(inserted_groups=1, inserted_links=inserted, errors_recorded=errors)

        group_id = int(group["id"])
        if self._should_preserve_existing_metadata(group_id, record):
            self.links.touch_active_links(group_id, now)
            return UpsertResult(skipped_groups=1, skipped_links=len(record.links))
        self.groups.update_group_seen(group_id, record, now)
        self.actors.ensure_mapping(group_id, record.actor_raw)
        self.sources.ensure_mapping(group_id, record.source_name)

        active_links = self.links.list_active_links(group_id)
        old_hash = build_link_set_hash(_rows_to_link_items(active_links))
        new_hash = build_link_set_hash(record.links)
        if old_hash == new_hash:
            self.links.touch_active_links(group_id, now)
            return UpsertResult(updated_groups=1, skipped_links=len(record.links))

        self.links.mark_active_links_deleted(group_id, now)
        inserted, errors = self._insert_all_links(import_id, group_id, record, now)
        return UpsertResult(
            updated_groups=1,
            link_sets_changed=1,
            inserted_links=inserted,
            errors_recorded=errors,
        )

    def record_error(self, import_id: int, error: ImportRowError) -> None:
        self.imports.add_import_error(
            import_id=import_id,
            row_number=error.row_number,
            source_key=error.source_key,
            error_type=error.error_type,
            message=error.message,
            raw_value=error.raw_value,
        )

    def _insert_all_links(
        self,
        import_id: int,
        group_id: int,
        record: ImportRecord,
        now: str,
    ) -> tuple[int, int]:
        inserted = 0
        errors = 0
        for raw_item in record.links:
            item = LinkItem(
                link_order=raw_item.link_order,
                mega_url=clean_text(raw_item.mega_url) or "",
                file_type=normalize_file_type(raw_item.file_type),
                size_bytes=raw_item.size_bytes,
                formatted_size=clean_text(raw_item.formatted_size),
            )
            existing = self.links.find_active_link_by_url(item.mega_url)
            if existing is not None and int(existing["record_group_id"]) == group_id:
                self.links.touch_active_links(group_id, now)
                continue
            if existing is not None and self._should_skip_json_overlap(record, existing):
                self.record_error(
                    import_id,
                    ImportRowError(
                        "json_xlsx_overlap",
                        f"JSON link already belongs to xlsx record_group_id={existing['record_group_id']}; xlsx metadata preserved.",
                        row_number=record.source_row_number,
                        source_key=build_source_key(record),
                        raw_value=item.mega_url,
                    ),
                )
                errors += 1
                continue
            if existing is not None:
                self.record_error(
                    import_id,
                    ImportRowError(
                        "active_url_conflict",
                        f"Active URL already belongs to record_group_id={existing['record_group_id']}",
                        row_number=record.source_row_number,
                        source_key=build_source_key(record),
                        raw_value=item.mega_url,
                    ),
                )
                errors += 1
                continue
            self.links.insert_link(group_id, item, now)
            inserted += 1
        return inserted, errors

    def _all_links_overlap_xlsx(self, import_id: int, record: ImportRecord, source_key: str) -> bool:
        if not self.prefer_xlsx_metadata or record.source_type != "json" or not record.links:
            return False

        overlapping: list[tuple[LinkItem, sqlite3.Row]] = []
        for link in record.links:
            url = clean_text(link.mega_url)
            if url is None:
                return False
            existing = self.links.find_active_link_by_url(url)
            if existing is None or not self._row_is_xlsx_group(existing):
                return False
            overlapping.append((link, existing))

        for link, existing in overlapping:
            self.record_error(
                import_id,
                ImportRowError(
                    "json_xlsx_overlap",
                    f"JSON link already belongs to xlsx record_group_id={existing['record_group_id']}; xlsx metadata preserved.",
                    row_number=record.source_row_number,
                    source_key=source_key,
                    raw_value=link.mega_url,
                ),
            )
        return True

    def _should_preserve_existing_metadata(self, group_id: int, record: ImportRecord) -> bool:
        if not self.prefer_xlsx_metadata or record.source_type != "json":
            return False
        active_links = self.links.list_active_links(group_id)
        for link in active_links:
            if self._row_is_xlsx_group(link):
                return True
        return False

    def _should_skip_json_overlap(self, record: ImportRecord, existing: sqlite3.Row) -> bool:
        return (
            self.prefer_xlsx_metadata
            and record.source_type == "json"
            and self._row_is_xlsx_group(existing)
        )

    def _row_is_xlsx_group(self, link: sqlite3.Row) -> bool:
        row = self.conn.execute(
            "SELECT source_type FROM record_groups WHERE id = ?",
            (int(link["record_group_id"]),),
        ).fetchone()
        return row is not None and row["source_type"] == "xlsx"

    def _validate_record(self, record: ImportRecord) -> None:
        required = {
            "actor_raw": record.actor_raw,
            "title": record.title,
            "upload_title": record.upload_title,
            "source_name": record.source_name,
        }
        for field, value in required.items():
            if clean_text(value) is None:
                raise ImportRowError(
                    "required_field_missing",
                    f"Required field is missing: {field}",
                    row_number=record.source_row_number,
                    raw_value=field,
                )
        if not record.links:
            raise ImportRowError(
                "link_set_empty",
                "Record has no MEGA links.",
                row_number=record.source_row_number,
            )
        for link in record.links:
            if clean_text(link.mega_url) is None:
                raise ImportRowError(
                    "mega_link_missing",
                    "MEGA link is missing.",
                    row_number=record.source_row_number,
                )
            if link.size_bytes < 0:
                raise ImportRowError(
                    "mega_size_invalid",
                    "MEGA link size must be non-negative.",
                    row_number=record.source_row_number,
                    raw_value=link.size_bytes,
                )


def apply_upsert_result(stats, result: UpsertResult) -> None:
    stats.inserted_groups += result.inserted_groups
    stats.updated_groups += result.updated_groups
    stats.skipped_groups += result.skipped_groups
    stats.link_sets_changed += result.link_sets_changed
    stats.inserted_links += result.inserted_links
    stats.skipped_links += result.skipped_links
    stats.error_count += result.errors_recorded


def _rows_to_link_items(rows: list[sqlite3.Row]) -> list[LinkItem]:
    return [
        LinkItem(
            link_order=int(row["link_order"]),
            mega_url=row["mega_url"],
            file_type=row["file_type"],
            size_bytes=int(row["size_bytes"]),
            formatted_size=row["formatted_size"],
        )
        for row in rows
    ]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
