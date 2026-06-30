# Architecture

RecordTreeDownloader SQLite is a local, single-process CLI application. It reads local source files, writes a local SQLite database, and delegates actual downloads to MEGAcmd through subprocess calls.

## Layers

- CLI: `recordtree/cli.py` defines Typer commands, formats Rich tables, and maps user-facing errors to exit codes.
- Application services: `recordtree/app.py` coordinates init, import, search, doctor, and download workflows.
- Importers: `recordtree/importer/` parses Excel, legacy JSON, and legacy SQLite inputs into normalized import models.
- Domain helpers: `recordtree/normalizers.py`, `recordtree/sizes.py`, and `recordtree/search.py` implement pure rules for dates, text, sizes, hashes, search, and download planning.
- Repositories: `recordtree/repositories.py` contains SQLite persistence operations.
- Infrastructure: `recordtree/db.py`, `recordtree/config.py`, and `recordtree/mega.py` handle schema setup, config loading, and MEGAcmd process wrapping.

Dependencies point inward from CLI orchestration toward helpers and repositories. New behavior should prefer the application service layer instead of making the CLI call persistence or subprocess code directly.

## Key Decisions

SQLite is used because the data set is local, relational, searchable, and large enough to benefit from indexes without requiring a server. The database is portable and easy to back up before large imports.

Excel is the primary data source because it is the most complete current Record Tree export. Legacy JSON and legacy SQLite imports exist for compatibility and migration.

Download status is authoritative at the link level. A record group can be `all`, `partial`, `none`, or `unknown` based on active link statuses, which preserves mixed states when a group has multiple files.

Default download output is built from the configured downloads root plus a relative folder template. The default template is `{actor_safe_name}/{record_group_id}`.

`legacy/` is reference-only. It preserves the original scripts for comparison and migration context, but the new `recordtree/` package must not import from it.

MEGA credentials are not stored by this application. The tool checks MEGAcmd login state with `mega-whoami` and runs `mega-get` only after preflight checks pass.
