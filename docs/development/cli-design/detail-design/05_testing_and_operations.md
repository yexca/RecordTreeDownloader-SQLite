# Testing And Operations Detailed Design

## 1. Test Layers

v1 uses three test layers:

| Layer | Goal | Dependencies |
|---|---|---|
| Unit tests | Verify pure rules and small functions | No real database or MEGAcmd |
| Integration tests | Verify SQLite schema, import upsert, and queries | Temporary SQLite and small fixtures |
| Command tests | Verify CLI arguments, output, and exit codes | Typer CliRunner or subprocess |

MEGAcmd download tests use mocks and do not access the real network or a real account.

## 2. Test Directory

```text
tests/
  fixtures/
    sample_record_tree.xlsx
    sample_record_tree_changed_links.xlsx
    sample_legacy.json
    sample_legacy.db
  test_normalizers.py
  test_sizes.py
  test_mega_parser.py
  test_import_service.py
  test_excel_importer.py
  test_legacy_db_importer.py
  test_json_importer.py
  test_search.py
  test_download_plan.py
  test_cli.py
```

Fixtures should stay small:

- Excel: 3 to 5 rows.
- JSON: 1 to 2 authors.
- Legacy DB: 3 to 5 records.

## 3. Unit Test Checklist

### normalizers

Cover:

- `clean_text(None)`.
- Empty strings and whitespace-only strings.
- Trimming normal strings.
- Case folding in `normalize_search_text`.
- `normalize_file_type("mp4") == ".mp4"`.
- `normalize_file_type(".MP4") == ".mp4"`.
- Excel datetime to ISO.
- ISO strings remain stable.
- Empty dates return null.
- Invalid dates raise an error.

### sizes

Cover:

```text
894.12 MB
13.53 GB
0 B
1024 KB
malformed text
None
```

Safety margin:

- Use 5% when 5% is greater than 512 MB.
- Use 512 MB when 5% is less than 512 MB.

### MEGA JSON parser

Cover:

- Valid JSON.
- Root is not an object.
- Missing `property`.
- `property` is not a list.
- Link missing `Link`.
- Link `Size` is a numeric string.
- Link `Size` cannot be converted to integer.
- Missing `Type`.

### hash

Cover:

- Identical metadata generates the same source key.
- Title changes generate a different source key.
- Source changes generate a different source key.
- The same link set repeatedly generates the same link-set hash.
- Whether link order affects the hash is fixed by design; v1 keeps it order-sensitive.

## 4. ImportService Integration Tests

Use temporary SQLite:

1. Initialize schema.
2. Build an `ImportRecord`.
3. Call `upsert_record`.

Scenarios:

- First import inserts group and links.
- Re-importing the same record does not add active links.
- Same metadata but changed link set: old links inactive, new links active.
- Same URL already active in another group: record a conflict error.
- Repeated actor/source mapping calls do not create duplicate joins.

Acceptance SQL:

```sql
SELECT COUNT(*) FROM record_groups;
SELECT COUNT(*) FROM download_links WHERE is_deleted = 0;
SELECT COUNT(*) FROM download_links WHERE is_deleted = 1;
```

## 5. Excel Import Tests

Fixture contains:

- 1 single-link row.
- 1 multi-link row.
- 1 row with blank dates and blank note.
- 1 row with malformed MEGA JSON.

Assertions:

- Valid rows import successfully.
- Malformed row is written to `import_errors`.
- Import status is `completed_with_errors`.
- Repeated import does not change active link count.

## 6. Legacy DB Migration Tests

Fixture legacy DB:

- 2 authors.
- 4 records.
- 1 URL matching an already imported Excel link.
- 1 unmatched legacy-only record.
- 1 record with `downloaded_date = '0'`.
- 1 record with `downloaded_date = '<completed-date>'`.

Assertions:

- Matching URL reuses existing link.
- Unmatched record creates a legacy-only group.
- `legacy_migration_map` has corresponding rows.
- `legacy_completed` status is created.
- A second migration does not duplicate data.

## 7. JSON Import Tests

