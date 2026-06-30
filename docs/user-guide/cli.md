# CLI Guide

The CLI entry point is `recordtree`.

## Initialize

```bash
recordtree init
```

Default runtime paths:

- Config: `env/config.toml`
- Database: `env/recordtree.sqlite3`
- Downloads: `downloads/`
- Logs: `logs/`
- Import error CSVs: `logs/import_<import_id>_errors.csv`
- Download output logs: `logs/downloads/download_<download_id>.log`

## Import Data

```bash
recordtree import "files/recordtree-export.xlsx"
recordtree import files/legacy-record.sqlite3
recordtree import "files/legacy-record.json"
```

Recommended import order:

1. Excel workbook
2. Legacy SQLite database
3. Legacy JSON export

Excel is treated as the highest-quality metadata source. Legacy SQLite can attach old download history by matching existing active URLs. JSON is mainly for compatibility and backfill.

## Search And Inspect

```bash
recordtree search-actor "<name>"
recordtree actor-records 12
recordtree search-source niconico
recordtree search-title ASMR
recordtree search-date --from 2026-01-01 --to 2026-01-31
recordtree list-undownloaded --limit 20
recordtree list-undownloaded --actor-id 12 --limit 20
recordtree info 123
recordtree stats
```

Search commands are case-insensitive and default to a limit of 50 rows.

## Download

Log in with MEGAcmd first:

```bash
mega-login
recordtree doctor
```

Examples:

```bash
recordtree download 123 --types mp4,m4a
recordtree download 123 --include-par2 --yes
recordtree download 123 --output "D:/RecordTree/123"
recordtree download --actor 12 --count 5 --yes
```

By default, `.par2` files are excluded. Use `--include-par2` to include them.

Each download attempt records item status in SQLite. When MEGAcmd runs, its streamed output is also written to `logs/downloads/download_<download_id>.log`.
