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
class ImportProgress:
    source_type: str
    source_path: Path
    completed_rows: int
    total_rows: int | None = None
    phase: str = "Importing"


@dataclass(frozen=True)
class ImportResult:
    import_id: int
    source_type: str
    source_path: Path
    status: str
    stats: ImportStats
    error_csv_path: Path | None = None
    extra_columns: tuple[str, ...] = ()
    notes: str | None = None


@dataclass(frozen=True)
class InitResult:
    config_path: Path
    database_path: Path
    downloads_dir: Path
    logs_dir: Path
    schema_version: str


@dataclass(frozen=True)
class RecordSummary:
    id: int
    source_key: str
    delivery_date: str | None
    entry_date: str | None
    actor: str | None
    title: str
    source: str | None
    size_bytes: int | None
    active_links: int
    completed_links: int
    downloaded: str


@dataclass(frozen=True)
class LinkSummary:
    id: int
    link_order: int
    mega_url: str
    file_type: str | None
    size_bytes: int
    formatted_size: str | None
    status: str


@dataclass(frozen=True)
class RecordDetail:
    id: int
    source_key: str
    actor: str
    delivery_date: str | None
    entry_date: str | None
    title: str
    source: str
    upload_title: str
    note: str | None
    size_bytes: int | None
    size_raw: str | None
    active_links: int
    completed_links: int
    downloaded: str
    links: list[LinkSummary]
    inactive_link_count: int


@dataclass(frozen=True)
class ImportSummary:
    id: int
    source_type: str
    source_file_name: str
    started_at: str
    status: str
    total_rows: int
    error_count: int


@dataclass(frozen=True)
class DownloadSummary:
    id: int
    record_group_id: int
    requested_at: str
    status: str
    selected_bytes: int
    message: str | None


@dataclass(frozen=True)
class StatsResult:
    total_record_groups: int
    active_link_count: int
    inactive_link_count: int
    actor_count: int
    source_count: int
    downloaded_all: int
    downloaded_partial: int
    downloaded_none: int
    downloaded_unknown: int
    recent_imports: list[ImportSummary]
    recent_downloads: list[DownloadSummary]


@dataclass(frozen=True)
class DownloadLink:
    id: int
    link_order: int
    mega_url: str
    file_type: str | None
    size_bytes: int
    formatted_size: str | None


@dataclass(frozen=True)
class DownloadPlan:
    record_group_id: int
    output_dir: Path
    actor: str = ""
    title: str = ""
    selected_links: list[DownloadLink] = field(default_factory=list)
    selected_bytes: int = 0
    margin_bytes: int = 0
    required_bytes: int = 0
    free_bytes_before: int | None = None
    include_par2: bool = False
    type_filter: set[str] | None = None


@dataclass(frozen=True)
class MegaCommandResult:
    exit_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class MegaLoginStatus:
    logged_in: bool
    exit_code: int
    message: str


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: str
    message: str


@dataclass(frozen=True)
class DoctorResult:
    checks: list[DoctorCheck]

    @property
    def ok(self) -> bool:
        return all(check.status in {"pass", "warn"} for check in self.checks)


@dataclass(frozen=True)
class DownloadExecutionResult:
    download_id: int
    record_group_id: int
    status: str
    completed: int
    failed: int
    output_dir: Path
    message: str | None = None


@dataclass(frozen=True)
class ActorDownloadResult:
    actor_id: int
    selected_count: int
    results: list[DownloadExecutionResult]
    message: str | None = None
