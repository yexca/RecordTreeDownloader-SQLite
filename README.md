# RecordTreeDownloader SQLite

RecordTreeDownloader SQLite is a local Python command-line tool for importing Record Tree metadata into SQLite, searching it, and downloading selected MEGA links through MEGAcmd.

The tool is intentionally local-first. It does not crawl remote sources, store MEGA credentials, or provide a GUI. MEGA authentication stays in your MEGAcmd installation.

## Installation

Requirements:

- Python 3.11 or newer
- MEGAcmd for downloads

Install the package and dependencies:

```bash
python -m pip install -e .
```

For test development, install the dev extra:

```bash
python -m pip install -e ".[dev]"
```

## Initialize

Create the local config, SQLite database, download directory, and log directory:

```bash
recordtree init
```

Default generated paths:

- Config: `env/config.toml`
- Database: `env/recordtree.sqlite3`
- Downloads: `downloads/`
- Logs: `logs/`
- Import error CSVs: `logs/import_<import_id>_errors.csv`

Edit `env/config.toml` if you want custom paths, MEGAcmd executable names, or download safety margin settings.

## Import Data

Use the same command for the primary Excel workbook, legacy SQLite database, and legacy JSON export:

```bash
recordtree import "files/Record Tree 260605.xlsx"
recordtree import files/record.db
recordtree import "files/Record Tree.Json"
```

Imports are designed to be repeatable. The importer upserts record groups by a generated source key and preserves historical inactive links when a record's active link set changes.

Before importing a large legacy database or doing a large re-import, back up `env/recordtree.sqlite3`. If SQLite WAL files exist, include `env/recordtree.sqlite3-wal` and `env/recordtree.sqlite3-shm`, or use the SQLite backup API.

## Search And Inspect

```bash
recordtree search-actor "<name>"
recordtree search-source niconico
recordtree search-title ASMR
recordtree search-date --from 2026-01-01 --to 2026-01-31
recordtree list-undownloaded --limit 20
recordtree info 123
recordtree stats
```

Search commands are case-insensitive and default to a limit of 50 rows.

## Download

Log in with MEGAcmd outside this tool first:

```bash
mega-login
```

Then check local readiness:

```bash
recordtree doctor
```

Download examples:

```bash
recordtree download 123 --types mp4,m4a
recordtree download 123 --include-par2 --yes
recordtree download 123 --output "D:/RecordTree/123"
```

By default, `.par2` files are excluded. Use `--include-par2` to include them. The downloader checks MEGAcmd availability, login status, selected byte count, and free disk space before running `mega-get`.

## Troubleshooting

Useful commands:

```bash
recordtree doctor
recordtree stats
recordtree info <id>
recordtree list-undownloaded --limit 20
```

Common failures:

- Missing config or database: run `recordtree init`.
- Unsupported import extension: use `.xlsx`, `.xlsm`, `.json`, `.db`, `.sqlite`, or `.sqlite3`.
- Import row errors: check `logs/import_<import_id>_errors.csv`.
- MEGAcmd missing: install MEGAcmd and ensure `mega-get` and `mega-whoami` are on `PATH`, or configure executable paths in `env/config.toml`.
- Not logged in: run `mega-login` manually, then `recordtree doctor`.
- Insufficient disk space: change `--output`, free space, or adjust the safety margin in `env/config.toml`.

## Testing

Run the automated test suite:

```bash
pytest
```

MEGAcmd tests use mocks and do not require a real MEGA account or network access.

## Maintainer Docs

- [Architecture](documents/architecture.md)
- [Data contract](documents/data_contract.md)
- [Testing guide](documents/testing_guide.md)
