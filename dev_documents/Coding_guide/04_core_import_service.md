# Phase 4: Core Import Service

## Goal

Implement the shared import foundation used by Excel, legacy SQLite, and legacy JSON imports: normalization, source identity, link-set change detection, record group upsert, actor/source mapping, import audit rows, row-level errors, and historical link preservation.

## Source Documents

- `dev_documents/requirement_analysis/03_database_and_migration.md`
- `dev_documents/high_level_design/03_data_import_and_migration_design.md`
- `dev_documents/detail_design/01_module_design.md`
- `dev_documents/detail_design/03_import_detail_design.md`

## Scope

This phase implements source-independent behavior. Source-specific parsing belongs to later phases.

Core behavior:

- text cleanup and search normalization
- date normalization
- file type normalization
- size parsing
- `source_key` generation
- `link_set_hash` generation
- `record_groups` upsert
- actor/source mapping refresh
- active link replacement with inactive historical preservation
- import stats and row-level error recording

## Files To Implement

- `recordtree/models.py`
- `recordtree/normalizers.py`
- `recordtree/sizes.py`
- `recordtree/repositories.py`
- `recordtree/importer/service.py`
- `recordtree/exceptions.py`

## Data Structures

Implement the core dataclasses in `models.py`:

```python
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
```

## Normalization Rules

`normalizers.py` should implement:

- Empty strings, whitespace-only strings, and `None` normalize to `None`.
- Search text uses trim plus `casefold()`.
- Dates return `YYYY-MM-DD`; blank dates return `None`; invalid dates raise `ValidationError`.
- File types normalize to lowercase with a leading dot, for example `mp4 -> .mp4`.
- Hash input should use `json.dumps(..., ensure_ascii=False, sort_keys=True)` and `sha256`.

`source_key` input fields:

```text
actor_raw
delivery_date
title
entry_date
upload_title
source_name
```

`link_set_hash` input fields:

```text
link_order
mega_url
file_type
size_bytes
formatted_size
```

## Upsert Algorithm

`ImportService.upsert_record(import_id, record)` should:

1. Build `source_key`.
2. Find an existing group by `source_key`.
3. If no group exists, insert the group, actor/source mappings, and all links.
4. If a group exists, update metadata, `last_seen_at`, and mappings.
5. Compare the current active link-set hash with the new link-set hash.
6. If hashes match, refresh active link `last_seen_at` and count skipped links.
7. If hashes differ, mark old active links inactive and insert the new active links.
8. If a URL is already active under a different group, record a conflict error instead of silently merging it.

## Repository Interfaces

`repositories.py` may be one file in v1, grouped by classes:

- `ImportRepository`
- `RecordGroupRepository`
- `LinkRepository`
- `ActorRepository`
- `SourceRepository`
- `DownloadRepository`
- `LegacyMigrationRepository`

Minimum useful methods:

```python
create_import(...)
finish_import(...)
fail_import(...)
add_import_error(...)
get_group_by_source_key(...)
insert_group(...)
update_group_seen(...)
list_active_links(...)
touch_active_links(...)
mark_active_links_deleted(...)
insert_link(...)
find_active_link_by_url(...)
```

## Test Guidance

Use temporary SQLite databases and hand-built `ImportRecord` objects:

- first import inserts one group and its links
- importing the same record twice does not add active links
- changed link sets make old links inactive and new links active
- active URL conflicts are recorded as errors
- repeated actor/source mapping calls do not duplicate join rows

## Acceptance Checks

- The core service does not depend on Excel, JSON, or legacy DB files.
- Re-importing the same sample creates no duplicate active links.
- Link changes preserve historical inactive links.
- `imports` and `import_errors` record status and row-level failures.
- Unit tests cover normalizers, sizes, and hash behavior.

## Done When

Any source importer can convert source rows into `ImportRecord` objects and reuse one consistent import/write path.
