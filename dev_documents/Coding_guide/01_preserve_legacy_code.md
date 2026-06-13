# Phase 1: Preserve Legacy Code

## Goal

Move the current root-level legacy scripts into `legacy/` so they remain available as reference material while the new `recordtree/` package is built. New implementation code must not import from `legacy/`.

## Source Documents

- `dev_documents/requirement_analysis/05_implementation_plan.md`
- `dev_documents/detail_design/01_module_design.md`

## Scope

Move and preserve:

```text
config.py
db.py
download.py
initSqlite.py
main.py
mega.py
Record.py
recordInsert.py
recordinsertbyxlsx.py
util.py
mapper/
```

## Implementation Steps

1. Create `legacy/` at the project root.
2. Move the legacy files and `mapper/` directory into `legacy/`.
3. Keep file contents readable and avoid behavior changes in this phase.
4. Add or keep a project convention that new code under `recordtree/` must not import from `legacy/`.
5. Search for `import legacy`, `from legacy`, and old root-level module imports after the move.

## Boundaries

- Do not rewrite, fix, or modernize legacy scripts in this phase.
- Do not use `legacy/` as a runtime dependency for the new CLI.
- If a legacy file has unrelated local edits, preserve those edits while moving the file.

## Acceptance Checks

- All listed legacy files are readable under `legacy/`.
- The project root no longer contains those old CLI entry scripts.
- No new package module imports from `legacy/`.
- Git diff clearly shows a move/preservation step, not a mixed refactor.

## Done When

The legacy implementation is preserved as reference-only material and the project is ready for the new package skeleton.
