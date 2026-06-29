# RecordTreeDownloader Requirements Overview

## 1. Project Goal

Refactor the old RecordTreeDownloader script collection into a maintainable Python command-line tool similar to `DLTreeDownloader-SQLite`.

The new program should:

- Import the latest Record Tree Excel workbook into SQLite.
- Preserve existing user history from the copied legacy database `files/legacy_record.db`.
- Keep a JSON import path for old exports, even though the official source currently appears to be Excel only.
- Search records by actor, source, title, date, and download status.
- Download selected MEGA links through MEGAcmd after checking login state and disk space.
- Track download history without losing old downloaded/undownloaded state.

The old program should be kept under a `legacy/` folder during the refactor so that behavior can still be inspected without mixing legacy scripts into the new package.

## 2. Current Program Summary

The current root-level scripts use global configuration and small mapper classes:

- `main.py` switches between search, download, and insert modes through `config.py`.
- `recordinsertbyxlsx.py` imports Excel rows.
- `recordInsert.py` imports old JSON rows.
- `download.py` downloads undownloaded records for one author.
- `mapper/authorMapper.py` and `mapper/recordMapper.py` access SQLite directly.

Observed legacy tables:

```text
author(author_id, name, added_date)
record(record_id, author_id, name, date, size, link, added_date, downloaded_date)
```

Important legacy behavior:

- `downloaded_date = '0'` means not downloaded.
- A date string in `downloaded_date` means downloaded.
- Duplicate links are skipped during legacy import.
- Download selection is author-based and count-based rather than record-based.

## 3. Source Data Summary

Observed latest workbook:

- File: `files/current_record_tree.xlsx`
- Sheet count: 1
- Sheet name: `Sheet1`
- Rows: tens of thousands
- Columns: 10
- Parsed MEGA links: more than one per row on average
- MEGA JSON parse errors in inspected file: 0

Observed columns:

| Column | Meaning |
|---|---|
| `声优` | Actor/performer name |
| `配信日期` | Delivery or stream date |
| `标题` | Title |
| `录入日期` | Record entry/import date from source |
| `备注` | Notes, often record-count text |
| `上传标题` | Canonical uploaded file group title |
| `重复检索` | Duplicate-search helper text |
| `来源` | Source platform |
| `MEGA` | JSON string containing file links and sizes |
| `容量` | Human-readable total size |

Observed old JSON file:

- File: `files/legacy_record_tree.json`
- Root type: list
- Author count: hundreds
- Shape: author object with `author`, `total_records`, `records`
- Record object includes `FileNames`, `total`, `FormattedSize`, `property`
- Link item includes `Link`, `Size`, `FormattedSize`, `Type`

## 4. Core User Stories

1. As a user, I can initialize a local CLI environment with config, database, logs, and download directories.
2. As a user, I can import the latest Excel workbook and safely re-import it later without duplicate active links.
3. As a user, I can import the copied legacy SQLite database and preserve previous downloaded status.
4. As a user, I can import old JSON exports for compatibility.
5. As a user, I can search records by actor name, source platform, title keyword, date range, and download status.
6. As a user, I can inspect one record group and see all active MEGA file links, file types, sizes, and previous download status.
7. As a user, I can download one record group or selected file types only after MEGAcmd and disk space checks pass.
8. As a user, I can keep `.par2` handling explicit because these files are common and may be optional.

## 5. Recommended CLI Scope

Initial commands:

```text
recordtree init
recordtree doctor
recordtree import <path>
recordtree search-actor <name>
recordtree search-title <keyword>
recordtree search-source <source>
recordtree search-date --from <date> --to <date>
recordtree list-undownloaded [--actor <name>] [--limit <n>]
recordtree info <record_id_or_key>
recordtree download <record_id_or_key> [--include-par2] [--types <exts>] [--output <dir>] [--yes]
recordtree stats
```

The `import` command should select the importer automatically:

- `.xlsx` / `.xlsm`: Excel workbook import.
- `.json`: legacy JSON import.
- `.db` / `.sqlite` / `.sqlite3`: legacy SQLite database import after schema validation.

If the extension is ambiguous or unsupported, the command should stop with a clear message. Optional explicit overrides such as `--type xlsx|json|legacy-db` can be added later, but should not be required for normal use.

## 6. Non-Goals For The First Version

- GUI application.
- Automatic scheduled import or background monitoring.
- Automatic MEGA credential storage.
- Automatic source-site scraping.
- Multi-user database access.
- Full-text search engine beyond SQLite `LIKE` or optional FTS.
- Integrity verification beyond MEGAcmd result and optional size summaries.
- Recreating the old config-driven run-mode interface.

## 7. Important Decisions

### Use Excel as the primary import source

The latest official data available in this workspace is an Excel workbook. The JSON import should remain for backward compatibility, but the main data contract should be the observed xlsx columns.

### Do not use `上传标题` alone as a unique key

The inspected workbook has duplicate `上传标题` values. `MEGA` values may be unique in one snapshot, but links can change over time. The database should use an internal `record_group` id and a content key derived from stable metadata such as actor, delivery date, title, entry date, source, upload title, and/or legacy filename.

### Preserve old downloaded status

Legacy `record.downloaded_date` contains real user history. Migration must map it into the new schema instead of discarding it.

### Preserve historical links

If a later import changes the link set for the same record group, keep old link rows and mark them inactive or deleted. Normal searches and downloads should show only active links by default.

### Keep actor names as first-class entities

The old program is actor-centered and the workbook has a required `声优` column. Store raw actor text on each record group and a normalized `actors` table for search.

## 8. Open Questions Before Implementation

1. What should the canonical record identity be when two rows share the same upload title but differ in links?
2. Should downloads mark status at file-link level, record-group level, or both?
3. Should `.par2` files be excluded by default, matching the DLTree project, or included for completeness?
4. Should the default download command download all non-`.par2` files for a group, or ask users to choose file types interactively?
5. Should legacy database import be one-time migration into the same database, or a repeatable command with idempotent merge behavior?
