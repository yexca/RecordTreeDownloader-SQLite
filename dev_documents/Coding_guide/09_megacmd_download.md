# Phase 9: MEGAcmd Download

## Goal

Implement diagnostics, download planning, MEGAcmd preflight checks, disk-space checks, confirmation prompts, `mega-get` execution, and download status recording.

## Source Documents

- `dev_documents/requirement_analysis/04_cli_and_flows.md`
- `dev_documents/requirement_analysis/05_implementation_plan.md`
- `dev_documents/high_level_design/04_cli_and_download_design.md`
- `dev_documents/detail_design/04_cli_search_download_detail.md`

## Scope

Implement:

```text
recordtree doctor
recordtree download <record_id_or_key> [--include-par2] [--types <exts>] [--output <dir>] [--yes]
```

Core behavior:

- MEGAcmd executable resolution
- `mega-whoami` login check
- active link selection
- default `.par2` exclusion
- file type filtering
- disk-space and safety-margin checks
- download plan confirmation
- per-link `mega-get`
- `downloads` and `download_items` persistence

## Files To Implement

- `recordtree/mega.py`
- `recordtree/app.py`
- `recordtree/cli.py`
- `recordtree/repositories.py`
- `recordtree/search.py`
- `recordtree/sizes.py`
- `recordtree/models.py`

## Doctor Command

Checks:

| Check | Result |
|---|---|
| config file exists and parses | pass/fail |
| database file is connectable | pass/fail |
| schema version exists | pass/fail |
| downloads/logs directories are writable | pass/fail |
| `mega-whoami` is executable | pass/fail |
| `mega-get` is executable | pass/fail |
| MEGA login status | pass/fail/warn |

`doctor` must not modify business data. Missing MEGAcmd or missing login should return a non-zero exit code with a useful fix hint.

## Mega Module

`mega.py` should only wrap external commands:

```python
def resolve_executable(configured: str) -> str: ...
def check_login(mega_whoami: str) -> MegaLoginStatus: ...
def download_link(mega_get: str, mega_url: str, output_dir: Path) -> MegaCommandResult: ...
```

Requirements:

- Use `subprocess.run([...], shell=False)`.
- Capture stdout and stderr.
- Truncate command output summaries, for example to 4000 characters.
- Do not update the database in `mega.py`.

## Download Arguments

```text
recordtree download <record_id_or_key> [--include-par2] [--types <exts>] [--output <dir>] [--yes]
```

Rules:

- Target resolution matches `info`.
- `--include-par2` explicitly includes `.par2`.
- `--types` accepts comma-separated extensions such as `.mp4,.m4a` or `mp4,m4a`.
- Default output directory is `downloads/<record_group_id>/`.
- `--yes` skips confirmation but never skips preflight checks.

## Plan Generation

Steps:

1. Resolve target.
2. Load active links.
3. Apply config and `--include-par2` rules.
4. Apply `--types`.
5. Calculate `selected_bytes`.
6. Calculate `margin_bytes`.
7. Resolve output directory.
8. Find the nearest existing parent directory and check free space.
9. Build `DownloadPlan`.

If no links remain, show why:

```text
No links selected after excluding .par2 and applying --types .mp4
```

## Disk-Space Rule

```python
margin = max(
    int(selected_bytes * safety_margin_percent / 100),
    safety_margin_min_mb * 1024 * 1024,
)
required = selected_bytes + margin
```

- Pass when `free_bytes_before >= required`.
- On failure, write `downloads.status = blocked` with required/free values in `message`.
- Do not create the final output directory.
- Do not call MEGAcmd.

## Execution Flow

Preflight order:

1. Resolve MEGAcmd executables.
2. Run `mega-whoami`.
3. Check disk space.
4. Show plan and ask for confirmation unless `--yes`.

Download execution:

1. Create output directory.
2. Create one `downloads` row with status `planned`.
3. For each selected link:
   - create a `download_items` row with status `planned`
   - call `mega-get <url> <output_dir>`
   - mark item `completed` on exit code 0
   - mark item `failed` on non-zero exit code or exception
4. Mark download `completed` if all items completed.
5. Mark download `failed` if any item failed.

In v1, continue after a single link failure and show the final completed/failed counts.

## Test Guidance

Mock subprocess; do not use a real MEGA account:

- missing MEGAcmd
- `mega-whoami` exit 0
- `mega-whoami` non-zero exit
- `mega-get` exit 0
- `mega-get` non-zero exit
- long stdout/stderr truncation
- no `mega-get` call when not logged in
- no `mega-get` call when disk space is insufficient

Plan tests:

- default `.par2` exclusion
- `--include-par2`
- `--types mp4,m4a`
- `--types par2` without `--include-par2`
- required byte calculation

## Acceptance Checks

- Missing MEGAcmd is reported clearly.
- Not logged in stops before download and suggests `mega-login`.
- Insufficient disk space stops before `mega-get`.
- User cancellation writes `cancelled`.
- Mocked successful downloads mark selected items completed.
- Mocked failed downloads record failed item status and useful messages.

## Done When

The CLI can safely download selected active links through local MEGAcmd and persist every attempt and per-link outcome.
