from __future__ import annotations

import sqlite3
import shutil
from pathlib import Path

from .exceptions import NotFoundError, ValidationError
from .models import (
    DownloadLink,
    DownloadPlan,
    DownloadSummary,
    ImportSummary,
    LinkSummary,
    RecordDetail,
    RecordSummary,
    StatsResult,
)
from .normalizers import normalize_date, normalize_search_text
from .sizes import calculate_margin


DEFAULT_LIMIT = 50
MAX_LIMIT = 500


class SearchService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def search_actor(self, name: str, limit: int = DEFAULT_LIMIT) -> list[RecordSummary]:
        return self._list_records(
            """
            WHERE rg.is_deleted = 0
              AND EXISTS (
                  SELECT 1
                  FROM record_group_actors rga
                  JOIN actors a ON a.id = rga.actor_id
                  WHERE rga.record_group_id = rg.id
                    AND a.name_normalized LIKE ?
              )
            """,
            (f"%{normalize_search_text(name)}%",),
            limit,
        )

    def search_title(self, keyword: str, limit: int = DEFAULT_LIMIT) -> list[RecordSummary]:
        text = f"%{normalize_search_text(keyword)}%"
        return self._list_records(
            """
            WHERE rg.is_deleted = 0
              AND (
                  lower(rg.title) LIKE ?
                  OR lower(rg.upload_title) LIKE ?
                  OR lower(COALESCE(rg.duplicate_search_raw, '')) LIKE ?
              )
            """,
            (text, text, text),
            limit,
        )

    def search_source(self, source: str, limit: int = DEFAULT_LIMIT) -> list[RecordSummary]:
        return self._list_records(
            """
            WHERE rg.is_deleted = 0
              AND EXISTS (
                  SELECT 1
                  FROM record_group_sources rgs
                  JOIN sources s ON s.id = rgs.source_id
                  WHERE rgs.record_group_id = rg.id
                    AND s.name_normalized LIKE ?
              )
            """,
            (f"%{normalize_search_text(source)}%",),
            limit,
        )

    def search_date(
        self,
        date_from: str | None,
        date_to: str | None,
        limit: int = DEFAULT_LIMIT,
    ) -> list[RecordSummary]:
        normalized_from = normalize_date(date_from) if date_from else None
        normalized_to = normalize_date(date_to) if date_to else None
        if normalized_from is None and normalized_to is None:
            raise ValidationError("search-date requires --from or --to.")
        clauses = ["rg.is_deleted = 0", "rg.delivery_date IS NOT NULL"]
        params: list[object] = []
        if normalized_from is not None:
            clauses.append("rg.delivery_date >= ?")
            params.append(normalized_from)
        if normalized_to is not None:
            clauses.append("rg.delivery_date <= ?")
            params.append(normalized_to)
        return self._list_records("WHERE " + " AND ".join(clauses), tuple(params), limit)

    def list_undownloaded(
        self,
        actor: str | None = None,
        source: str | None = None,
        limit: int = DEFAULT_LIMIT,
    ) -> list[RecordSummary]:
        clauses = [
            "rg.is_deleted = 0",
            """
            EXISTS (
                SELECT 1
                FROM download_links dl
                WHERE dl.record_group_id = rg.id
                  AND dl.is_deleted = 0
                  AND NOT EXISTS (
                      SELECT 1
                      FROM download_items di
                      WHERE di.link_id = dl.id
                        AND di.status IN ('completed', 'legacy_completed')
                  )
            )
            """,
        ]
        params: list[object] = []
        if actor:
            clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM record_group_actors rga
                    JOIN actors a ON a.id = rga.actor_id
                    WHERE rga.record_group_id = rg.id
                      AND a.name_normalized LIKE ?
                )
                """
            )
            params.append(f"%{normalize_search_text(actor)}%")
        if source:
            clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM record_group_sources rgs
                    JOIN sources s ON s.id = rgs.source_id
                    WHERE rgs.record_group_id = rg.id
                      AND s.name_normalized LIKE ?
                )
                """
            )
            params.append(f"%{normalize_search_text(source)}%")
        return self._list_records("WHERE " + " AND ".join(clauses), tuple(params), limit)

    def get_info(self, record_id_or_key: str) -> RecordDetail:
        if record_id_or_key.isdigit():
            row = self.conn.execute(
                "SELECT * FROM record_groups WHERE id = ? AND is_deleted = 0",
                (int(record_id_or_key),),
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT * FROM record_groups WHERE source_key = ? AND is_deleted = 0",
                (record_id_or_key,),
            ).fetchone()
        if row is None:
            raise NotFoundError(f"Record not found: {record_id_or_key}")

        status = self._status_counts(int(row["id"]))
        links = [
            LinkSummary(
                id=int(link["id"]),
                link_order=int(link["link_order"]),
                mega_url=link["mega_url"],
                file_type=link["file_type"],
                size_bytes=int(link["size_bytes"]),
                formatted_size=link["formatted_size"],
                status=link["status"] or "none",
            )
            for link in self.conn.execute(
                """
                SELECT dl.*,
                       (
                           SELECT di.status
                           FROM download_items di
                           WHERE di.link_id = dl.id
                           ORDER BY di.id DESC
                           LIMIT 1
                       ) AS status
                FROM download_links dl
                WHERE dl.record_group_id = ? AND dl.is_deleted = 0
                ORDER BY dl.link_order, dl.id
                """,
                (int(row["id"]),),
            ).fetchall()
        ]
        inactive_count = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM download_links
            WHERE record_group_id = ? AND is_deleted = 1
            """,
            (int(row["id"]),),
        ).fetchone()[0]
        return RecordDetail(
            id=int(row["id"]),
            source_key=row["source_key"],
            actor=row["actor_raw"],
            delivery_date=row["delivery_date"],
            entry_date=row["entry_date"],
            title=row["title"],
            source=row["source_name"],
            upload_title=row["upload_title"],
            note=row["note"],
            size_bytes=row["size_bytes"],
            size_raw=row["size_raw"],
            active_links=status["active_count"],
            completed_links=status["completed_count"],
            downloaded=_downloaded_label(status["active_count"], status["completed_count"]),
            links=links,
            inactive_link_count=int(inactive_count),
        )

    def build_download_plan(
        self,
        record_id_or_key: str,
        downloads_dir: Path,
        include_par2_by_default: bool,
        include_par2: bool,
        type_filter_text: str | None,
        output_dir: Path | None,
        safety_margin_percent: int,
        safety_margin_min_mb: int,
    ) -> DownloadPlan:
        detail = self.get_info(record_id_or_key)
        links = [
            DownloadLink(
                id=link.id,
                link_order=link.link_order,
                mega_url=link.mega_url,
                file_type=link.file_type,
                size_bytes=link.size_bytes,
                formatted_size=link.formatted_size,
            )
            for link in detail.links
        ]
        should_include_par2 = include_par2 or include_par2_by_default
        if not should_include_par2:
            links = [link for link in links if link.file_type != ".par2"]

        type_filter = parse_type_filter(type_filter_text)
        if type_filter is not None:
            links = [link for link in links if link.file_type in type_filter]
        if not links:
            description = "excluding .par2" if not should_include_par2 else "including .par2"
            if type_filter:
                description += " and applying --types " + ",".join(sorted(type_filter))
            raise ValidationError(f"No links selected after {description}.")

        selected_bytes = sum(link.size_bytes for link in links)
        margin = calculate_margin(selected_bytes, safety_margin_percent, safety_margin_min_mb)
        resolved_output = (
            output_dir.expanduser().resolve()
            if output_dir is not None
            else (downloads_dir / str(detail.id)).resolve()
        )
        check_parent = nearest_existing_parent(resolved_output)
        free_bytes = shutil.disk_usage(check_parent).free
        return DownloadPlan(
            record_group_id=detail.id,
            output_dir=resolved_output,
            actor=detail.actor,
            title=detail.title,
            selected_links=links,
            selected_bytes=selected_bytes,
            margin_bytes=margin,
            required_bytes=selected_bytes + margin,
            free_bytes_before=free_bytes,
            include_par2=should_include_par2,
            type_filter=type_filter,
        )

    def stats(self) -> StatsResult:
        totals = self.conn.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM record_groups WHERE is_deleted = 0) AS groups_count,
                (SELECT COUNT(*) FROM download_links WHERE is_deleted = 0) AS active_links,
                (SELECT COUNT(*) FROM download_links WHERE is_deleted = 1) AS inactive_links,
                (SELECT COUNT(*) FROM actors) AS actors_count,
                (SELECT COUNT(*) FROM sources) AS sources_count
            """
        ).fetchone()
        buckets = {"all": 0, "partial": 0, "none": 0, "unknown": 0}
        for row in self.conn.execute(
            """
            SELECT
                (
                    SELECT COUNT(*)
                    FROM download_links dl
                    WHERE dl.record_group_id = rg.id AND dl.is_deleted = 0
                ) AS active_count,
                (
                    SELECT COUNT(DISTINCT dl.id)
                    FROM download_links dl
                    JOIN download_items di ON di.link_id = dl.id
                    WHERE dl.record_group_id = rg.id
                      AND dl.is_deleted = 0
                      AND di.status IN ('completed', 'legacy_completed')
                ) AS completed_count
            FROM record_groups rg
            WHERE rg.is_deleted = 0
            """
        ).fetchall():
            label = _downloaded_label(int(row["active_count"]), int(row["completed_count"]))
            buckets[label] = buckets.get(label, 0) + 1
        imports = [
            ImportSummary(
                id=int(row["id"]),
                source_type=row["source_type"],
                source_file_name=row["source_file_name"],
                started_at=row["started_at"],
                status=row["status"],
                total_rows=int(row["total_rows"] or 0),
                error_count=int(row["error_count"] or 0),
            )
            for row in self.conn.execute(
                """
                SELECT *
                FROM imports
                ORDER BY id DESC
                LIMIT 5
                """
            ).fetchall()
        ]
        downloads = [
            DownloadSummary(
                id=int(row["id"]),
                record_group_id=int(row["record_group_id"]),
                requested_at=row["requested_at"],
                status=row["status"],
                selected_bytes=int(row["selected_bytes"] or 0),
                message=row["message"],
            )
            for row in self.conn.execute(
                """
                SELECT *
                FROM downloads
                ORDER BY id DESC
                LIMIT 5
                """
            ).fetchall()
        ]
        return StatsResult(
            total_record_groups=int(totals["groups_count"]),
            active_link_count=int(totals["active_links"]),
            inactive_link_count=int(totals["inactive_links"]),
            actor_count=int(totals["actors_count"]),
            source_count=int(totals["sources_count"]),
            downloaded_all=buckets["all"],
            downloaded_partial=buckets["partial"],
            downloaded_none=buckets["none"],
            downloaded_unknown=buckets["unknown"],
            recent_imports=imports,
            recent_downloads=downloads,
        )

    def _list_records(
        self,
        where_sql: str,
        params: tuple[object, ...],
        limit: int,
    ) -> list[RecordSummary]:
        normalized_limit = normalize_limit(limit)
        rows = self.conn.execute(
            f"""
            SELECT rg.*,
                   (
                       SELECT COUNT(*)
                       FROM download_links dl
                       WHERE dl.record_group_id = rg.id AND dl.is_deleted = 0
                   ) AS active_count,
                   (
                       SELECT COUNT(DISTINCT dl.id)
                       FROM download_links dl
                       JOIN download_items di ON di.link_id = dl.id
                       WHERE dl.record_group_id = rg.id
                         AND dl.is_deleted = 0
                         AND di.status IN ('completed', 'legacy_completed')
                   ) AS completed_count
            FROM record_groups rg
            {where_sql}
            ORDER BY rg.delivery_date DESC, rg.entry_date DESC, rg.id DESC
            LIMIT ?
            """,
            params + (normalized_limit,),
        ).fetchall()
        return [_summary_from_row(row) for row in rows]

    def _status_counts(self, group_id: int) -> dict[str, int]:
        row = self.conn.execute(
            """
            SELECT
                (
                    SELECT COUNT(*)
                    FROM download_links
                    WHERE record_group_id = ? AND is_deleted = 0
                ) AS active_count,
                (
                    SELECT COUNT(DISTINCT dl.id)
                    FROM download_links dl
                    JOIN download_items di ON di.link_id = dl.id
                    WHERE dl.record_group_id = ?
                      AND dl.is_deleted = 0
                      AND di.status IN ('completed', 'legacy_completed')
                ) AS completed_count
            """,
            (group_id, group_id),
        ).fetchone()
        return {
            "active_count": int(row["active_count"]),
            "completed_count": int(row["completed_count"]),
        }


