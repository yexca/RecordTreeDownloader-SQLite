# Phase 6: Legacy Database Import

## Goal

Import the old SQLite database, preserve historical downloaded status, and prefer URL-based matching to Excel-imported active links so duplicate active URLs are not created.

## Source Documents

- `dev_documents/requirement_analysis/03_database_and_migration.md`
- `dev_documents/requirement_analysis/05_implementation_plan.md`
- `dev_documents/high_level_design/03_data_import_and_migration_design.md`
- `dev_documents/detail_design/03_import_detail_design.md`

## Scope

Implement:

- `.db` / `.sqlite` / `.sqlite3` import dispatch
- legacy schema validation
- reading `author` and `record`
- URL matching against new active links
- legacy-only group creation for unmatched URLs
- `legacy_migration_map` writes
- `downloaded_date` preservation as `legacy_completed`
- idempotent repeated migration

## Files To Implement

- `recordtree/importer/legacy_db.py`
- `recordtree/repositories.py`
- `recordtree/importer/service.py`
- `recordtree/app.py`
- `recordtree/cli.py`

## Required Legacy Schema

```text
author(author_id, name, added_date)
record(record_id, author_id, name, date, size, link, added_date, downloaded_date)
```

Validation:

- Use `sqlite_master` to confirm required tables exist.
- Use `PRAGMA table_info(author)` and `PRAGMA table_info(record)` to confirm required columns exist.
- Missing tables or columns are hard errors.

## Read Query

```sql
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
ORDER BY r.record_id;
```

## Migration Rules

For each legacy record:

1. Skip it if `legacy_migration_map.legacy_record_id` already exists.
2. Record `legacy_link_missing` if `mega_url` is empty.
3. If the URL matches a new active link:
   - reuse that link and its `record_group_id`
   - backfill `download_links.legacy_record_id` and `legacy_author_id`
   - insert `legacy_migration_map`
4. If the URL does not exist:
   - create `ImportRecord(source_type="legacy_db")`
   - set `actor_raw = author_name`
   - set `delivery_date = normalize_date(record_date)`
   - set `title = record_name`
   - set `upload_title = record_name`
   - set `source_name = "legacy"`
   - create one link from legacy `link` and `size`
5. If `downloaded_date != '0'`, create a special `legacy_completed` download and item.

## Download Status Preservation

Do not fake a real download attempt. Use a special imported status:

```text
output_dir = ""
selected_bytes = legacy size
free_bytes_before = null
status = legacy_completed
message = "Migrated from legacy database downloaded_date=<date>"
```

If the legacy date cannot be normalized, keep the raw value in `message` and allow `finished_at` to be null.

## Conflict Handling

Record row-level errors and continue by default:

- `legacy_url_ambiguous`: one legacy URL matches multiple active links
- `legacy_record_conflict`: one legacy record id maps to a different link
- `legacy_link_missing`: legacy record has no URL

## Test Guidance

Use a small fixture database with:

- two authors
- four records
- one URL matching an existing Excel-imported link
- one unmatched legacy-only URL
- one `downloaded_date = '0'`
- one `downloaded_date = '<completed-date>'`

Assertions:

- matched URLs reuse existing links
- unmatched URLs create legacy-only groups
- `legacy_migration_map` rows are created
- `legacy_completed` status is created
- running migration twice does not duplicate rows

## Acceptance Checks

- `files/legacy_record.db` can be imported.
- The importer can read all expected authors and records.
- All expected downloaded statuses are preserved.
- No duplicate active URLs are created.
- Re-running the import is idempotent.

## Done When

Legacy downloaded history is preserved in the new database and search/download status commands treat migrated completed links correctly.
