# Import And Migration Detailed Design

## 1. Unified Import Entry Point

User command:

```text
recordtree import <path>
```

Dispatch rules:

| Extension | source_type | Importer |
|---|---|---|
| `.xlsx` | `xlsx` | `ExcelImporter` |
| `.xlsm` | `xlsx` | `ExcelImporter` |
| `.json` | `json` | `JsonImporter` |
| `.db` | `legacy_db` | `LegacyDbImporter` |
| `.sqlite` | `legacy_db` | `LegacyDbImporter` |
| `.sqlite3` | `legacy_db` | `LegacyDbImporter` |

Unknown extensions fail immediately and do not create import records.

## 2. Import Execution Framework

Pseudocode:

```python
def import_file(path: Path) -> ImportResult:
    source_type = detect_source_type(path)
    importer = create_importer(source_type)
    import_id = repo.create_import(source_type, path, status="running")
    stats = ImportStats()

    try:
        with transaction(conn):
            for record in importer.iter_records(path):
                stats.total_rows += 1
                try:
                    result = service.upsert_record(import_id, record)
                    stats.apply(result)
                except ImportRowError as exc:
                    service.record_error(import_id, exc)
                    stats.error_count += 1
            status = "completed_with_errors" if stats.error_count else "completed"
            repo.finish_import(import_id, stats, status)
    except Exception as exc:
        repo.fail_import(import_id, exc)
        raise
```

Notes:

- `iter_records` should stream standardized `ImportRecord` objects where possible.
- Row-level errors do not stop the whole import.
- Missing headers, unreadable files, and mismatched legacy schemas are hard errors.

## 3. Excel Header Mapping

Required columns:

| Source Header | Internal Field |
|---|---|
| `声优` | `actor_raw` |
| `配信日期` | `delivery_date` |
| `标题` | `title` |
| `录入日期` | `entry_date` |
| `备注` | `note` |
| `上传标题` | `upload_title` |
| `重复检索` | `duplicate_search_raw` |
| `来源` | `source_name` |
| `MEGA` | `mega_json` |
| `容量` | `size_raw` |

These headers come from the currently observed workbook. The implementation should match the actual header strings in the file. If a future source uses mojibake or alternate names, add them to a header-alias table while keeping the readable Chinese names above as the canonical contract.

Header validation:

- Missing required column: hard error.
- Extra column: allowed, but mention it in the import summary.
- Duplicate header: hard error.

## 4. Excel Row Parsing

Per-row steps:

1. Read actor, title, upload title, source, MEGA, and size.
2. If a required field is empty, raise a row-level error.
3. Normalize `delivery_date` and `entry_date`; blanks are allowed.
4. Parse `size_raw` with `parse_size_text`; failures return `None` and do not block import.
5. Parse `MEGA` with `parse_mega_json`.
6. Build `ImportRecord(source_type="xlsx")`.

Workbook opening:

```python
openpyxl.load_workbook(path, read_only=True, data_only=True)
```

By default, read only the active sheet or first sheet. If future workbooks contain multiple sheets, v1 may either fail clearly or import the first sheet with a warning.

## 5. MEGA JSON Parsing

Input example:

```json
{
  "FileNames": "...",
  "total": 937552133,
  "FormattedSize": "894.12 MB",
  "property": [
    {
      "Link": "https://mega.nz/file/...",
      "Size": 875464405,
      "FormattedSize": "834.91 MB",
      "Type": ".mp4"
    }
  ]
}
```

Parsing rules:

- Root is not an object: row-level error `mega_json_invalid_root`.
- JSON parse failure: row-level error `mega_json_parse_error`.
- `property` is missing or not a list: row-level error `mega_property_invalid`.
- `property` is empty: row-level error `mega_property_empty`.
- Link item is missing `Link`: row-level error `mega_link_missing`.
- Link item `Size` cannot be converted to int: row-level error `mega_size_invalid`.
- If `Type` is empty, set `file_type = None`.

To avoid incomplete download plans, any structural error in any link item should make the whole row fail and prevent insertion of that record group.

## 6. Source Key Generation

Input fields:

```text
actor_raw
delivery_date
title
entry_date
upload_title
source_name
```

Normalization:

- Strings use `clean_text`.
- Search-related fields additionally use `casefold()`.
- Dates use ISO strings or null.

Pseudocode:

```python
payload = {
    "actor_raw": normalize_search_text(record.actor_raw),
    "delivery_date": record.delivery_date,
    "title": normalize_search_text(record.title),
    "entry_date": record.entry_date,
    "upload_title": normalize_search_text(record.upload_title),
    "source_name": normalize_search_text(record.source_name),
}
source_key = sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
```

## 7. Link Set Hash

Each link item is normalized as:

```text
link_order
mega_url
file_type
size_bytes
formatted_size
```

Keep `link_order` because order within a group is useful for display and troubleshooting. Identical hashes mean the active link set has not changed.