def normalize_limit(limit: int) -> int:
    if limit < 1:
        raise ValidationError("Limit must be at least 1.")
    return min(limit, MAX_LIMIT)


def parse_type_filter(value: str | None) -> set[str] | None:
    if value is None or not value.strip():
        return None
    parts = [part.strip().casefold() for part in value.split(",") if part.strip()]
    if not parts:
        return None
    normalized = {part if part.startswith(".") else f".{part}" for part in parts}
    return normalized


def nearest_existing_parent(path: Path) -> Path:
    current = path if path.exists() else path.parent
    while not current.exists():
        parent = current.parent
        if parent == current:
            raise ValidationError(f"No existing parent directory for output path: {path}")
        current = parent
    return current


def preview_url(url: str, edge: int = 24) -> str:
    if len(url) <= edge * 2 + 3:
        return url
    return f"{url[:edge]}...{url[-edge:]}"


def _summary_from_row(row: sqlite3.Row) -> RecordSummary:
    active_count = int(row["active_count"])
    completed_count = int(row["completed_count"])
    return RecordSummary(
        id=int(row["id"]),
        source_key=row["source_key"],
        delivery_date=row["delivery_date"],
        entry_date=row["entry_date"],
        actor=row["actor_raw"],
        title=row["title"],
        source=row["source_name"],
        size_bytes=row["size_bytes"],
        active_links=active_count,
        completed_links=completed_count,
        downloaded=_downloaded_label(active_count, completed_count),
    )


def _downloaded_label(active_count: int, completed_count: int) -> str:
    if active_count == 0:
        return "unknown"
    if completed_count == 0:
        return "none"
    if completed_count < active_count:
        return "partial"
    return "all"
