# Data Contract

This document describes the public input shapes and persistence rules used by RecordTreeDownloader SQLite.

## Excel Workbook

The Excel importer expects one header row and these logical fields:

- `actor_raw`
- `delivery_date`
- `title`
- `entry_date`
- `note`
- `upload_title`
- `duplicate_search_raw`
- `source_name`
- `mega_json`
- `size_raw`

Known legacy mojibake header aliases are accepted by the importer. Extra columns are ignored and reported in import notes.

Dates may be typed Excel date cells or ISO-like strings. Blank dates become null. Invalid dates are row-level import errors.

## MEGA JSON

Each Excel row's `mega_json` is a JSON object. Root fields:

- `FileNames`: optional display name for the MEGA bundle
- `total`: optional total byte count
- `FormattedSize`: optional human-readable size
- `property`: required list of link items

Each `property` item is an object with:

- `Link`: required MEGA URL
- `Size`: required integer byte count or numeric string
- `Type`: optional file type, normalized to lower-case with a leading dot
- `FormattedSize`: optional human-readable size

Malformed JSON, missing `property`, missing `Link`, or non-integer `Size` produce row-level import errors.

## Legacy SQLite

The legacy SQLite importer requires:

- Table `author` with columns `author_id`, `name`, `added_date`
- Table `record` with columns `record_id`, `author_id`, `name`, `date`, `size`, `link`, `added_date`, `downloaded_date`

Legacy rows are matched to existing active links by URL. A matched URL reuses the existing record group and link. An unmatched URL creates a legacy-only record group and link.

For best metadata preservation, import the primary Excel workbook before importing the legacy SQLite database. In that order, URL matches attach legacy IDs and `legacy_completed` history to Excel-backed record groups instead of creating legacy-only groups first.

## Legacy JSON

The legacy JSON importer supports a root list. Each author item must be an object with:

- `author`
- `records`, a list of record objects

Each record object uses the same MEGA JSON fields described above, including a `property` link list. JSON metadata has lower priority than existing Excel metadata when links overlap.

Legacy JSON should be imported after Excel and legacy SQLite. It is intended for compatibility checks and backfill, not as the authoritative metadata source.

## Identity And Link Rules

`source_key` is generated from normalized actor, delivery date, title, entry date, upload title, and source name. The same metadata yields the same key; changing those identity fields yields a different key.

The active link set is hashed from link order, URL, file type, size, and formatted size. Link order is intentionally significant in v1.

When the same `source_key` is imported again with the same active link set, active links are not duplicated. When the link set changes, old active links are marked inactive with `is_deleted = 1`, and the new links become active. Active MEGA URLs must be unique.

## Download Status Values

Download rows and items use these status values:

- `planned`
- `completed`
- `failed`
- `blocked`
- `cancelled`
- `legacy_completed`

Search and stats derive record-level labels from active links:

- `all`: every active link has `completed` or `legacy_completed`
- `partial`: some active links are completed
- `none`: no active links are completed
- `unknown`: no active links exist
