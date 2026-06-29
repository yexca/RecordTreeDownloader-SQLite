# Phase 5: Excel Import

## Goal

Implement `recordtree import <path>` for `.xlsx` and `.xlsm`. Excel is the v1 primary data source, so the importer must support streaming reads, header validation, MEGA JSON parsing, row-level errors, import audit rows, and idempotent re-import.

## Source Documents

- `dev_documents/requirement_analysis/02_data_profile.md`
- `dev_documents/requirement_analysis/04_cli_and_flows.md`
- `dev_documents/requirement_analysis/05_implementation_plan.md`
- `dev_documents/high_level_design/03_data_import_and_migration_design.md`
- `dev_documents/detail_design/03_import_detail_design.md`

## Scope

Implement:

- `.xlsx` / `.xlsm` import dispatch
- workbook header validation
- `openpyxl.load_workbook(read_only=True, data_only=True)`
- row parsing into `ImportRecord(source_type="xlsx")`
- MEGA JSON parsing into `LinkItem` values
- shared `ImportService` integration
- import summary output
- error CSV export

## Files To Implement

- `recordtree/importer/excel.py`
- `recordtree/importer/parsers.py`
- `recordtree/app.py`
- `recordtree/cli.py`
- `recordtree/repositories.py`

## Header Handling

Match the 10 observed workbook columns to internal fields:

```text
actor_raw
delivery_date
title
entry_date
note
upload_title
duplicate_search_raw
source_name
mega_json
size_raw
```

Rules:

- Missing required columns are hard errors.
- Duplicate headers are hard errors.
- Extra columns are allowed and should be reported in the import summary.
- If readable Chinese headers are later confirmed in the source workbook, support them as aliases while keeping the current observed header strings supported.

## Row Parsing

For each row:

1. Read actor, title, upload title, source, MEGA JSON, and size.
2. Treat missing required fields as row-level errors.
3. Normalize `delivery_date` and `entry_date`; blanks are allowed.
4. Parse `size_raw`; malformed display sizes return `None` and do not block import.
5. Parse `mega_json`.
6. Build `ImportRecord(source_type="xlsx")`.

Read only the active sheet or first sheet in v1. Multi-sheet merge support is out of scope.

## MEGA JSON Parsing

`parse_mega_json(raw, row_number)` supports:

```json
{
  "FileNames": "...",
  "total": 937552133,
  "FormattedSize": "894.12 MB",
  "property": [
    {
      "Link": "https://mega.nz/file/...",
      "Size": 875464405,
      "FormattedSize": "834.91 MB",
      "Type": ".mp4"
    }
  ]
}
```

Error codes:

- `mega_json_invalid_root`
- `mega_json_parse_error`
- `mega_property_invalid`
- `mega_property_empty`
- `mega_link_missing`
- `mega_size_invalid`

If any link item is structurally invalid, reject the whole row so download plans are never based on partial link sets.

## Import Dispatch

`app.import_file(path)` should:

1. Check that the file exists.
2. Detect source type by extension.
3. Create `ExcelImporter` for `.xlsx` and `.xlsm`.
4. Create an `imports` row with status `running`.
5. Iterate `iter_records(path)`.
6. Call `ImportService.upsert_record` for each valid record.
7. Continue after row-level errors.
8. Finish the import with `completed` or `completed_with_errors`.
9. Export `logs/import_<import_id>_errors.csv` when errors exist.

## CLI Output

Print a concise summary:

- import id
- source file
- total rows
- inserted groups
- updated groups
- link sets changed
- inserted links
- skipped links
- error count
- error CSV path, when present

## Test Guidance

Use a small workbook fixture with:

- one single-link row
- one multi-link row
- one row with blank dates and blank note
- one malformed MEGA JSON row

Assertions:

- valid rows import successfully
- malformed rows are written to `import_errors`
- import status is `completed_with_errors`
- repeated import does not increase active link count

## Acceptance Checks

- The current Record Tree workbook can be imported.
- Target data scale is tens of thousands of visible record groups and hundreds of thousands of active links, excluding intentionally skipped malformed rows.
- Re-import is idempotent.
- Header and row-level errors are clear.
- Large workbooks are read in streaming mode.

## Done When

Excel can be used as the primary source to populate record groups and active links for search and download workflows.
