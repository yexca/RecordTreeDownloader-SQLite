from __future__ import annotations

import sqlite3
import shutil
from pathlib import Path

from .exceptions import NotFoundError, ValidationError
from .models import (
    ActorPage,
    ActorSummary,
    DownloadLink,
    DownloadPlan,
    DownloadSummary,
    ImportSummary,
    LinkSummary,
    RecordPage,
    RecordDetail,
    RecordSummary,
    SourcePage,
    SourceSummary,
    StatsResult,
)
from .normalizers import normalize_date, normalize_search_text
from .sizes import calculate_margin


DEFAULT_LIMIT = 50
MAX_LIMIT = 500


class SearchService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def search_actor(self, name: str, limit: int = DEFAULT_LIMIT) -> list[ActorSummary]:
        normalized_limit = normalize_limit(limit)
        rows = self.conn.execute(
            """
            SELECT
                a.id,
                a.name,
                COUNT(DISTINCT rg.id) AS record_count,
                COUNT(DISTINCT CASE
                    WHEN EXISTS (
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
                    THEN rg.id
                END) AS undownloaded_count
            FROM actors a
            JOIN record_group_actors rga ON rga.actor_id = a.id
            JOIN record_groups rg ON rg.id = rga.record_group_id
            WHERE rg.is_deleted = 0
              AND a.name_normalized LIKE ?
            GROUP BY a.id, a.name
            ORDER BY a.name COLLATE NOCASE, a.id
            LIMIT ?
            """,
            (f"%{normalize_search_text(name)}%", normalized_limit),
        ).fetchall()
        return [
            ActorSummary(
                id=int(row["id"]),
                name=row["name"],
                record_count=int(row["record_count"]),
                undownloaded_count=int(row["undownloaded_count"]),
            )
            for row in rows
        ]

    def list_actor_page(self, name: str, page: int = 1, page_size: int = DEFAULT_LIMIT) -> ActorPage:
        normalized_page = normalize_page(page)
        normalized_page_size = normalize_limit(page_size)
        text = f"%{normalize_search_text(name)}%"
        total = int(
            self.conn.execute(
                "SELECT COUNT(*) FROM actors WHERE name_normalized LIKE ?",
                (text,),
            ).fetchone()[0]
        )
        offset = (normalized_page - 1) * normalized_page_size
        rows = self.conn.execute(
            """
            SELECT
                a.id,
                a.name,
                COUNT(rg.id) AS record_count
            FROM actors a
            LEFT JOIN record_group_actors rga ON rga.actor_id = a.id
            LEFT JOIN record_groups rg ON rg.id = rga.record_group_id AND rg.is_deleted = 0
            WHERE a.name_normalized LIKE ?
            GROUP BY a.id, a.name
            ORDER BY a.name COLLATE NOCASE, a.id
            LIMIT ? OFFSET ?
            """,
            (text, normalized_page_size, offset),
        ).fetchall()
        total_pages = (total + normalized_page_size - 1) // normalized_page_size if total else 0
        return ActorPage(
            items=[
                ActorSummary(
                    id=int(row["id"]),
                    name=row["name"],
                    record_count=int(row["record_count"]),
                    undownloaded_count=0,
                )
                for row in rows
            ],
            page=normalized_page,
            page_size=normalized_page_size,
            total=total,
            total_pages=total_pages,
        )

    def actor_undownloaded_counts(self, actor_ids: list[int]) -> dict[int, int]:
        ids = _normalized_ids(actor_ids)
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        rows = self.conn.execute(
            f"""
            SELECT rga.actor_id, COUNT(DISTINCT rg.id) AS undownloaded_count
            FROM record_group_actors rga
            JOIN record_groups rg ON rg.id = rga.record_group_id
            WHERE rga.actor_id IN ({placeholders})
              AND rg.is_deleted = 0
              AND {_undownloaded_exists_sql()}
            GROUP BY rga.actor_id
            """,
            tuple(ids),
        ).fetchall()
        counts = {actor_id: 0 for actor_id in ids}
        counts.update({int(row["actor_id"]): int(row["undownloaded_count"]) for row in rows})
        return counts

    def get_actor(self, actor_id: int) -> ActorSummary:
        if actor_id < 1:
            raise ValidationError("Actor id must be at least 1.")
        row = self.conn.execute(
            """
            SELECT
                a.id,
                a.name,
                COUNT(DISTINCT rg.id) AS record_count,
                COUNT(DISTINCT CASE
                    WHEN EXISTS (
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
                    THEN rg.id
                END) AS undownloaded_count
            FROM actors a
            JOIN record_group_actors rga ON rga.actor_id = a.id
            JOIN record_groups rg ON rg.id = rga.record_group_id
            WHERE rg.is_deleted = 0
              AND a.id = ?
            GROUP BY a.id, a.name
            """,
            (actor_id,),
        ).fetchone()
        if row is None:
            raise NotFoundError(f"Actor not found: {actor_id}")
        return ActorSummary(
            id=int(row["id"]),
            name=row["name"],
            record_count=int(row["record_count"]),
            undownloaded_count=int(row["undownloaded_count"]),
        )

    def list_actor_records(self, actor_id: int, limit: int = DEFAULT_LIMIT) -> list[RecordSummary]:
        self._require_actor(actor_id)
        return self._list_records(
            """
            WHERE rg.is_deleted = 0
              AND EXISTS (
                  SELECT 1
                  FROM record_group_actors rga
                  WHERE rga.record_group_id = rg.id
                    AND rga.actor_id = ?
              )
            """,
            (actor_id,),
            limit,
        )

    def search_platform(self, name: str, limit: int = DEFAULT_LIMIT) -> list[SourceSummary]:
        normalized_limit = normalize_limit(limit)
        rows = self.conn.execute(
            """
            SELECT
                s.id,
                s.name,
                COUNT(DISTINCT rg.id) AS record_count,
                COUNT(DISTINCT CASE
                    WHEN EXISTS (
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
                    THEN rg.id
                END) AS undownloaded_count
            FROM sources s
            JOIN record_group_sources rgs ON rgs.source_id = s.id
            JOIN record_groups rg ON rg.id = rgs.record_group_id
            WHERE rg.is_deleted = 0
              AND s.name_normalized LIKE ?
            GROUP BY s.id, s.name
            ORDER BY s.name COLLATE NOCASE, s.id
            LIMIT ?
            """,
            (f"%{normalize_search_text(name)}%", normalized_limit),
        ).fetchall()
        return [
            SourceSummary(
                id=int(row["id"]),
                name=row["name"],
                record_count=int(row["record_count"]),
                undownloaded_count=int(row["undownloaded_count"]),
            )
            for row in rows
        ]

    def list_platform_page(self, name: str, page: int = 1, page_size: int = DEFAULT_LIMIT) -> SourcePage:
        normalized_page = normalize_page(page)
        normalized_page_size = normalize_limit(page_size)
        text = f"%{normalize_search_text(name)}%"
        total = int(
            self.conn.execute(
                "SELECT COUNT(*) FROM sources WHERE name_normalized LIKE ?",
                (text,),
            ).fetchone()[0]
        )
        offset = (normalized_page - 1) * normalized_page_size
        rows = self.conn.execute(
            """
            SELECT
                s.id,
                s.name,
                COUNT(rg.id) AS record_count
            FROM sources s
            LEFT JOIN record_group_sources rgs ON rgs.source_id = s.id
            LEFT JOIN record_groups rg ON rg.id = rgs.record_group_id AND rg.is_deleted = 0
            WHERE s.name_normalized LIKE ?
            GROUP BY s.id, s.name
            ORDER BY s.name COLLATE NOCASE, s.id
            LIMIT ? OFFSET ?
            """,
            (text, normalized_page_size, offset),
        ).fetchall()
        total_pages = (total + normalized_page_size - 1) // normalized_page_size if total else 0
        return SourcePage(
            items=[
                SourceSummary(
                    id=int(row["id"]),
                    name=row["name"],
                    record_count=int(row["record_count"]),
                    undownloaded_count=0,
                )
                for row in rows
            ],
            page=normalized_page,
            page_size=normalized_page_size,
            total=total,
            total_pages=total_pages,
        )

    def platform_undownloaded_counts(self, source_ids: list[int]) -> dict[int, int]:
        ids = _normalized_ids(source_ids)
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        rows = self.conn.execute(
            f"""
            SELECT rgs.source_id, COUNT(DISTINCT rg.id) AS undownloaded_count
            FROM record_group_sources rgs
            JOIN record_groups rg ON rg.id = rgs.record_group_id
            WHERE rgs.source_id IN ({placeholders})
              AND rg.is_deleted = 0
              AND {_undownloaded_exists_sql()}
            GROUP BY rgs.source_id
            """,
            tuple(ids),
        ).fetchall()
        counts = {source_id: 0 for source_id in ids}
        counts.update({int(row["source_id"]): int(row["undownloaded_count"]) for row in rows})
        return counts

    def get_platform(self, source_id: int) -> SourceSummary:
        if source_id < 1:
            raise ValidationError("Platform id must be at least 1.")
        row = self.conn.execute(
            """
            SELECT
                s.id,
                s.name,
                COUNT(DISTINCT rg.id) AS record_count,
                COUNT(DISTINCT CASE
                    WHEN EXISTS (
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
                    THEN rg.id
                END) AS undownloaded_count
            FROM sources s
            JOIN record_group_sources rgs ON rgs.source_id = s.id
            JOIN record_groups rg ON rg.id = rgs.record_group_id
            WHERE rg.is_deleted = 0
              AND s.id = ?
            GROUP BY s.id, s.name
            """,
            (source_id,),
        ).fetchone()
        if row is None:
            raise NotFoundError(f"Platform not found: {source_id}")
        return SourceSummary(
            id=int(row["id"]),
            name=row["name"],
            record_count=int(row["record_count"]),
            undownloaded_count=int(row["undownloaded_count"]),
        )

    def list_platform_records(self, source_id: int, limit: int = DEFAULT_LIMIT) -> list[RecordSummary]:
        self._require_source(source_id)
        return self._list_records(
            """
            WHERE rg.is_deleted = 0
              AND EXISTS (
                  SELECT 1
                  FROM record_group_sources rgs
                  WHERE rgs.record_group_id = rg.id
                    AND rgs.source_id = ?
              )
            """,
            (source_id,),
            limit,
        )

    def list_records(
        self,
        *,
        record_id: int | None = None,
        title: str = "",
        actor: str = "",
        source: str = "",
        date_from: str | None = None,
        date_to: str | None = None,
        downloaded: str | None = None,
        file_type: str | None = None,
        only_undownloaded: bool = False,
        page: int = 1,
        page_size: int = DEFAULT_LIMIT,
    ) -> RecordPage:
        normalized_page = normalize_page(page)
        normalized_page_size = normalize_limit(page_size)
        where_sql, params = self._build_record_filters(
            record_id=record_id,
            title=title,
            actor=actor,
            source=source,
            date_from=date_from,
            date_to=date_to,
            downloaded=downloaded,
            file_type=file_type,
            only_undownloaded=only_undownloaded,
        )
        total = self._count_records(where_sql, params)
        offset = (normalized_page - 1) * normalized_page_size
        items = self._list_records_page(where_sql, params, normalized_page_size, offset)
        total_pages = (total + normalized_page_size - 1) // normalized_page_size if total else 0
        return RecordPage(
            items=items,
            page=normalized_page,
            page_size=normalized_page_size,
            total=total,
            total_pages=total_pages,
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
        actor_id: int | None = None,
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
        if actor_id is not None:
            self._require_actor(actor_id)
            clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM record_group_actors rga
                    WHERE rga.record_group_id = rg.id
                      AND rga.actor_id = ?
                )
                """
            )
            params.append(actor_id)
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
        only_undownloaded: bool = False,
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
            if not only_undownloaded or link.status not in {"completed", "legacy_completed"}
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
            SELECT {_summary_columns_sql()},
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

    def _list_records_page(
        self,
        where_sql: str,
        params: tuple[object, ...],
        limit: int,
        offset: int,
    ) -> list[RecordSummary]:
        rows = self.conn.execute(
            f"""
            SELECT {_summary_columns_sql()},
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
            LIMIT ? OFFSET ?
            """,
            params + (limit, offset),
        ).fetchall()
        return [_summary_from_row(row) for row in rows]

    def _count_records(self, where_sql: str, params: tuple[object, ...]) -> int:
        row = self.conn.execute(
            f"""
            SELECT COUNT(*)
            FROM record_groups rg
            {where_sql}
            """,
            params,
        ).fetchone()
        return int(row[0])

    def _build_record_filters(
        self,
        *,
        record_id: int | None,
        title: str,
        actor: str,
        source: str,
        date_from: str | None,
        date_to: str | None,
        downloaded: str | None,
        file_type: str | None,
        only_undownloaded: bool,
    ) -> tuple[str, tuple[object, ...]]:
        normalized_from = normalize_date(date_from) if date_from else None
        normalized_to = normalize_date(date_to) if date_to else None
        normalized_downloaded = downloaded.casefold() if downloaded else None
        if normalized_downloaded is not None and normalized_downloaded not in {"all", "partial", "none", "unknown"}:
            raise ValidationError("Downloaded must be one of: all, partial, none, unknown.")

        normalized_file_type = None
        if file_type is not None and file_type.strip():
            stripped = file_type.strip().casefold()
            normalized_file_type = stripped if stripped.startswith(".") else f".{stripped}"

        clauses = ["rg.is_deleted = 0"]
        params: list[object] = []

        if record_id is not None:
            if record_id < 1:
                raise ValidationError("Record id must be at least 1.")
            clauses.append("rg.id = ?")
            params.append(record_id)
        if title:
            text = f"%{normalize_search_text(title)}%"
            clauses.append(
                """
                (
                    lower(rg.title) LIKE ?
                    OR lower(rg.upload_title) LIKE ?
                    OR lower(COALESCE(rg.duplicate_search_raw, '')) LIKE ?
                )
                """
            )
            params.extend([text, text, text])
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
        if normalized_from is not None:
            clauses.append("rg.delivery_date IS NOT NULL")
            clauses.append("rg.delivery_date >= ?")
            params.append(normalized_from)
        if normalized_to is not None:
            clauses.append("rg.delivery_date IS NOT NULL")
            clauses.append("rg.delivery_date <= ?")
            params.append(normalized_to)
        if normalized_file_type is not None:
            clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM download_links dl
                    WHERE dl.record_group_id = rg.id
                      AND dl.is_deleted = 0
                      AND dl.file_type = ?
                )
                """
            )
            params.append(normalized_file_type)
        if only_undownloaded:
            clauses.append(_undownloaded_exists_sql())
        if normalized_downloaded is not None:
            clauses.append(_downloaded_filter_sql(normalized_downloaded))

        return "WHERE " + " AND ".join(clauses), tuple(params)

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

    def _require_actor(self, actor_id: int) -> None:
        if actor_id < 1:
            raise ValidationError("Actor id must be at least 1.")
        row = self.conn.execute("SELECT 1 FROM actors WHERE id = ?", (actor_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Actor not found: {actor_id}")

    def _require_source(self, source_id: int) -> None:
        if source_id < 1:
            raise ValidationError("Platform id must be at least 1.")
        row = self.conn.execute("SELECT 1 FROM sources WHERE id = ?", (source_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Platform not found: {source_id}")


def normalize_limit(limit: int) -> int:
    if limit < 1:
        raise ValidationError("Limit must be at least 1.")
    return min(limit, MAX_LIMIT)


def normalize_page(page: int) -> int:
    if page < 1:
        raise ValidationError("Page must be at least 1.")
    return page


def _normalized_ids(values: list[int]) -> list[int]:
    ids = sorted({int(value) for value in values if int(value) > 0})
    if len(ids) > MAX_LIMIT:
        raise ValidationError(f"At most {MAX_LIMIT} ids are allowed.")
    return ids


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


def _summary_columns_sql() -> str:
    return """
           rg.id,
           rg.source_key,
           rg.delivery_date,
           rg.entry_date,
           rg.actor_raw,
           rg.title,
           rg.source_name,
           rg.size_bytes
           """


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


def _active_count_sql() -> str:
    return """
    (
        SELECT COUNT(*)
        FROM download_links dl
        WHERE dl.record_group_id = rg.id AND dl.is_deleted = 0
    )
    """


def _completed_count_sql() -> str:
    return """
    (
        SELECT COUNT(DISTINCT dl.id)
        FROM download_links dl
        JOIN download_items di ON di.link_id = dl.id
        WHERE dl.record_group_id = rg.id
          AND dl.is_deleted = 0
          AND di.status IN ('completed', 'legacy_completed')
    )
    """


def _undownloaded_exists_sql() -> str:
    return """
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
    """


def _downloaded_filter_sql(downloaded: str) -> str:
    active_count = _active_count_sql()
    completed_count = _completed_count_sql()
    if downloaded == "unknown":
        return f"{active_count} = 0"
    if downloaded == "none":
        return f"{active_count} > 0 AND {completed_count} = 0"
    if downloaded == "partial":
        return f"{completed_count} > 0 AND {completed_count} < {active_count}"
    return f"{active_count} > 0 AND {completed_count} = {active_count}"