## 8. Detailed Upsert Algorithm

Pseudocode:

```python
def upsert_record(record):
    now = utc_now()
    source_key = build_source_key(record)
    group = group_repo.get_by_source_key(source_key)

    if group is None:
        group_id = group_repo.insert(record, source_key, now)
        actor_repo.ensure_mapping(group_id, record.actor_raw)
        source_repo.ensure_mapping(group_id, record.source_name)
        inserted = insert_all_links(group_id, record.links, now)
        return UpsertResult(inserted_groups=1, inserted_links=inserted)

    group_repo.update_seen_and_metadata(group["id"], record, now)
    actor_repo.ensure_mapping(group["id"], record.actor_raw)
    source_repo.ensure_mapping(group["id"], record.source_name)

    old_hash = build_link_set_hash(link_repo.list_active_links(group["id"]))
    new_hash = build_link_set_hash(record.links)

    if old_hash == new_hash:
        link_repo.touch_active_links(group["id"], now)
        return UpsertResult(updated_groups=1, skipped_links=len(record.links))

    link_repo.mark_active_deleted(group["id"], now)
    inserted = insert_all_links(group["id"], record.links, now)
    return UpsertResult(updated_groups=1, link_sets_changed=1, inserted_links=inserted)
```

`insert_all_links` must handle the active URL uniqueness constraint:

- If the URL already exists as an active link for the same group, refresh `last_seen_at`.
- If the URL already exists as an active link for another group, record a conflict error and do not silently move it.
- If the URL exists as an inactive historical link, insert a new active link and keep the historical row.

## 9. Actor And Source Mapping

`ensure_mapping` steps:

1. Clean the raw name with `clean_text`.
2. Build `name_normalized = normalize_search_text(name)`.
3. Find or insert by raw `name`.
4. Insert into the join table and ignore conflicts.

v1 does not split multi-actor strings. If future source data contains separators, add parsing rules later.

## 10. Legacy SQLite Schema Validation

Required tables and fields:

```text
author(author_id, name, added_date)
record(record_id, author_id, name, date, size, link, added_date, downloaded_date)
```

Validation method:

- Query `sqlite_master` to confirm tables exist.
- Use `PRAGMA table_info(author)` and `PRAGMA table_info(record)` to confirm fields exist.
- Missing fields are hard errors.

## 11. Legacy SQLite Migration

Read SQL:

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

Processing rules:

1. If `legacy_migration_map` already contains this `record_id`, skip it.
2. If `mega_url` matches an active link in the new database:
   - Use the matched link's `record_group_id`.
   - Fill `download_links.legacy_record_id` and `legacy_author_id`.
   - Write `legacy_migration_map`.
3. If the URL does not exist:
   - Create a legacy-only `ImportRecord`.
   - `actor_raw = author_name`.
   - `delivery_date = normalize_date(record_date)`.
   - `title = record_name`.
   - `upload_title = record_name`.
   - `source_name = "legacy"`.
   - The link uses legacy `link` and `size`.
4. If `downloaded_date != '0'`:
   - Create one `downloads` row with status `legacy_completed`.
   - Create one `download_items` row with status `legacy_completed`.

Legacy-only source key input still uses the unified fields, but `source_type = "legacy_db"`.

## 12. Legacy Download Status Import

To avoid pretending that a real new download attempt occurred, use a special download record:

```text
output_dir = ""
selected_bytes = legacy size
free_bytes_before = null
status = legacy_completed
message = "Migrated from legacy database downloaded_date=<date>"
```

Corresponding item:

```text
status = legacy_completed
started_at = null
finished_at = legacy_downloaded_date
mega_exit_code = null
```

If the date is not ISO formatted, keep the raw value in `message`; `finished_at` may be null.

## 13. Legacy Conflict Handling

Conflict scenarios:

- The same legacy URL matches multiple active links: record `legacy_url_ambiguous`.
- The same legacy record id is already mapped to a different link: record `legacy_record_conflict`.
- A legacy record is missing URL: record `legacy_link_missing`.

Conflicts do not stop the whole migration by default.

## 14. JSON Import

Supported structure:

```text
root list
  author object
    author
    records list
      FileNames
      total
      FormattedSize
      property list
```

Processing rules:

- Root is not a list: hard error.
- Single author missing `records`: row-level error.
- Single record missing `property`: row-level error.
- `source_name = "json"` unless a reliable source field is later found in JSON.
- `title` and `upload_title` default to `FileNames`.
- `delivery_date` and `entry_date` are null when there is no reliable source.
- If a JSON link matches an existing Excel active link, do not overwrite the Excel record-group metadata; only supplement import audit information.

## 15. Error CSV Export

When `error_count > 0`, write the following under `logs` after import completes:

```text
logs/import_<import_id>_errors.csv
```

Columns:

```text
import_id,row_number,source_key,error_type,message,raw_value,created_at
```

The CSV is a portable copy of database error records. The database remains the authoritative source.
