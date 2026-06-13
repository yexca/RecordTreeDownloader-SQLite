# Quality Attributes And Decisions

## 1. Quality Goals

| Quality Attribute | Goal |
|---|---|
| Data consistency | Repeated imports do not create duplicate active links; link changes preserve history; legacy download status is not lost. |
| Recoverability | Import errors are traceable, download failures are recorded, and failure causes can be located from the database or logs. |
| Maintainability | CLI, import, database, search, and MEGAcmd integration boundaries are clear, avoiding further spread of legacy-script global state. |
| Testability | Core rules such as normalization, hashing, size parsing, import upsert, and download planning can be tested without real MEGAcmd. |
| Usability | Command output is clear, large result sets are limited by default, and download plans are shown before user confirmation. |
| Performance | Support local import and query for tens of thousands of Excel rows and hundreds of thousands of MEGA links and legacy records. |

## 2. Key Design Decisions

### Decision 1: Use SQLite

Rationale:

- A single-machine tool does not need a database service.
- SQLite provides transactions, indexes, and enough scale for the current data.
- The database file is easy to back up, migrate, and inspect.

Trade-offs:

- It is not designed for multi-user concurrent writes.
- Full-text search is limited; FTS5 can be added later if needed.

### Decision 2: Treat Excel As The Primary Data Source

Rationale:

- The current latest and most complete data source is the Excel workbook.
- JSON has old-format and text-quality issues.
- The main value of legacy SQLite is download history, not latest metadata.

Trade-offs:

- The importer must provide clear errors when Excel headers change.
- Priority rules are required when JSON or legacy data overlaps with Excel data.

### Decision 3: Use `record_groups` Instead Of The Old `record`

Rationale:

- One new Record Tree row may contain multiple MEGA file links.
- User search and download behavior usually centers on a group of files.
- A record group can represent an Excel row, a JSON record, or a legacy-only group.

Trade-offs:

- Migrating legacy single-link records requires generating or matching record groups.
- Download status must be displayed at both group and link levels.

### Decision 4: Use `source_key` For Imported Record Identity

Rationale:

- Upload title has duplicates.
- MEGA links can change.
- A combination of stable metadata fields is better for deciding whether two imports refer to the same record group.

Trade-offs:

- If upstream data corrects a title or date, the import may generate a new source key.
- Detailed design should define conflict investigation and manual repair entry points.

### Decision 5: Preserve Historical Links

Rationale:

- Later imports may change link sets; overwriting them would lose audit information.
- Legacy download status may be associated with old links.
- Historical links help debug source-data changes and repeated import behavior.

Trade-offs:

- Queries must consistently filter `is_deleted = 0`.
- Database size grows with import history.

### Decision 6: Make Link-Level Download Status Authoritative

Rationale:

- A record group can contain multiple file types and links.
- Users may download only `.mp4` or exclude `.par2`.
- Legacy data download status is effectively attached to one old record/link.

Trade-offs:

- Group-level downloaded display requires aggregation.
- CLI output must avoid implying that a partial download means all files are complete.

### Decision 7: Exclude `.par2` By Default

Rationale:

- `.par2` files can be numerous and are usually for verification/recovery, not necessarily the main content users want by default.
- Excluding them by default reduces disk pressure.
- `--include-par2` and configuration still allow full downloads.

Trade-offs:

- The download plan must clearly state whether `.par2` was excluded.
- User documentation must describe the default behavior.

### Decision 8: Require MEGAcmd And Disk Checks Before Download

Rationale:

- Avoid starting downloads in states known to fail.
- Missing login and insufficient space can be reported quickly.
- Download records can preserve blocked reasons for troubleshooting.

Trade-offs:

- The download flow is longer than directly calling `mega-get`.
- Disk space can still be consumed by other processes during the download.

## 3. Test Strategy

Prioritize core rules:

- Size parser: `894.12 MB`, `13.53 GB`, `0 B`, malformed text.
- Date parser: Excel datetime, ISO string, blank.
- MEGA JSON parser: valid JSON, missing `property`, missing `Link`, non-integer `Size`.
- Source key: stable for identical metadata, changes when title/source/date changes.
- Import idempotency: importing the same sample twice does not create duplicates.
- Link replacement: old links become inactive and new links become active when the link set changes.
- Legacy migration: `downloaded_date = '0'`, date string, URL match, unmatched legacy row.
- Search: actor/source/title/date/status filters and limit behavior.
- Download planning: par2 exclusion, type filter, disk check, mocked MEGAcmd.

Test layers:

- Unit tests cover pure rule modules.
- Integration tests use small xlsx/json/legacy-db fixtures and temporary SQLite databases.
- MEGAcmd is mocked through subprocess tests, without relying on real network or a real account.

## 4. Main Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Excel header changes | Import fails or fields shift | Validate by header name and report missing/extra columns. |
| Source-key fields are corrected upstream | One logical record may become a new record group | Preserve raw fields and link URLs; later provide conflict/duplicate checks. |
| Legacy DB overlaps with Excel | Duplicate links or status overwrite | Match by URL, prefer Excel metadata, map legacy status separately. |
| Poor JSON text quality | Bad metadata enters the main database | Keep JSON lower priority than Excel; do not overwrite high-quality metadata for overlapping links. |
| Large imports are slow | User waits too long | Use read-only streaming, transactions, indexes, and progress output. |
| MEGAcmd state is unstable | Download fails | Run `mega-whoami` before every download and record failure summaries. |
| Disk-space estimate is insufficient | Download interruption | Add a safety margin of 5% or at least 512 MB. |

## 5. Open Questions

Recommended confirmations before detailed design or implementation:

1. Should `download <record_id>` download all non-`.par2` active links by default?
2. Does v1 need interactive selection of a single link, or are `--types` and `--include-par2` enough?
3. Should legacy SQLite import be repeatable, or only a one-time migration entry point?
4. Should search results display downloaded status as all/partial/none, or only whether undownloaded links exist?
5. Does v1 need a command for querying inactive historical links?

## 6. Phase Delivery Boundary

After high-level design, the next phase can move into detailed design or directly implement the v1 skeleton.

Recommended implementation order:

1. Move old code into `legacy/` and create the new package skeleton.
2. Implement configuration, database schema, and `init`.
3. Implement the unified import service and Excel import.
4. Implement legacy SQLite migration and JSON compatibility import.
5. Implement search, info, and stats commands.
6. Implement `doctor`, download planning, MEGAcmd invocation, and download records.
7. Complete tests and user documentation.
