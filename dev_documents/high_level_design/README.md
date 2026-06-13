# RecordTreeDownloader High-Level Design

This folder documents the high-level design for RecordTreeDownloader-SQLite and builds on the requirements analysis in `dev_documents/requirement_analysis/`.

Recommended reading order:

1. `01_system_context.md`
2. `02_architecture.md`
3. `03_data_import_and_migration_design.md`
4. `04_cli_and_download_design.md`
5. `05_quality_and_decisions.md`

## Design Goals

RecordTreeDownloader-SQLite is a local Python + SQLite command-line tool. It imports Record Tree data sources, searches records, preserves legacy download history, and downloads selected MEGA files when MEGAcmd and disk space checks pass.

The high-level design focuses on:

- System boundaries, external dependencies, and main inputs and outputs.
- Module decomposition, dependency direction, and core responsibilities.
- A unified handling model for Excel, JSON, and legacy SQLite import paths.
- Runtime design for search, info, download, and diagnostic commands.
- Data consistency, recoverability, testability, and key design decisions.

## Main Design Conclusions

- Use a single-machine CLI architecture, without a background service, GUI, or remote database.
- Use SQLite for local persistence. The default database file is `env/recordtree.sqlite3`.
- Excel is the primary v1 data source; JSON and legacy SQLite are compatibility/migration paths.
- Use `record_groups` as the primary record-group entity, and use `download_links` to store current and historical MEGA links.
- Link-level download status is authoritative. Record-group status is derived from link status and recent download attempts.
- Import uses `source_key` for record-group upsert, detects link changes with a link-set hash, and preserves replaced historical links.
- Legacy SQLite migration must preserve `downloaded_date` and should preferentially merge into Excel-imported records by URL match.
- Downloads exclude `.par2` by default. Users can explicitly include it through configuration or `--include-par2`.

## Relationship To Requirements Analysis

This high-level design does not repeat the full field profiles and statistics from the requirements analysis. Instead, it turns the requirements analysis into an implementable system plan. Detailed field semantics, import statistics, command lists, and acceptance items remain grounded in `dev_documents/requirement_analysis/`.
