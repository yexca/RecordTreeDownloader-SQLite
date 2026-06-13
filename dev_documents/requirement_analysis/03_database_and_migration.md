# Database And Migration Requirements

## 1. Design Goals

The database should support:

- Repeatable imports from the latest Excel workbook.
- Compatibility imports from old JSON exports.
- One-time or repeatable migration from legacy SQLite.
- Search by actor, source, title, date, file type, and download status.
- Historical preservation of old link rows when imports change.
- Per-link and per-record-group download tracking.
- Fast disk-size calculation before MEGAcmd download.

## 2. Recommended Tables

### `record_groups`

Stores one row per workbook row or imported legacy record group.

```sql
CREATE TABLE record_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_key TEXT NOT NULL UNIQUE,
    actor_raw TEXT NOT NULL,
    delivery_date TEXT,
    title TEXT NOT NULL,
    entry_date TEXT,
    note TEXT,
    upload_title TEXT NOT NULL,
    duplicate_search_raw TEXT,
    source_name TEXT NOT NULL,
    size_raw TEXT,
    size_bytes INTEGER,
    mega_file_name TEXT,
    mega_total_bytes INTEGER,
    mega_formatted_size TEXT,
    mega_json TEXT,
    source_row_number INTEGER,
    first_imported_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0
);
```

Notes:

- `source_key` is a deterministic hash from normalized source metadata.
- `mega_json` is optional but useful for audit and future parser improvements.
- `is_deleted` is reserved for records missing from a later full import.

### `actors`

```sql
CREATE TABLE actors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    name_normalized TEXT NOT NULL
);
```

### `record_group_actors`

```sql
CREATE TABLE record_group_actors (
    record_group_id INTEGER NOT NULL,
    actor_id INTEGER NOT NULL,
    PRIMARY KEY (record_group_id, actor_id),
    FOREIGN KEY (record_group_id) REFERENCES record_groups(id),
    FOREIGN KEY (actor_id) REFERENCES actors(id)
);
```

### `sources`

```sql
CREATE TABLE sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    name_normalized TEXT NOT NULL
);
```

### `record_group_sources`

This join table is optional for v1 because each workbook row has one source. It is useful if future rows contain multiple platforms or aliases.

```sql
CREATE TABLE record_group_sources (
    record_group_id INTEGER NOT NULL,
    source_id INTEGER NOT NULL,
    PRIMARY KEY (record_group_id, source_id),
    FOREIGN KEY (record_group_id) REFERENCES record_groups(id),
    FOREIGN KEY (source_id) REFERENCES sources(id)
);
```

### `download_links`

Stores current and historical MEGA file links.

```sql
CREATE TABLE download_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_group_id INTEGER NOT NULL,
    link_order INTEGER NOT NULL,
    mega_url TEXT NOT NULL,
    file_type TEXT,
    size_bytes INTEGER NOT NULL,
    formatted_size TEXT,
    content_hash TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    deleted_at TEXT,
    legacy_record_id INTEGER,
    legacy_author_id INTEGER,
    FOREIGN KEY (record_group_id) REFERENCES record_groups(id)
);
```

Recommended indexes:

```sql
CREATE INDEX idx_links_group_active ON download_links(record_group_id, is_deleted);
CREATE INDEX idx_links_url ON download_links(mega_url);
CREATE UNIQUE INDEX idx_links_active_url
ON download_links(mega_url)
WHERE is_deleted = 0;
CREATE INDEX idx_links_file_type ON download_links(file_type);
```

### `imports`

Tracks xlsx, json, and legacy-db import jobs.

```sql
CREATE TABLE imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,
    source_path TEXT NOT NULL,
    source_file_name TEXT NOT NULL,
    source_file_size INTEGER,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    total_rows INTEGER DEFAULT 0,
    inserted_groups INTEGER DEFAULT 0,
    updated_groups INTEGER DEFAULT 0,
    skipped_groups INTEGER DEFAULT 0,
    link_sets_changed INTEGER DEFAULT 0,
    inserted_links INTEGER DEFAULT 0,
    skipped_links INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    notes TEXT
);
```

### `import_errors`

```sql
CREATE TABLE import_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_id INTEGER NOT NULL,
    row_number INTEGER,
    source_key TEXT,
    error_type TEXT NOT NULL,
    message TEXT NOT NULL,
    raw_value TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (import_id) REFERENCES imports(id)
);
```

### `downloads`

Tracks download attempts at the group level.

