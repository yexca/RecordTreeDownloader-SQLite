from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class LinkItem:
    link_order: int
    mega_url: str
    file_type: str | None
    size_bytes: int
    formatted_size: str | None


@dataclass(frozen=True)
class ImportRecord:
    source_type: str
    actor_raw: str
    delivery_date: str | None
    title: str
    entry_date: str | None
    note: str | None
    upload_title: str
    duplicate_search_raw: str | None
    source_name: str
    size_raw: str | None
    size_bytes: int | None
    mega_file_name: str | None
    mega_total_bytes: int | None
    mega_formatted_size: str | None
    mega_json: str | None
    source_row_number: int | None
    links: list[LinkItem]


@dataclass
class ImportStats:
    total_rows: int = 0
    inserted_groups: int = 0
    updated_groups: int = 0
    skipped_groups: int = 0
    link_sets_changed: int = 0
    inserted_links: int = 0
    skipped_links: int = 0
    error_count: int = 0


@dataclass(frozen=True)
class ImportResult:
    import_id: int
    source_type: str
    source_path: Path
    status: str
    stats: ImportStats
    error_csv_path: Path | None = None
    extra_columns: tuple[str, ...] = ()


@dataclass(frozen=True)
class InitResult:
    config_path: Path
    database_path: Path
    downloads_dir: Path
    logs_dir: Path
    schema_version: str


@dataclass(frozen=True)
class DownloadLink:
    id: int
    mega_url: str
    file_type: str | None
    size_bytes: int
    formatted_size: str | None


@dataclass(frozen=True)
class DownloadPlan:
    record_group_id: int
    output_dir: Path
    selected_links: list[DownloadLink] = field(default_factory=list)
    selected_bytes: int = 0
    margin_bytes: int = 0
    required_bytes: int = 0
    free_bytes_before: int | None = None
    include_par2: bool = False
    type_filter: set[str] | None = None
