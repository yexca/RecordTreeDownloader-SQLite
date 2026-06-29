# Phase 11: User Documentation

## Goal

Write user and maintainer documentation for installation, initialization, import, search, download, MEGAcmd setup, data paths, testing, and troubleshooting.

## Source Documents

- `dev_documents/requirement_analysis/05_implementation_plan.md`
- `dev_documents/high_level_design/01_system_context.md`
- `dev_documents/high_level_design/02_architecture.md`
- `dev_documents/detail_design/05_testing_and_operations.md`

## Scope

Create or update:

```text
README.md
README.zh-cn.md
documents/architecture.md
documents/data_contract.md
documents/testing_guide.md
```

The documentation should be useful without requiring users to read the design documents.

## README Content

Include:

- project summary: local Python + SQLite CLI
- non-goals: no remote source crawling, no MEGA credential storage, no GUI
- installation
- initialization
- unified import command
- search examples
- info and stats examples
- download examples
- MEGAcmd login note
- default database/config/download/log paths
- common failures and troubleshooting commands

Example commands:

```text
recordtree init
recordtree import "files/current_record_tree.xlsx"
recordtree import files/legacy_record.db
recordtree import "files/legacy_record_tree.json"
recordtree search-actor "<name>"
recordtree search-source niconico
recordtree info 123
recordtree download 123 --types mp4,m4a
recordtree download 123 --include-par2 --yes
recordtree doctor
recordtree stats
```

## Architecture Document

`documents/architecture.md` should cover:

- local single-process CLI architecture
- layers: CLI, application services, domain helpers, repositories, infrastructure
- dependency direction
- why SQLite is used
- why Excel is the primary data source
- why download status is link-level authoritative
- why `legacy/` is reference-only

## Data Contract Document

`documents/data_contract.md` should cover:

- required Excel columns
- MEGA JSON root fields
- required link item fields
- legacy SQLite schema
- legacy JSON supported shape
- `source_key` input fields
- active/inactive link rules
- download status values:

```text
planned
completed
failed
blocked
cancelled
legacy_completed
```

## Testing Guide

`documents/testing_guide.md` should cover:

- installing test dependencies
- running the full test suite
- running a single test file or focused unit tests
- fixture design principles
- why MEGAcmd tests must use mocks
- backup guidance before large real-data imports

## Troubleshooting Notes

Document common commands:

```text
recordtree doctor
recordtree stats
recordtree info <id>
recordtree list-undownloaded --limit 20
```

Document generated files:

```text
logs/recordtree.log
logs/import_<import_id>_errors.csv
```

Backup guidance:

- Back up `env/recordtree.sqlite3` before importing a legacy DB.
- Back up the database before large re-imports.
- With SQLite WAL mode, account for `-wal` and `-shm`, or use the SQLite backup API.

## Acceptance Checks

- README lets a new user install, initialize, import, search, and download.
- `README.zh-cn.md` contains the same command examples as README.
- `documents/architecture.md` explains module boundaries and key decisions.
- `documents/data_contract.md` helps maintainers validate input files.
- `documents/testing_guide.md` explains how to run tests and design fixtures.

## Done When

Users can operate the CLI from README instructions, and maintainers can understand architecture, data contracts, and test strategy from `documents/`.