Fixture JSON:

- Root list.
- 1 author.
- 2 records.
- 1 malformed record.

Assertions:

- Valid record imports.
- Malformed record records an error.
- When URL overlaps with Excel, Excel actor/title/source are not overwritten.

## 8. Search Tests

Prepare data:

- actor A / source niconico / title ASMR.
- actor B / source Withny / title music.
- Different delivery dates.
- completed, partial, and none download statuses.

Cover:

- Actor `LIKE` search.
- Title search matching `title`.
- Title search matching `upload_title`.
- Case-insensitive source search.
- Date from/to.
- `list-undownloaded` excludes all-completed groups.
- Limit behavior.

## 9. Download Plan Tests

Do not call MEGAcmd; test only planning:

- Default excludes `.par2`.
- `--include-par2` includes `.par2`.
- `--types mp4,m4a` filters successfully.
- `--types par2` without include-par2 leaves no links.
- Selected bytes and required bytes are correct.
- If output directory does not exist, check the nearest existing parent.
- Insufficient space generates a blocked result.

## 10. MEGAcmd Execution Tests

Use mocked subprocess:

- `mega-whoami` exit 0: logged in.
- `mega-whoami` non-zero exit: not logged in.
- `mega-get` exit 0: item completed.
- `mega-get` non-zero exit: item failed.
- Long stdout/stderr is truncated.

Assertions:

- Command arguments use a list, not shell.
- When not logged in, `mega-get` is not called.
- When disk space is insufficient, `mega-get` is not called.

## 11. CLI Tests

Cover:

- `recordtree init` is repeatable.
- Unsupported import extension returns exit code 2.
- Missing `info` target returns exit code 3.
- Search limit below 1 returns exit code 2.
- Declining download confirmation creates a cancelled record.

CLI output should assert key text only, not brittle full table snapshots.

## 12. Logging Strategy

Recommended v1 file logs:

```text
logs/recordtree.log
logs/import_<import_id>_errors.csv
```

Record:

- Import start/end.
- Import hard failure.
- Error CSV path.
- Download blocked/cancelled/failed summary.
- MEGAcmd exit code.

Do not record:

- MEGA account passwords.
- Full overlong stdout/stderr.
- Unrelated local environment variables.

## 13. Operational Troubleshooting Commands

Common commands:

```text
recordtree doctor
recordtree stats
recordtree info <id>
recordtree list-undownloaded --limit 20
```

Recommended future commands:

```text
recordtree list-imports
recordtree import-errors <import_id>
recordtree export-links <record_id_or_key>
```

## 14. Performance Concerns

Import scale:

- Excel: tens of thousands of rows.
- Active links: hundreds of thousands of rows.
- Legacy records: hundreds of thousands of rows.

Implementation recommendations:

- Use read-only streaming for Excel.
- Wrap imports in transactions.
- Prepare necessary indexes, but avoid repeated complex per-row queries.
- Rely on `idx_links_url` for URL matching.
- Use default query limits.

If import performance is insufficient, optimize in this order:

1. Reduce repeated per-row queries.
2. Batch-prefetch actor/source ids.
3. Build an in-memory cache for link URLs.
4. Defer non-essential statistics.

## 15. Data Backup Recommendations

User documentation should recommend:

- Back up `env/recordtree.sqlite3` before importing the legacy DB.
- Back up the database file before large re-imports.
- In SQLite WAL mode, handle `-wal` and `-shm` files during backup, or use the SQLite backup API.

## 16. Acceptance Checklist

v1 completion criteria:

- `recordtree init` creates configuration, database, download directory, and log directory.
- Excel import handles the current workbook and can be repeated.
- Active link count does not grow after repeated imports.
- Legacy DB migration preserves download status.
- JSON import is compatible with the old format.
- Actor/title/source/date searches work.
- `info` displays active links and download status.
- Download pre-checks verify MEGAcmd, login, and disk space.
- `.par2` is excluded by default and can be included by argument.
- Core rules have unit tests.
- MEGAcmd-related tests do not depend on the real network.
