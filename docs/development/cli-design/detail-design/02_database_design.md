# Database Detailed Design

## 1. Database File And Initialization

Default database path:

```text
env/recordtree.sqlite3
```

`recordtree init` is responsible for:

1. Creating `env/`, `downloads/`, and `logs/`.
2. Creating default `env/config.toml`.
3. Connecting to SQLite.
4. Executing `recordtree/schema.sql`.
5. Printing actual paths.

Initialization must be repeatable. All `CREATE TABLE` and `CREATE INDEX` statements use `IF NOT EXISTS`.

## 2. Schema Version

Add a `schema_meta` table to record the schema version for future migrations.

```sql
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

After v1 initialization, write:

```text
schema_version = 1
```

The implementation can initially support only creating the latest schema. Stepwise migrations can be added in later versions.

## 3. Record Group Table

```sql
CREATE TABLE IF NOT EXISTS record_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_key TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL,
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
    is_deleted INTEGER NOT NULL DEFAULT 0,
    CHECK (is_deleted IN (0, 1))
);
```

Field notes:

| Field | Description |
|---|---|
| `source_key` | Metadata hash used as the upsert key for repeated imports. |
| `source_type` | `xlsx`, `json`, or `legacy_db`. |
| `actor_raw` | Raw actor string for display. |
| `delivery_date` | Record Tree delivery date, ISO date or null. |
| `title` | Title. |
| `entry_date` | Entry date, ISO date or null. |
| `upload_title` | Upload title or legacy filename. |
| `duplicate_search_raw` | Duplicate-search helper text. |
| `source_name` | Raw display name of the source platform. |
| `mega_json` | Raw MEGA JSON from Excel, retained for audit. |
| `is_deleted` | Reserved for future full-import marking of missing records. |

## 4. Actor And Source

```sql
CREATE TABLE IF NOT EXISTS actors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    name_normalized TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS record_group_actors (
    record_group_id INTEGER NOT NULL,
    actor_id INTEGER NOT NULL,
    PRIMARY KEY (record_group_id, actor_id),
    FOREIGN KEY (record_group_id) REFERENCES record_groups(id) ON DELETE CASCADE,
    FOREIGN KEY (actor_id) REFERENCES actors(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    name_normalized TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS record_group_sources (
    record_group_id INTEGER NOT NULL,
    source_id INTEGER NOT NULL,
    PRIMARY KEY (record_group_id, source_id),
    FOREIGN KEY (record_group_id) REFERENCES record_groups(id) ON DELETE CASCADE,
    FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE RESTRICT
);
```

In v1 each record group has one `actor_raw` and one `source_name`, but join tables are retained to support future multi-actor or source-alias behavior.

## 5. Download Link Table

```sql
CREATE TABLE IF NOT EXISTS download_links (
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
    FOREIGN KEY (record_group_id) REFERENCES record_groups(id) ON DELETE CASCADE,
    CHECK (is_deleted IN (0, 1))
);
```

`content_hash` input:

```text
mega_url
file_type
size_bytes
formatted_size
```

Active links use `is_deleted = 0`. Historical links are not deleted.

## 6. Import Audit Tables

```sql
CREATE TABLE IF NOT EXISTS imports (
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

CREATE TABLE IF NOT EXISTS import_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_id INTEGER NOT NULL,
    row_number INTEGER,
    source_key TEXT,
    error_type TEXT NOT NULL,
    message TEXT NOT NULL,
    raw_value TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (import_id) REFERENCES imports(id) ON DELETE CASCADE
);
```

`imports.status` values:

```text
running
completed
completed_with_errors
failed
```

## 7. Download Record Tables

```sql
CREATE TABLE IF NOT EXISTS downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_group_id INTEGER NOT NULL,
    requested_at TEXT NOT NULL,
    output_dir TEXT NOT NULL,
    selected_bytes INTEGER NOT NULL,
    free_bytes_before INTEGER,
    status TEXT NOT NULL,
    mega_exit_code INTEGER,
    message TEXT,
    FOREIGN KEY (record_group_id) REFERENCES record_groups(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS download_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    download_id INTEGER NOT NULL,
    link_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    mega_exit_code INTEGER,
    message TEXT,
    FOREIGN KEY (download_id) REFERENCES downloads(id) ON DELETE CASCADE,
    FOREIGN KEY (link_id) REFERENCES download_links(id) ON DELETE RESTRICT
);
```

Status values:

```text
planned
completed
failed
blocked
cancelled
legacy_completed
```

In v1, a link is considered downloaded if any `download_items` row for that link has status `completed` or `legacy_completed`.

## 8. Legacy Mapping Table

```sql
CREATE TABLE IF NOT EXISTS legacy_migration_map (
    legacy_record_id INTEGER PRIMARY KEY,
    legacy_author_id INTEGER NOT NULL,
    record_group_id INTEGER NOT NULL,
    link_id INTEGER NOT NULL,
    legacy_downloaded_date TEXT,
    migrated_at TEXT NOT NULL,
    FOREIGN KEY (record_group_id) REFERENCES record_groups(id) ON DELETE CASCADE,
    FOREIGN KEY (link_id) REFERENCES download_links(id) ON DELETE RESTRICT
);
```

Constraints:

- `legacy_record_id` is the idempotency key.
- If a legacy URL matches an existing active link, reuse that link.
- If `legacy_downloaded_date != '0'`, create a `legacy_completed` download record or equivalent status record for that link during migration.

## 9. Recommended Indexes

```sql
CREATE INDEX IF NOT EXISTS idx_record_groups_delivery_date
ON record_groups(delivery_date);

CREATE INDEX IF NOT EXISTS idx_record_groups_entry_date
ON record_groups(entry_date);

CREATE INDEX IF NOT EXISTS idx_record_groups_deleted
ON record_groups(is_deleted);

CREATE INDEX IF NOT EXISTS idx_record_groups_source_type
ON record_groups(source_type);

CREATE INDEX IF NOT EXISTS idx_actors_normalized
ON actors(name_normalized);

CREATE INDEX IF NOT EXISTS idx_sources_normalized
ON sources(name_normalized);

CREATE INDEX IF NOT EXISTS idx_links_group_active
ON download_links(record_group_id, is_deleted);

CREATE INDEX IF NOT EXISTS idx_links_url
ON download_links(mega_url);

CREATE UNIQUE INDEX IF NOT EXISTS idx_links_active_url
ON download_links(mega_url)
WHERE is_deleted = 0;

CREATE INDEX IF NOT EXISTS idx_links_file_type
ON download_links(file_type);

CREATE INDEX IF NOT EXISTS idx_download_items_link_status
ON download_items(link_id, status);

CREATE INDEX IF NOT EXISTS idx_legacy_map_group
ON legacy_migration_map(record_group_id);
```

## 10. Suggested Query Views

v1 can initially avoid SQL views and let `search.py` assemble queries. If implementation reveals repeated SQL, add a view:

```sql
CREATE VIEW IF NOT EXISTS active_record_groups AS
SELECT *
FROM record_groups
WHERE is_deleted = 0;
```

Do not use complex materialized summary tables in v1. Download status can be aggregated from `download_items` in real time.

## 11. Transaction Strategy

Import:

- The starting `imports` record may be created outside the transaction with status `running`.
- Data writes and error records are placed in one transaction.
- At completion, update `imports` statistics and status.
- On hard errors, roll back business writes and set `imports.status` to `failed`.

Download:

- Use short transactions when creating blocked/cancelled/completed download records.
- Create each item as `planned` before running a single `mega-get`.
- Update the item immediately after execution so long-running external processes do not hold database transactions.

## 12. Data Consistency Rules

- `record_groups.source_key` is unique.
- Active URLs are unique at any point in time.
- All search and download commands filter `record_groups.is_deleted = 0` and `download_links.is_deleted = 0` by default.
- Legacy migration must not overwrite high-quality Excel metadata.
- Historical inactive links do not participate in the default download plan.
