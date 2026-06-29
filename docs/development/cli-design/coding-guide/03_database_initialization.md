# Phase 3: Database Initialization

## Goal

Implement `recordtree init` so a fresh working directory gets a default config file, SQLite database, downloads directory, and logs directory. Initialization must be idempotent.

## Source Documents

- `dev_documents/requirement_analysis/03_database_and_migration.md`
- `dev_documents/requirement_analysis/05_implementation_plan.md`
- `dev_documents/detail_design/02_database_design.md`
- `dev_documents/detail_design/04_cli_search_download_detail.md`

## Scope

Create:

- `env/config.toml`
- `env/recordtree.sqlite3`
- `downloads/`
- `logs/`
- SQLite schema from `recordtree/schema.sql`

## Files To Implement

- `recordtree/config.py`
- `recordtree/db.py`
- `recordtree/schema.sql`
- `recordtree/app.py`
- `recordtree/cli.py`

## Config Work

`config.py` should provide:

```python
def default_config() -> dict: ...
def ensure_config(path: Path) -> Path: ...
def load_config(path: Path | None = None) -> AppConfig: ...
def resolve_path(base_dir: Path, configured_path: str) -> Path: ...
```

Suggested default keys:

```text
database_path = "env/recordtree.sqlite3"
downloads_dir = "downloads"
logs_dir = "logs"
safety_margin_percent = 5
safety_margin_min_mb = 512
include_par2_by_default = false
mega_get = "mega-get"
mega_whoami = "mega-whoami"
prefer_xlsx_metadata = true
```

## Database Work

`db.py` should provide:

```python
def connect(database_path: Path) -> sqlite3.Connection: ...
def initialize_schema(conn: sqlite3.Connection) -> None: ...
@contextmanager
def transaction(conn: sqlite3.Connection): ...
```

Connection setup:

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
```

`schema.sql` must include the v1 schema:

- `schema_meta`
- `record_groups`
- `actors`
- `record_group_actors`
- `sources`
- `record_group_sources`
- `download_links`
- `imports`
- `import_errors`
- `downloads`
- `download_items`
- `legacy_migration_map`
- recommended indexes from the detailed design

All `CREATE TABLE` and `CREATE INDEX` statements should use `IF NOT EXISTS`.

## CLI Behavior

`recordtree init` should:

1. Create `env/`.
2. Create `env/config.toml` if missing; never overwrite an existing config.
3. Load config and resolve configured paths.
4. Create the database parent directory, downloads directory, and logs directory.
5. Open SQLite and apply `schema.sql`.
6. Set `schema_meta.schema_version = 1`.
7. Print a concise Rich summary of the actual paths.

## Test Guidance

- Run `init` in a temporary directory.
- Run `init` twice and verify no error occurs.
- Verify the config file is not overwritten on the second run.
- Verify all expected tables and indexes exist.
- Verify `PRAGMA foreign_keys` is enabled.

## Acceptance Checks

- `recordtree init` creates all required folders and files.
- `recordtree init` is safe to run repeatedly.
- `env/recordtree.sqlite3` is connectable.
- `schema_version` is `1`.
- User-facing failures do not print Python tracebacks.

## Done When

A new project checkout can be initialized into a usable local environment with one command.
