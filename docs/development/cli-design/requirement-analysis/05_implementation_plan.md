# Implementation Plan

## Phase 1: Preserve Legacy Code

Move current root-level legacy scripts into:

```text
legacy/
```

Legacy files to preserve include:

```text
config.py
db.py
download.py
initSqlite.py
main.py
mega.py
Record.py
recordInsert.py
recordinsertbyxlsx.py
util.py
mapper/
```

Acceptance checks:

- Legacy files are still readable under `legacy/`.
- New package files do not import from `legacy/`.
- Git history clearly shows the move during implementation.

## Phase 2: Project Skeleton

Create a package structure similar to the reference CLI project:

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
    service.py
  mega.py
  models.py
  normalizers.py
  repositories.py
  schema.sql
  search.py
  sizes.py
tests/
documents/
dev_documents/
```

Recommended dependencies:

```text
openpyxl
typer
rich
```

Potential packaging files:

```text
pyproject.toml
requirements.txt
run-install.bat
setup_env.ps1
```

## Phase 3: Database Initialization

Implement:

- `recordtree init`
- Config creation under `env/config.toml`
- SQLite schema creation under `env/recordtree.sqlite3`
- `downloads/` and `logs/` creation

Acceptance checks:

- Running `recordtree init` creates required folders/files.
- Running it twice is safe.
- All schema tables and indexes exist.

## Phase 4: Core Import Service

Implement shared import logic for normalized record groups and link items:

- Text normalization.
- Date normalization.
- Size parsing.
- Source key hashing.
- Link set hashing.
- Record group upsert.
- Actor/source mapping refresh.
- Link replacement and historical preservation.
- Import stats and row-level errors.

Acceptance checks:

- Import service can be tested with in-memory sample rows.
- Same sample imported twice creates no duplicate active links.
- Changed link set marks old active links deleted and inserts new links.

## Phase 5: Excel Import

Implement:

- `recordtree import <path>` dispatch for `.xlsx` / `.xlsm`.
- Workbook header validation for the 10 observed columns.
- Streaming row iteration with `openpyxl.load_workbook(read_only=True, data_only=True)`.
- MEGA JSON parsing for root keys `FileNames`, `total`, `FormattedSize`, `property`.
- Progress reporting through Rich.
- Error CSV export when row-level errors exist.

Acceptance checks:

- Import `files/current_record_tree.xlsx`.
- Database contains the expected visible record groups after import.
- Active link count matches the parsed workbook link count after first import, minus only intentionally skipped malformed rows.
- Re-import is idempotent.

## Phase 6: Legacy Database Import

Implement:

- `recordtree import <path>` dispatch for `.db` / `.sqlite` / `.sqlite3`.
- Schema validation for `author` and `record`.
- URL-based matching to xlsx-imported links.
- Legacy-only group creation for unmatched URLs.
- Migration mapping storage.
- Downloaded status preservation.

Acceptance checks:

- Import `files/legacy_record.db`.
- Reads all expected legacy authors and records.
- Preserves all expected downloaded statuses.
- Does not create duplicate active URLs.
- Can run a second time without duplicating migrated rows.

## Phase 7: JSON Import

Implement:

- `recordtree import <path>` dispatch for `.json`.
- Old JSON root list parsing.
- Author/records/property traversal.
- Shared import service integration.
- Lower priority metadata merge when matching existing links.

Acceptance checks:

- Import `files/legacy_record_tree.json` without crashing.
- Row-level malformed records are reported, not fatal.
- Re-import is idempotent.

## Phase 8: Search And Info Commands

Implement:

- `search-actor`
- `search-title`
- `search-source`
- `search-date`
- `list-undownloaded`
- `info`
- `stats`

Acceptance checks:

- Known actor search returns rows from the imported xlsx.
- Source search works for `niconico`, `Withny`, and `rPlay`.
- `list-undownloaded` respects legacy migrated download statuses.
- `info` shows active links and status without overwhelming the terminal.

## Phase 9: MEGAcmd Download

Implement:

- `doctor`
- MEGAcmd executable resolution.
- `mega-whoami` login check.
- Download planning and confirmation.
- Disk space check.
- `mega-get` execution.
- Download and download item status recording.

Acceptance checks:

- Missing MEGAcmd is reported clearly.
- Not logged in stops before download.
- Insufficient disk space stops before `mega-get`.
- Mocked successful `mega-get` marks selected items completed.
- Failed `mega-get` records failed item status and useful message.

## Phase 10: Tests

Minimum tests:

- Size parser:
  - `894.12 MB`
  - `13.53 GB`
  - `0 B`
  - malformed text
- Date parser:
  - Excel datetime
  - ISO string
  - blank
- Excel MEGA parser:
  - valid JSON
  - missing `property`
  - missing `Link`
  - non-integer `Size`
- Source key:
  - stable for identical metadata
  - changes when title/source/date changes
- Import idempotency:
  - same sample twice
  - changed link set
- Legacy migration:
  - downloaded date `0`
  - downloaded date string
  - URL match with existing xlsx link
  - unmatched legacy row
- Search:
  - actor/source/title filters
  - limit behavior
- Download:
  - par2 exclusion
  - type filter
  - disk check
  - mocked MEGAcmd calls

## Phase 11: User Documentation

Create:

```text
README.md
README.zh-cn.md
documents/architecture.md
documents/data_contract.md
documents/testing_guide.md
```

README should include:

- Installation.
- Initialization.
- Unified import command with xlsx, JSON, and legacy DB examples.
- Search examples.
- Download examples.
- MEGAcmd login note.
- Database and config paths.

## Risks And Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Future workbook column changes | Import fails | Validate by header names and report missing/extra columns clearly. |
| Upload title is not unique | Wrong merges | Use source key from multiple metadata fields. |
| Links change for same record | Lost history | Keep historical links with `is_deleted`. |
| Legacy DB overlaps xlsx data | Duplicate active links | Match by URL and keep migration map. |
| JSON text quality is worse than xlsx | Bad metadata | Treat JSON as compatibility source with lower priority. |
| Large import is slow | Poor UX | Use read-only workbook streaming, transactions, indexes, and progress display. |
| MEGAcmd session state is stale | Download fails confusingly | Run `mega-whoami` before `mega-get`. |
| Disk usage underestimated | Mid-download failure | Add configurable safety margin. |

## Suggested Defaults

- Command name: `recordtree`
- Database: `env/recordtree.sqlite3`
- Config: `env/config.toml`
- Downloads: `downloads/<record_group_id>/`
- Logs: `logs/`
- Download default: exclude `.par2`
- Search result limit: 50
- Import mode: upsert by source key, replace active links only when link set changes
