# Testing Guide

Install runtime and test dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run the full suite:

```bash
pytest
```

Run one file:

```bash
pytest tests/test_import_service.py
```

Run focused tests:

```bash
pytest tests/test_download.py -k par2
```

## Fixture Principles

Keep fixtures small and synthetic. Tests should use temporary SQLite databases and generated files under `tmp_path` rather than real private exports.

Recommended fixture sizes:

- Excel: 3 to 5 rows
- JSON: 1 to 2 authors
- Legacy SQLite: 3 to 5 records

Real personal exports or credentials should not be committed. If manual testing needs sensitive real data, place it under `real_test/` and keep it out of commits.

## MEGAcmd Tests

MEGAcmd tests must use mocks. Automated tests should not require:

- Real network access
- A real MEGA account
- Stored MEGA credentials
- Actual `mega-get` downloads

Mock `subprocess.run`, `recordtree.mega.check_login`, or `recordtree.mega.download_link` depending on the layer under test. Assert subprocess arguments are lists and `shell=False`.

## Backup Guidance

Before large real-data imports:

```bash
recordtree stats
```

Back up `env/recordtree.sqlite3`. If SQLite WAL mode files are present, include `env/recordtree.sqlite3-wal` and `env/recordtree.sqlite3-shm`, or use the SQLite backup API.

After imports, inspect:

```bash
recordtree stats
recordtree list-undownloaded --limit 20
```

If the import completed with errors, review:

```text
logs/import_<import_id>_errors.csv
```
