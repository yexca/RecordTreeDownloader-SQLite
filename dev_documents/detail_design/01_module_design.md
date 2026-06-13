# Module Detailed Design

## 1. Package Structure

Recommended implementation structure:

```text
recordtree/
  __init__.py
  __main__.py
  app.py
  cli.py
  config.py
  db.py
  exceptions.py
  importer/
    __init__.py
    excel.py
    json_importer.py
    legacy_db.py
    parsers.py
    service.py
  mega.py
  models.py
  normalizers.py
  repositories.py
  schema.sql
  search.py
  sizes.py
tests/
```

During implementation, move old scripts to `legacy/`. The new package should not import from `legacy/`.

## 2. Layered Dependencies

Dependency direction:

```text
cli -> app -> repositories / importer / search / mega / domain helpers
```

Constraints:

- `cli.py` only handles command arguments, user output, and exit codes; it does not access SQLite directly.
- `app.py` orchestrates use cases and centralizes configuration paths, transaction boundaries, and exception conversion.
- `repositories.py` encapsulates SQL; it does not parse Excel/JSON and does not call MEGAcmd.
- `importer/*` produces standardized import objects and calls `ImportService`.
- `normalizers.py`, `sizes.py`, and `importer/parsers.py` should remain mostly pure functions.
- `mega.py` only handles external commands and does not write the database.

## 3. Core Data Structures

Use `dataclasses` for internal structures to support testing and type hints.

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

Download-related structure:

```python
@dataclass(frozen=True)
class DownloadPlan:
    record_group_id: int
    output_dir: Path
    selected_links: list[DownloadLink]
    selected_bytes: int
    margin_bytes: int
    required_bytes: int
    free_bytes_before: int | None
    include_par2: bool
    type_filter: set[str] | None
```

## 4. `config.py`

Responsibilities:

- Define default paths and default download settings.
- Create `env/config.toml`.
- Read and validate configuration.
- Resolve relative paths to absolute paths under the project working directory.

Main interfaces:

```python
def default_config() -> dict: ...
def ensure_config(path: Path) -> Path: ...
def load_config(path: Path | None = None) -> AppConfig: ...
def resolve_path(base_dir: Path, configured_path: str) -> Path: ...
```

`AppConfig` fields:

- `database_path`
- `downloads_dir`
- `logs_dir`
- `safety_margin_percent`
- `safety_margin_min_mb`
- `include_par2_by_default`
- `mega_get`
- `mega_whoami`
- `prefer_xlsx_metadata`

Configuration errors should raise `ConfigError`, which `app.py` or `cli.py` converts to exit code 2.

## 5. `db.py`

Responsibilities:

- Create SQLite connections.
- Enable `PRAGMA foreign_keys = ON`.
- Initialize schema.
- Provide a transaction context.

Main interfaces:

```python
def connect(database_path: Path) -> sqlite3.Connection: ...
def initialize_schema(conn: sqlite3.Connection) -> None: ...
@contextmanager
def transaction(conn: sqlite3.Connection): ...
```

Connection settings:

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
```

Use `sqlite3.Row` for `row_factory` so repository results are mapping-friendly.

## 6. `normalizers.py`

Responsibilities:

- Trim text and normalize empty values.
- Normalize actor/source search text.
- Normalize dates.
- Normalize file types.
- Normalize inputs for source keys and link-set hashes.

Main interfaces:

```python
def clean_text(value: object) -> str | None: ...
def normalize_search_text(value: str) -> str: ...
def normalize_date(value: object) -> str | None: ...
def normalize_file_type(value: object) -> str | None: ...
def build_source_key(record: ImportRecord) -> str: ...
def build_link_set_hash(links: Iterable[LinkItem]) -> str: ...
```

Rules:

- Empty strings, `None`, and `NaN` become `None`.
- Search normalization uses `casefold()` and trims surrounding whitespace.
- File types are lowercase; user input `mp4` becomes `.mp4`.
- Dates are emitted as `YYYY-MM-DD`; unparseable dates raise `ValidationError`.
- Hashes use `json.dumps(..., ensure_ascii=False, sort_keys=True)` followed by `sha256`.

## 7. `sizes.py`

Responsibilities:

- Parse human-readable sizes.
- Calculate download safety margins.
- Format byte counts.

Main interfaces:

```python
def parse_size_text(value: str | None) -> int | None: ...
def calculate_margin(selected_bytes: int, percent: int, min_mb: int) -> int: ...
def calculate_required_bytes(selected_bytes: int, percent: int, min_mb: int) -> int: ...
def format_bytes(value: int | None) -> str: ...
```

Supported units:

```text
B, KB, MB, GB, TB
```

Units are interpreted with a 1024 base. Unparseable displayed size text returns `None`, but a link item's `Size` field must be treated as a row-level error if missing or not integer-compatible.

## 8. `repositories.py`

Responsibilities:

- Encapsulate all SQL.
- Prevent business layers from concatenating SQL.
- Return necessary domain data or `sqlite3.Row`.

Multiple classes are recommended, but v1 can keep them in one file:

```python
class ImportRepository: ...
class RecordGroupRepository: ...
class LinkRepository: ...
class ActorRepository: ...
class SourceRepository: ...
class DownloadRepository: ...
class LegacyMigrationRepository: ...
```

Key interfaces:

```python
def create_import(...)-> int
def finish_import(import_id: int, stats: ImportStats, status: str) -> None
def add_import_error(import_id: int, row_number: int | None, error_type: str, message: str, raw_value: str | None) -> None

