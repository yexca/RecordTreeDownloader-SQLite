# RecordTreeDownloader Detailed Design

This folder documents the detailed design for RecordTreeDownloader-SQLite and builds on:

- `dev_documents/requirement_analysis/`
- `dev_documents/high_level_design/`

Recommended reading order:

1. `01_module_design.md`
2. `02_database_design.md`
3. `03_import_detail_design.md`
4. `04_cli_search_download_detail.md`
5. `05_testing_and_operations.md`

## Design Goals

The detailed design refines the architectural decisions from the high-level design into implementable modules, data structures, SQL, algorithms, and command behavior. The goal is to make later implementation proceed module by module, with core rules verifiable through unit tests and small integration tests.

## v1 Scope

The v1 detailed design covers:

- New `recordtree` Python package structure.
- Configuration, database connection, and schema initialization.
- Excel, legacy SQLite, and legacy JSON import paths.
- Unified import upsert service.
- Actor/title/source/date/download-status search.
- Record group detail display.
- MEGAcmd download planning, pre-checks, execution, and status recording.
- Test strategy, fixture design, logs, and operational troubleshooting.

## Key Conventions

- Command name: `recordtree`.
- Default database: `env/recordtree.sqlite3`.
- Default configuration: `env/config.toml`.
- Default download directory: `downloads/<record_group_id>/`.
- Default log directory: `logs/`.
- Excel is the primary data source; JSON and legacy SQLite are compatibility/migration paths.
- Link-level download status is authoritative; record-group status is only an aggregate display.
- `.par2` is excluded by default unless configuration or command arguments explicitly include it.
