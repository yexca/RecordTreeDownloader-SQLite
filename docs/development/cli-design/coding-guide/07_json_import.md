# Phase 7: JSON Import

## Goal

Implement compatibility import for the old JSON export format. JSON is a lower-priority compatibility source and must not overwrite higher-quality Excel metadata.

## Source Documents

- `dev_documents/requirement_analysis/02_data_profile.md`
- `dev_documents/requirement_analysis/03_database_and_migration.md`
- `dev_documents/requirement_analysis/05_implementation_plan.md`
- `dev_documents/high_level_design/03_data_import_and_migration_design.md`
- `dev_documents/detail_design/03_import_detail_design.md`

## Scope

Implement:

- `.json` import dispatch
- old JSON root-list parsing
- author / records / property traversal
- shared MEGA property parsing rules
- `ImportRecord(source_type="json")` construction
- shared `ImportService` integration
- Excel metadata priority when links overlap

## Files To Implement

- `recordtree/importer/json_importer.py`
- `recordtree/importer/parsers.py`
- `recordtree/importer/service.py`
- `recordtree/app.py`
- `recordtree/cli.py`

## Supported Shape

```text
root list
  author object
    author
    records list
      FileNames
      total
      FormattedSize
      property list
```

## Parsing Rules

- Root must be a list; otherwise this is a hard error.
- A single author object missing `records` is a row-level error.
- A single record missing `property` is a row-level error.
- Use `source_name = "json"` unless a trustworthy source field is found.
- Use `FileNames` as both `title` and `upload_title`.
- Use the author name as `actor_raw`.
- Leave `delivery_date` and `entry_date` null when no reliable date source exists.
- Prefer `total` for `size_bytes` and `FormattedSize` for display.
- Reuse the same link item rules for `Link`, `Size`, `FormattedSize`, and `Type`.

## Metadata Priority

Excel is the primary source:

- If a JSON link matches an existing Excel active link, do not overwrite Excel record group metadata.
- JSON may still contribute import audit information and row-level errors.
- JSON-only records may create new record groups.
- If finer merge policy is needed later, extend `prefer_xlsx_metadata`.

## Import Behavior

`recordtree import <path.json>` should:

1. Check file existence and extension.
2. Create an `imports` row with status `running`.
3. Parse the root list.
4. Build one `ImportRecord` per valid author/record.
5. Call `ImportService`.
6. Continue after row-level errors.
7. Print an import summary.
8. Export `logs/import_<import_id>_errors.csv` when errors exist.

## Test Guidance

Use a fixture containing:

- a root list
- one author
- two records
- one malformed record
- one URL overlapping an Excel fixture

Assertions:

- valid records import
- malformed records are written to `import_errors`
- overlapping Excel metadata is not overwritten
- repeated import is idempotent

## Acceptance Checks

- `files/legacy_record_tree.json` imports without crashing on a single bad record.
- Malformed records are reported as row-level errors.
- Re-import does not duplicate active links.
- JSON/Excel overlap respects Excel priority.

## Done When

Users can import old JSON exports as supplemental data without degrading records imported from Excel.
