# CLI, Search And Download Detailed Design

## 1. CLI Framework

Recommended libraries:

```text
typer
rich
```

Entry point:

```python
# recordtree/__main__.py
from .cli import app

if __name__ == "__main__":
    app()
```

Shared command options can be added later:

```text
--config <path>
--verbose
```

v1 can initially use the default `env/config.toml`.

## 2. Commands And Exit Codes

| Command | Success Exit Code | Main Failure Exit Codes |
|---|---:|---|
| `init` | 0 | 2 |
| `doctor` | 0 | 4 |
| `import` | 0 | 2, 10 |
| `search-*` | 0 | 2 |
| `list-undownloaded` | 0 | 2 |
| `info` | 0 | 3 |
| `download` | 0 | 3, 4, 5, 10 |
| `stats` | 0 | 2 |

Failure scenarios do not print Python tracebacks unless a future `--verbose` option is added.

## 3. `init`

Flow:

1. Create the configuration file.
2. Load configuration.
3. Create the database parent directory, download directory, and log directory.
4. Initialize schema.
5. Output a path summary.

Repeated execution:

- Existing configuration is not overwritten.
- Existing database only receives missing schema objects.
- Existing directories do not produce errors.

## 4. `doctor`

Checks:

| Check | Result |
|---|---|
| Configuration file exists and can be parsed | pass/fail |
| Database file can be connected | pass/fail |
| Schema version exists | pass/fail |
| downloads/logs directories are writable | pass/fail |
| `mega-whoami` is executable | pass/fail |
| `mega-get` is executable | pass/fail |
| MEGA login status | pass/fail/warn |

`doctor` does not modify business data. If MEGAcmd is missing or not logged in, it returns a non-zero exit code and provides a repair hint.

## 5. Search Queries

Common output columns:

```text
id | delivery_date | actor | title | source | size | active_links | downloaded
```

Sorting:

```sql
ORDER BY
  record_groups.delivery_date DESC,
  record_groups.entry_date DESC,
  record_groups.id DESC
```

Default limit:

```text
--limit 50
```

Limit rules:

- Default to 50 when unspecified.
- Values below 1 are argument errors.
- Use an upper bound such as 500 to avoid excessive terminal output.

## 6. `search-actor`

Arguments:

```text
recordtree search-actor <name> [--limit <n>]
```

Query logic:

```sql
SELECT ...
FROM record_groups rg
JOIN record_group_actors rga ON rga.record_group_id = rg.id
JOIN actors a ON a.id = rga.actor_id
WHERE rg.is_deleted = 0
  AND a.name_normalized LIKE ?
```

Parameter value:

```text
%normalize_search_text(name)%
```

## 7. `search-title`

Arguments:

```text
recordtree search-title <keyword> [--limit <n>]
```

Search fields:

- `title`
- `upload_title`
- `duplicate_search_raw`

v1 can directly use `LIKE` on raw fields and a casefolded user input. If SQLite's default case behavior proves insufficient, add normalized shadow columns later.

## 8. `search-source`

Arguments:

```text
recordtree search-source <source> [--limit <n>]
```

The query logic is similar to actor search and uses `sources.name_normalized LIKE ?`.

## 9. `search-date`

Arguments:

```text
recordtree search-date [--from <date>] [--to <date>] [--limit <n>]
```

Rules:

- At least one of `--from` or `--to` must be provided.
- Dates must normalize to `YYYY-MM-DD`.
- Query only `delivery_date`.

SQL conditions:

```sql
delivery_date >= :date_from
delivery_date <= :date_to
```

Rows with empty `delivery_date` do not appear in date-search results.

## 10. `list-undownloaded`

Arguments:

```text
recordtree list-undownloaded [--actor <name>] [--source <source>] [--limit <n>]
```

Definition:

At least one active link exists, and that link has no `completed` or `legacy_completed` status.

SQL idea:

```sql
WHERE EXISTS (
    SELECT 1
    FROM download_links dl
    WHERE dl.record_group_id = rg.id
      AND dl.is_deleted = 0
      AND NOT EXISTS (
          SELECT 1
          FROM download_items di
          WHERE di.link_id = dl.id
            AND di.status IN ('completed', 'legacy_completed')
      )
)
```

Optional actor/source filters reuse the joins from search queries.

## 11. Download Status Aggregation

Per group statistics:

```text
active_count
completed_count
```

Display values:

