# Phase 10: Tests

## Goal

Add v1 test coverage for core rules, import idempotency, query behavior, download planning, MEGAcmd command wrapping, and CLI exit codes. Tests must not depend on real MEGA network access or a real MEGA account.

## Source Documents

- `dev_documents/requirement_analysis/05_implementation_plan.md`
- `dev_documents/high_level_design/05_quality_and_decisions.md`
- `dev_documents/detail_design/05_testing_and_operations.md`

## Test Layers

| Layer | Goal | Dependencies |
|---|---|---|
| Unit tests | Validate pure rules and small helpers | no real DB or MEGAcmd |
| Integration tests | Validate SQLite schema, import upsert, and search | temporary SQLite and small fixtures |
| CLI tests | Validate command parameters, output, and exit codes | Typer `CliRunner` or subprocess |

MEGAcmd tests must use mocks.

## Recommended Test Tree

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

Keep fixtures small:

- Excel: 3 to 5 rows
- JSON: 1 to 2 authors
- legacy DB: 3 to 5 records

## Unit Test Checklist

`normalizers`:

- `clean_text(None)`
- empty and whitespace-only strings
- normal string trim
- `normalize_search_text` case folding
- `normalize_file_type("mp4") == ".mp4"`
- `normalize_file_type(".MP4") == ".mp4"`
- Excel datetime to ISO date
- ISO string remains stable
- blank date returns null
- invalid date raises an error

`sizes`:

```text
894.12 MB
13.53 GB
0 B
1024 KB
malformed text
None
```

Safety margin:

- choose 5% when 5% is larger than 512 MB
- choose 512 MB when 5% is smaller than 512 MB

`MEGA JSON parser`:

- valid JSON
- root is not object
- missing `property`
- `property` is not a list
- link missing `Link`
- link `Size` as a numeric string
- link `Size` not convertible to integer
- missing `Type`

`hash`:

- identical metadata produces the same `source_key`
- title change changes `source_key`
- source change changes `source_key`
- identical link set produces the same `link_set_hash`
- link order affects hash in v1

## Integration Test Checklist

`ImportService`:

- first import inserts group and links
- repeated import does not add active links
- same metadata with changed links marks old links inactive and new links active
- same active URL under another group records a conflict
- repeated actor/source mapping does not duplicate join rows

`ExcelImporter`:

- valid rows import
- malformed MEGA JSON writes `import_errors`
- import status is `completed_with_errors`
- repeated import does not change active link count

`LegacyDbImporter`:

- matched URL reuses an existing link
- unmatched URL creates a legacy-only group
- `legacy_migration_map` rows are created
- `legacy_completed` status is created
- second migration does not duplicate rows

`JsonImporter`:

- valid record imports
- malformed record writes an error
- overlapping Excel URL does not overwrite Excel actor/title/source

## Search Tests

Prepare data with:

- actor A / source niconico / title ASMR
- actor B / source Withny / title music
- different `delivery_date` values
- completed, partial, and none download states

Cover:

- actor LIKE search
- title search matching `title`
- title search matching `upload_title`
- case-insensitive source search
- date from/to search
- `list-undownloaded` excluding all-completed groups
- limit behavior

## Download Tests

Download plan:

- default `.par2` exclusion
- `--include-par2`
- `--types mp4,m4a`
- `--types par2` without `--include-par2`
- correct selected and required bytes
- nonexistent output directory checks nearest existing parent
- insufficient space creates a blocked result

MEGAcmd execution:

- `mega-whoami` exit 0 means logged in
- `mega-whoami` non-zero means not logged in
- `mega-get` exit 0 marks item completed
- `mega-get` non-zero marks item failed
- long stdout/stderr is truncated
- subprocess calls use argument lists, not `shell=True`
- not logged in or insufficient space prevents `mega-get`

## CLI Tests

Cover:

- `recordtree init` is idempotent
- unsupported import extension returns exit code 2
- missing `info` target returns exit code 3
- search limit below 1 returns exit code 2
- download cancellation creates a `cancelled` row

Assert key text only; do not snapshot full Rich tables.

## Acceptance Checks

- Tests run in a clean environment.
- MEGAcmd tests do not access real network.
- Import idempotency and link-change tests pass.
- Download status summary covers all/partial/none.
- Core error paths are covered.

## Done When

The v1 behavior has automated protection for the import, search, and download paths most likely to regress.
