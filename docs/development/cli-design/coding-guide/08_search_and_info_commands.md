# Phase 8: Search And Info Commands

## Goal

Implement read-only search, detail, and stats commands so imported data can be inspected and users can identify download targets.

## Source Documents

- `dev_documents/requirement_analysis/04_cli_and_flows.md`
- `dev_documents/requirement_analysis/05_implementation_plan.md`
- `dev_documents/high_level_design/04_cli_and_download_design.md`
- `dev_documents/detail_design/04_cli_search_download_detail.md`

## Scope

Implement:

```text
recordtree search-actor <name> [--limit <n>]
recordtree search-title <keyword> [--limit <n>]
recordtree search-source <source> [--limit <n>]
recordtree search-date [--from <date>] [--to <date>] [--limit <n>]
recordtree list-undownloaded [--actor <name>] [--source <source>] [--limit <n>]
recordtree info <record_id_or_key>
recordtree stats
```

## Files To Implement

- `recordtree/search.py`
- `recordtree/repositories.py`
- `recordtree/app.py`
- `recordtree/cli.py`
- `recordtree/normalizers.py`
- `recordtree/sizes.py`

## Common Output Rules

List columns:

```text
id | delivery_date | actor | title | source | size | active_links | downloaded
```

Rules:

- Default `--limit` is 50.
- A limit below 1 is a parameter error.
- Use a maximum limit such as 500 to avoid flooding the terminal.
- Sort by `delivery_date DESC`, `entry_date DESC`, and `id DESC`.
- Display missing dates, notes, and sizes as `-`.
- Show URL previews in list/detail output; full export can be added later.

## Download Status Summary

Calculate per group from active links:

```text
active_count
completed_count
```

Display:

| Condition | Display |
|---|---|
| `active_count = 0` | `unknown` |
| `completed_count = 0` | `none` |
| `completed_count < active_count` | `partial` |
| `completed_count = active_count` | `all` |

`completed_count` includes `download_items.status IN ('completed', 'legacy_completed')`.

## Search Commands

`search-actor`:

- Query `actors.name_normalized LIKE ?`.
- Bind `%normalize_search_text(name)%`.

`search-title`:

- Search `title`, `upload_title`, and `duplicate_search_raw`.
- v1 may use SQLite `LIKE`; add normalized shadow columns later only if needed.

`search-source`:

- Query `sources.name_normalized LIKE ?`.

`search-date`:

- Require at least one of `--from` or `--to`.
- Normalize dates to `YYYY-MM-DD`.
- Query only `delivery_date`.
- Exclude rows with null `delivery_date`.

`list-undownloaded`:

- Include groups with at least one active link that lacks `completed` or `legacy_completed`.
- Reuse actor/source joins for optional filters.

## Info Command

`recordtree info <record_id_or_key>` accepts:

- all digits: lookup by `record_groups.id`
- otherwise: lookup by exact `source_key`

Output sections:

```text
Record group
  id
  source_key
  actor
  delivery_date
  entry_date
  title
  source
  upload_title
  note
  size
  active_links
  downloaded
```

Link table:

```text
order | type | size | status | url
```

URL preview format:

```text
https://mega.nz/file/<redacted-preview>
```

If inactive links exist, show only a count by default:

```text
Historical inactive links: 3
```

## Stats Command

Report:

- total record groups
- active link count
- inactive historical link count
- actor count
- source count
- downloaded all/partial/none summary
- five most recent imports
- five most recent downloads

`stats` must be read-only.

## Test Guidance

Prepare data with:

- actor A / source niconico / title ASMR
- actor B / source Withny / title music
- different `delivery_date` values
- completed, partial, and none download states

Cover:

- actor LIKE search
- title search against `title`
- title search against `upload_title`
- case-insensitive source search
- date from/to search
- `list-undownloaded` excluding all-completed groups
- limit behavior
- `info` not found exit code 3

## Acceptance Checks

- Known actors from imported Excel data can be found.
- Source search works for `niconico`, `Withny`, and `rPlay`.
- `list-undownloaded` respects migrated legacy download statuses.
- `info` shows active links and status without overwhelming the terminal.
- `stats` returns quickly.

## Done When

Users can find target records, inspect active links and status, and gather IDs for download commands.
