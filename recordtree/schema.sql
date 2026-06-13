CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

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
