# Phase 2: Project Skeleton

## Goal

Create the new Python CLI package skeleton, command entrypoint, dependency files, and core module boundaries. This phase should produce a runnable CLI shell, not full import/search/download behavior.

## Source Documents

- `dev_documents/requirement_analysis/05_implementation_plan.md`
- `dev_documents/high_level_design/02_architecture.md`
- `dev_documents/detail_design/01_module_design.md`

## Target Structure

```text
recordtree/
  __init__.py
  __main__.py
  app.py
  cli.py
  config.py
  db.py
  exceptions.py
  importer/
    __init__.py
    excel.py
    json_importer.py
    legacy_db.py
    parsers.py
    service.py
  mega.py
  models.py
  normalizers.py
  repositories.py
  schema.sql
  search.py
  sizes.py
tests/
documents/
dev_documents/
```

Recommended runtime dependencies:

```text
typer
rich
openpyxl
```

Recommended test/development dependency:

```text
pytest
```

Optional project files:

```text
pyproject.toml
requirements.txt
run-install.bat
setup_env.ps1
```

## Module Responsibilities

- `cli.py`: Typer command definitions, Rich output, user prompts, exit codes.
- `app.py`: application use-case orchestration and exception translation.
- `config.py`: default paths, config creation, config loading, path resolution.
- `db.py`: SQLite connection setup, schema initialization, transaction helper.
- `models.py`: dataclasses such as `ImportRecord`, `LinkItem`, and `DownloadPlan`.
- `repositories.py`: SQL access only; no Excel, JSON, or MEGAcmd logic.
- `normalizers.py` and `sizes.py`: pure rule helpers.
- `importer/*`: source-specific importers and shared import service.
- `mega.py`: MEGAcmd executable resolution and subprocess execution only.
- `search.py`: query composition and group-level download status summaries.

## Implementation Steps

1. Create the directory and file skeleton.
2. Implement `recordtree/__main__.py`:

```python
from .cli import app

if __name__ == "__main__":
    app()
```

3. Add placeholder Typer commands for `init`, `doctor`, `import`, and `stats`.
4. Define base exceptions in `exceptions.py`, including `RecordTreeError`, `ConfigError`, `ValidationError`, and `NotFoundError`.
5. Add initial dataclass shells in `models.py`; fill behavior in later phases.
6. Configure packaging or requirements so `python -m recordtree --help` works.

## Constraints

- Keep dependency direction as `cli -> app -> repositories / importer / search / mega / helpers`.
- Do not let `cli.py` directly query SQLite or call `subprocess`.
- Do not import from `legacy/`.
- Keep pure helper modules independent of SQLite.

## Acceptance Checks

- `python -m recordtree --help` runs successfully.
- The `recordtree` package imports cleanly.
- `tests/` exists.
- Placeholder commands fail gracefully or report "not implemented" without tracebacks.
- The package layout matches the detailed design.

## Done When

The project has a runnable CLI shell and stable module boundaries for the implementation phases that follow.