| Condition | Display |
|---|---|
| `active_count = 0` | `unknown` |
| `completed_count = 0` | `none` |
| `completed_count < active_count` | `partial` |
| `completed_count = active_count` | `all` |

## 12. `info`

Arguments:

```text
recordtree info <record_id_or_key>
```

Target resolution:

- All digits: query by `record_groups.id`.
- Otherwise: query by full `source_key`.

Output block:

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

Default URL preview:

```text
https://mega.nz/file/<redacted-preview>
```

If inactive links exist:

```text
Historical inactive links: 3
```

v1 does not expand historical links by default.

## 13. `stats`

Output:

- Total record groups.
- Total active links.
- Total inactive historical links.
- Actor count.
- Source count.
- Downloaded all/partial/none summary.
- Last 5 imports.
- Last 5 downloads.

`stats` reads only from the database.

## 14. Download Arguments

Command:

```text
recordtree download <record_id_or_key> [--include-par2] [--types <exts>] [--output <dir>] [--yes]
```

Argument rules:

- `record_id_or_key` follows `info` target resolution.
- `--include-par2` overrides configuration and explicitly includes `.par2`.
- `--types` accepts comma-separated values: `.mp4,.m4a` or `mp4,m4a`.
- When `--output` is omitted, use `downloads/<record_group_id>/`.
- `--yes` skips confirmation but does not skip pre-checks.

## 15. Download Plan Generation

Steps:

1. Resolve target.
2. Read active links.
3. Filter `.par2` according to configuration and `--include-par2`.
4. Filter file types according to `--types`.
5. Calculate `selected_bytes`.
6. Calculate `margin_bytes`.
7. Resolve output directory.
8. Find the nearest existing parent directory and read available disk space.
9. Generate `DownloadPlan`.

If filtering leaves no links, raise `NoLinksSelectedError`. Exit code 2 or 3 is acceptable; 3 is recommended because the target exists but cannot be downloaded.

## 16. File Type Filtering

Normalization:

```text
mp4 -> .mp4
.MP4 -> .mp4
" .mp4 , m4a " -> {".mp4", ".m4a"}
```

Matching is case-insensitive.

Default `.par2` exclusion can run before or after `--types`, but the error message must describe the final filter conditions. Recommended order:

1. Active links.
2. par2 rule.
3. Type filter.

With this order, `--types par2` still will not download `.par2` unless `--include-par2` is also passed, and the prompt should explain that `--include-par2` is needed.

## 17. Disk Space Check

Calculation:

```python
margin = max(
    int(selected_bytes * safety_margin_percent / 100),
    safety_margin_min_mb * 1024 * 1024,
)
required = selected_bytes + margin
```

Check:

- Pass when `free_bytes_before >= required`.
- If it fails, write `downloads.status = blocked` and include required/free in `message`.
- Do not create the final output directory.
- Do not call MEGAcmd.

## 18. MEGAcmd Pre-Checks

Order:

1. `resolve_executable(mega_whoami)`.
2. `resolve_executable(mega_get)`.
3. Check login with `mega-whoami`.

If not logged in:

- Write `downloads.status = blocked`.
- Include a message prompting the user to run `mega-login` manually.
- Do not call `mega-get`.

## 19. Confirmation Prompt

Unless `--yes` is passed, display:

```text
Record: <id> <actor> <title>
Output: <dir>
Files: <count>
Types: .mp4, .m4a
Selected size: <size>
Safety margin: <size>
Required: <size>
Free: <size>
Exclude .par2: yes/no
```

If the user declines:

- Write `downloads.status = cancelled`.
- Do not create the output directory.
- Do not call `mega-get`.

## 20. Download Execution

Steps:

1. Create output directory.
2. Create a `downloads` record with status `planned`.
3. For each selected link:
   - Create a `download_items` row with status `planned`.
   - Call `mega-get <url> <output_dir>`.
   - Exit code 0: item status `completed`.
   - Non-zero exit code or exception: item status `failed`.
4. After all items finish:
   - All completed: download status `completed`.
   - Any failed: download status `failed`.

If a single link fails, v1 should continue downloading subsequent links and show the failure count in the final summary.

## 21. Output Summary

Success:

```text
Download completed
  record_group_id: 123
  completed: 2
  failed: 0
  output: downloads/123
```

Partial failure:

```text
Download finished with failures
  completed: 1
  failed: 1
  see database download id: 456
```

Blocked:

```text
Download blocked: insufficient disk space
  required: 10.50 GB
  free: 8.20 GB
```