def get_group_by_source_key(source_key: str) -> Row | None
def insert_group(record: ImportRecord, source_key: str, now: str) -> int
def update_group_seen(group_id: int, record: ImportRecord, now: str) -> None

def list_active_links(group_id: int) -> list[Row]
def mark_active_links_deleted(group_id: int, now: str) -> None
def insert_link(group_id: int, item: LinkItem, content_hash: str, now: str) -> int
def find_active_link_by_url(url: str) -> Row | None
```

## 9. `importer/parsers.py`

Responsibilities:

- Parse the MEGA JSON root.
- Validate link items.
- Convert parse errors to row-level errors.

Main interface:

```python
def parse_mega_json(raw: str, row_number: int | None = None) -> MegaPayload: ...
```

`MegaPayload` contains:

- `file_names`
- `total_bytes`
- `formatted_size`
- `links`

Validation rules:

- Root must be a JSON object.
- `property` must be a list.
- Each link item must have a non-empty `Link` and integer-compatible `Size`.
- By default, any single link-item structural error fails the current record to avoid misleading partial download plans.

## 10. `importer/service.py`

Responsibilities:

- Handle unified upsert for Excel, JSON, and legacy-only records.
- Write actor/source mappings.
- Detect link-set changes.
- Record import errors and statistics.

Main interfaces:

```python
class ImportService:
    def upsert_record(self, import_id: int, record: ImportRecord) -> UpsertResult: ...
    def record_error(self, import_id: int, error: ImportRowError) -> None: ...
```

`upsert_record` steps:

1. Build `source_key`.
2. Query the existing record group.
3. For a new record, insert the group, actor/source mappings, and links.
4. For an existing record, update metadata and `last_seen_at`.
5. Calculate the link-set hash for existing active links.
6. If the hash is identical, only refresh `last_seen_at`.
7. If the hash differs, mark old active links inactive and insert new links.

## 11. `search.py`

Responsibilities:

- Encapsulate search filters and sorting.
- Calculate group-level download status.

Main interfaces:

```python
def search_actor(conn, name: str, limit: int) -> list[SearchRow]: ...
def search_title(conn, keyword: str, limit: int) -> list[SearchRow]: ...
def search_source(conn, source: str, limit: int) -> list[SearchRow]: ...
def search_date(conn, date_from: str | None, date_to: str | None, limit: int) -> list[SearchRow]: ...
def list_undownloaded(conn, actor: str | None, source: str | None, limit: int) -> list[SearchRow]: ...
def get_record_info(conn, target: str) -> RecordInfo: ...
```

Download status aggregation:

```text
none       no active links have completed/legacy_completed status
partial    some active links have completed/legacy_completed status
all        all active links have completed/legacy_completed status
unknown    there are no active links, or status cannot be determined
```

## 12. `mega.py`

Responsibilities:

- Locate `mega-whoami` and `mega-get`.
- Check login status.
- Download a single link.

Main interfaces:

```python
def resolve_executable(configured: str) -> str: ...
def check_login(mega_whoami: str) -> MegaLoginStatus: ...
def download_link(mega_get: str, mega_url: str, output_dir: Path) -> MegaCommandResult: ...
```

Requirements:

- Use `subprocess.run([...], shell=False)`.
- Capture stdout/stderr.
- Cap output summaries, for example at 4000 characters, to avoid oversized database records.
- Do not update the database from this module.

## 13. `app.py`

Responsibilities:

- Serve as the use-case layer between CLI and business modules.
- Read configuration, open connections, and call repositories/services.
- Convert exceptions into displayable results consistently.

Main interfaces:

```python
class RecordTreeApp:
    def init(self) -> InitResult: ...
    def doctor(self) -> DoctorResult: ...
    def import_file(self, path: Path) -> ImportResult: ...
    def search_actor(self, name: str, limit: int) -> list[SearchRow]: ...
    def info(self, target: str) -> RecordInfo: ...
    def plan_download(...) -> DownloadPlan: ...
    def execute_download(plan: DownloadPlan, yes: bool) -> DownloadResult: ...
```

## 14. `cli.py`

Responsibilities:

- Define Typer commands.
- Render Rich tables, panels, and confirmation prompts.
- Control exit codes.

Output principles:

- Search commands output tables.
- `info` outputs a metadata block and a links table.
- `import` outputs a statistics summary and error report path.
- `download` outputs the plan and asks for confirmation before invoking MEGAcmd, unless `--yes` is passed.
- Exception messages are user-facing and do not print Python tracebacks; a future `--verbose` option can support debug output.