```sql
CREATE TABLE downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_group_id INTEGER NOT NULL,
    requested_at TEXT NOT NULL,
    output_dir TEXT NOT NULL,
    selected_bytes INTEGER NOT NULL,
    free_bytes_before INTEGER,
    status TEXT NOT NULL,
    mega_exit_code INTEGER,
    message TEXT,
    FOREIGN KEY (record_group_id) REFERENCES record_groups(id)
);
```

### `download_items`

Tracks download status per selected link.

```sql
CREATE TABLE download_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    download_id INTEGER NOT NULL,
    link_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    mega_exit_code INTEGER,
    message TEXT,
    FOREIGN KEY (download_id) REFERENCES downloads(id),
    FOREIGN KEY (link_id) REFERENCES download_links(id)
);
```

### `legacy_migration_map`

Keeps traceability from old SQLite rows to new rows.

```sql
CREATE TABLE legacy_migration_map (
    legacy_record_id INTEGER PRIMARY KEY,
    legacy_author_id INTEGER NOT NULL,
    record_group_id INTEGER NOT NULL,
    link_id INTEGER NOT NULL,
    legacy_downloaded_date TEXT,
    migrated_at TEXT NOT NULL,
    FOREIGN KEY (record_group_id) REFERENCES record_groups(id),
    FOREIGN KEY (link_id) REFERENCES download_links(id)
);
```

## 3. Source Key Policy

Recommended xlsx source key input:

```text
actor_raw
delivery_date
title
entry_date
upload_title
source_name
```

Recommended algorithm:

```text
source_key = sha256(json.dumps(normalized_fields, ensure_ascii=False, sort_keys=True))
```

Rationale:

- `上传标题` is not unique.
- `MEGA` can change and should not define the record identity.
- The source key should remain stable when links are refreshed.

## 4. Link Change Detection

For each imported record group, parse active link items into normalized tuples:

```text
(link_order, mega_url, file_type, size_bytes, formatted_size)
```

Create a stable link-set hash:

```text
sha256(json.dumps(sorted_links, ensure_ascii=False, sort_keys=True))
```

Import behavior:

- If a group has no active links, insert imported links.
- If the active link-set hash is unchanged, update `last_seen_at`.
- If changed, mark old active links as `is_deleted = 1`, set `deleted_at`, then insert new active links.
- If an individual URL already exists from legacy migration, attach or reuse carefully rather than creating duplicate active URL rows.

## 5. Legacy SQLite Migration

Legacy source schema:

```text
author(author_id, name, added_date)
record(record_id, author_id, name, date, size, link, added_date, downloaded_date)
```

Migration mapping:

| Legacy field | New field |
|---|---|
| `author.name` | `record_groups.actor_raw`, `actors.name` |
| `record.name` | `record_groups.upload_title`, `record_groups.mega_file_name`, fallback title parsing source |
| `record.date` | `record_groups.delivery_date` |
| `record.size` | `download_links.size_bytes` |
| `record.link` | `download_links.mega_url` |
| `record.added_date` | `record_groups.first_imported_at`, `download_links.first_seen_at` when no better value exists |
| `record.downloaded_date` | `legacy_migration_map.legacy_downloaded_date`; also seed download status if not `0` |

Migration requirements:

- Must be idempotent by `legacy_record_id` or `record.link`.
- Must preserve all legacy record rows.
- Must preserve all downloaded statuses.
- Must not create orphan groups.
- Must report conflicts when the same link maps to a different new group.

Recommended behavior when xlsx and legacy-db data overlap:

1. Prefer xlsx metadata for actor/title/source/date when a matching MEGA URL is found.
2. Preserve legacy downloaded status on the matched link.
3. Keep legacy ids in mapping fields for traceability.
4. Create legacy-only record groups for links not found in xlsx.

## 6. JSON Import

JSON import should parse the old shape:

```text
author -> records[] -> property[]
```

Requirements:

- Use the same normalization and link insertion pipeline as xlsx import.
- Treat JSON metadata as lower priority than xlsx when links overlap.
- Continue row-level import when one author or record has malformed data.
- Store import errors in `import_errors`.

## 7. Download State Model

Recommended model:

- Link-level status is authoritative for "has this file/link been downloaded".
- Group-level status is a summary from the latest download attempt.
- Legacy `downloaded_date != '0'` should seed link-level completed history.

Useful download statuses:

```text
planned
completed
failed
blocked
cancelled
legacy_completed
```

## 8. Transaction Policy

Recommended import transaction model:

- Use one transaction per import command where practical.
- Always create an `imports` row at start.
- On hard failure, mark import as `failed`.
- On row-level errors, continue import and mark final status as `completed_with_errors`.
- Export import errors to CSV logs when error count is greater than zero.
