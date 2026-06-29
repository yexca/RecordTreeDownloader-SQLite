# Troubleshooting

## Useful Commands

```bash
recordtree doctor
recordtree stats
recordtree info <id>
recordtree list-undownloaded --limit 20
recordtree list-undownloaded --actor-id <actor-id>
```

## Common Issues

- Missing config or database: run `recordtree init`.
- Unsupported import extension: use `.xlsx`, `.xlsm`, `.json`, `.db`, `.sqlite`, or `.sqlite3`.
- Import row errors: check `logs/import_<import_id>_errors.csv`.
- MEGAcmd missing: install MEGAcmd and ensure `mega-get` and `mega-whoami` are on `PATH`, or configure executable paths in `env/config.toml`.
- Not logged in: run `mega-login`, then run `recordtree doctor`.
- Insufficient disk space: change `--output`, free space, or adjust the safety margin in `env/config.toml`.

## Backups

Before importing large legacy databases or doing large re-imports, back up:

- `env/recordtree.sqlite3`
- `env/recordtree.sqlite3-wal`, if present
- `env/recordtree.sqlite3-shm`, if present

You can also use the SQLite backup API.
